from __future__ import annotations

import ipaddress
from dataclasses import dataclass

from app.core.cache import cache
from app.core.exceptions import RateLimitExceededError, RateLimitUnavailableError
from fastapi import Request


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: str
    limit: int
    window_seconds: int
    fail_closed_on_unavailable: bool = False


def _normalize_ip(raw_ip: str | None) -> str:
    if not raw_ip:
        return "unknown"
    try:
        return ipaddress.ip_address(raw_ip).compressed
    except ValueError:
        return raw_ip.strip() or "unknown"


def _extract_client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        return _normalize_ip(first_ip)
    if request.client is not None:
        return _normalize_ip(request.client.host)
    return "unknown"


async def enforce_rate_limit(request: Request, policy: RateLimitPolicy) -> None:
    key = f"rate_limit:{policy.scope}:{_extract_client_id(request)}"
    result = await cache.increment_with_ttl(key, ttl_seconds=policy.window_seconds)
    if result is None:
        if policy.fail_closed_on_unavailable:
            raise RateLimitUnavailableError(
                "Rate limiting is temporarily unavailable",
                details={"scope": policy.scope},
            )
        return

    count, retry_after = result
    remaining = max(policy.limit - count, 0)
    request.state.rate_limit = {
        "limit": policy.limit,
        "remaining": remaining,
        "retry_after": max(retry_after, 0),
    }

    if count > policy.limit:
        raise RateLimitExceededError(
            "Too many requests",
            details={
                "scope": policy.scope,
                "limit": policy.limit,
                "retry_after_seconds": max(retry_after, 0),
            },
        )
