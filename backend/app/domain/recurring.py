from calendar import monthrange
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.core.exceptions import DomainExceptionError


class RecurringCadence(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


def normalize_start_at(start_at: datetime) -> datetime:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=UTC)
    return start_at.astimezone(UTC)


def normalize_end_at(end_at: datetime | None) -> datetime | None:
    if end_at is None:
        return None
    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=UTC)
    return end_at.astimezone(UTC)


def normalize_interval(interval: int) -> int:
    if interval <= 0:
        raise DomainExceptionError("Recurring interval must be greater than zero")
    return interval


def advance_run(current: datetime, cadence: RecurringCadence, interval: int) -> datetime:
    if cadence == RecurringCadence.DAILY:
        return current + timedelta(days=interval)
    if cadence == RecurringCadence.WEEKLY:
        return current + timedelta(weeks=interval)
    if cadence == RecurringCadence.MONTHLY:
        total_months = (current.year * 12 + current.month - 1) + interval
        year = total_months // 12
        month = total_months % 12 + 1
        day = min(current.day, monthrange(year, month)[1])
        return current.replace(year=year, month=month, day=day)
    raise DomainExceptionError("Unsupported cadence")


def align_next_run(
    start_at: datetime,
    cadence: RecurringCadence,
    interval: int,
    now: datetime,
) -> datetime:
    candidate = start_at
    if candidate > now:
        return candidate
    while candidate <= now:
        candidate = advance_run(candidate, cadence, interval)
    return candidate
