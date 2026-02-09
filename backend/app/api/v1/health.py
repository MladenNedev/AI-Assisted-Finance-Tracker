from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.cache import cache
from app.persistence.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(response: Response) -> dict[str, object]:
    database_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        database_ok = True
    except Exception:
        database_ok = False

    redis_ok = await cache.is_available()

    overall = "ok" if database_ok else "degraded"
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall,
        "checks": {
            "database": "ok" if database_ok else "error",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }
