import logging
import secrets
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
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
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = int((time.perf_counter() - start) * 1000)
        user_id = getattr(request.state, "user_id", None)
        logger.info(
            "request_completed request_id=%s method=%s path=%s status=%s duration_ms=%s user_id=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            user_id,
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


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

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
    return app


app = create_app()
