from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)

REPORT_VERSION_KEY_PREFIX = "report:ver:user"


class CacheService:
    def __init__(self) -> None:
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        settings = get_settings()
        if not settings.redis_url:
            return

        try:
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("Redis cache connected")
        except Exception:
            logger.warning("Redis cache unavailable; continuing without cache", exc_info=True)
            self._client = None

    async def disconnect(self) -> None:
        if self._client is None:
            return
        await self._client.aclose()
        self._client = None
        logger.info("Redis cache disconnected")

    async def get_json(self, key: str) -> Any | None:
        if self._client is None:
            return None
        try:
            payload = await self._client.get(key)
            if payload is None:
                return None
            return json.loads(payload)
        except Exception:
            logger.warning("Failed cache read for key=%s", key, exc_info=True)
            return None

    async def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.setex(
                key,
                ttl_seconds,
                json.dumps(value, default=str, separators=(",", ":")),
            )
            return True
        except Exception:
            logger.warning("Failed cache write for key=%s", key, exc_info=True)
            return False

    async def get_user_report_version(self, user_id: UUID) -> int:
        if self._client is None:
            return 1
        key = _user_report_version_key(user_id)
        try:
            value = await self._client.get(key)
            if value is None:
                await self._client.set(key, "1")
                return 1
            return int(value)
        except Exception:
            logger.warning(
                "Failed reading report cache version for user=%s", user_id, exc_info=True
            )
            return 1

    async def bump_user_report_version(self, user_id: UUID) -> int:
        if self._client is None:
            return 1
        key = _user_report_version_key(user_id)
        try:
            value = await self._client.incr(key)
            return int(value)
        except Exception:
            logger.warning(
                "Failed bumping report cache version for user=%s", user_id, exc_info=True
            )
            return 1


def _user_report_version_key(user_id: UUID) -> str:
    return f"{REPORT_VERSION_KEY_PREFIX}:{user_id}"


def report_cache_key(
    user_id: UUID,
    version: int,
    prefix: str,
    params: Mapping[str, Any] | None = None,
) -> str:
    pairs = []
    if params:
        pairs = [f"{key}={params[key]}" for key in sorted(params)]
    suffix = ":".join(pairs)
    if suffix:
        return f"report:v{version}:user:{user_id}:{prefix}:{suffix}"
    return f"report:v{version}:user:{user_id}:{prefix}"


cache = CacheService()
