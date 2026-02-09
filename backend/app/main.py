from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.errors import add_exception_handlers
from app.api.v1 import api_router
from app.core.cache import cache
from app.core.config import get_settings
from app.core.logging import configure_logging


class CookieSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
