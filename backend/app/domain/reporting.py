from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.core.exceptions import DomainExceptionError


class ReportPeriod(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    CUSTOM = "custom"


class ReportGranularity(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class CategoryBreakdownType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


def normalize_report_datetime(value: datetime) -> datetime:
    normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC)


def validate_date_range(from_date: datetime, to_date: datetime) -> tuple[datetime, datetime]:
    normalized_from = normalize_report_datetime(from_date)
    normalized_to = normalize_report_datetime(to_date)
    if normalized_from > normalized_to:
        raise DomainExceptionError("from_date must be before to_date")
    if normalized_to - normalized_from > timedelta(days=365 * 2):
        raise DomainExceptionError("Date range cannot exceed 2 years")
    return normalized_from, normalized_to


def get_period_bounds(
    period: ReportPeriod, *, reference_date: datetime | None = None
) -> tuple[datetime, datetime]:
    reference = normalize_report_datetime(reference_date or datetime.now(UTC))

    if period == ReportPeriod.DAY:
        start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end

    if period == ReportPeriod.WEEK:
        start = reference - timedelta(days=reference.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)
        return start, end

    if period == ReportPeriod.MONTH:
        start = reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    if period == ReportPeriod.YEAR:
        start = reference.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
        return start, end

    raise DomainExceptionError("Unsupported report period")
