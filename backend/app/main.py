import logging
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import sentry_sdk
from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.api.errors import add_exception_handlers
from app.api.v1 import api_router
from app.core.cache import cache
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.errors import ErrorResponse

logger = logging.getLogger(__name__)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CookieSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        if sentry_sdk.Hub.current.client is not None:
            sentry_sdk.set_tag("request_id", request_id)
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": getattr(request.state, "user_id", None),
                "client_ip": request.client.host if request.client else None,
            },
        )

        response.headers["X-Request-ID"] = request_id

        rate_limit = getattr(request.state, "rate_limit", None)
        if isinstance(rate_limit, dict):
            response.headers["X-RateLimit-Limit"] = str(rate_limit.get("limit", ""))
            response.headers["X-RateLimit-Remaining"] = str(rate_limit.get("remaining", ""))
            response.headers["Retry-After"] = str(rate_limit.get("retry_after", ""))
        return response


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        path = request.url.path

        if (
            settings.csrf_enabled
            and request.method not in SAFE_METHODS
            and path.startswith("/api/v1")
            and path not in {"/api/v1/auth/login", "/api/v1/auth/register"}
        ):
            session_token = request.cookies.get(settings.cookie_name)
            if session_token:
                csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
                csrf_header = request.headers.get(settings.csrf_header_name)
                if (
                    not csrf_cookie
                    or not csrf_header
                    or not secrets.compare_digest(csrf_cookie, csrf_header)
                ):
                    payload = ErrorResponse(
                        code="csrf_invalid", message="CSRF token missing or invalid"
                    )
                    return JSONResponse(
                        status_code=403,
                        content=jsonable_encoder(payload.model_dump()),
                    )

        response: Response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    await cache.connect()
    try:
        yield
    finally:
        await cache.disconnect()


def _configure_frontend(app: FastAPI, settings: object) -> None:
    dist_dir_value = getattr(settings, "frontend_dist_dir", None)
    if not dist_dir_value:
        return

    dist_dir = Path(dist_dir_value)
    if not dist_dir.exists():
        logger.warning("Frontend dist directory not found: %s", dist_dir)
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="Not found")

        candidate = dist_dir / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)

    return FileResponse(dist_dir / "index.html")


def _configure_sentry(settings: object) -> None:
    dsn = getattr(settings, "sentry_dsn", None)
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=getattr(settings, "sentry_environment", "development"),
        traces_sample_rate=getattr(settings, "sentry_traces_sample_rate", 0.1),
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    )


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    _configure_sentry(settings)

    app = FastAPI(title="AI-Assisted Finance Tracker", version="0.1.0", lifespan=lifespan)

    app.add_middleware(CookieSessionMiddleware)
    app.add_middleware(CsrfProtectionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    add_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    _configure_frontend(app, settings)
    return app


app = create_app()
