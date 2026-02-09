from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from app.core.exceptions import DomainExceptionError
from app.domain.money import quantize_money


class BudgetStatus(StrEnum):
    ON_TRACK = "on_track"
    WARNING = "warning"
    EXCEEDED = "exceeded"


def parse_budget_month(month: str) -> date:
    normalized = month.strip()
    try:
        parsed = datetime.strptime(normalized, "%Y-%m")
    except ValueError as exc:
        raise DomainExceptionError("Month must be in YYYY-MM format") from exc
    return date(parsed.year, parsed.month, 1)


def format_budget_month(month_start: date) -> str:
    return month_start.strftime("%Y-%m")


def validate_budget_limit(limit_amount: Decimal) -> Decimal:
    normalized = quantize_money(limit_amount)
    if normalized <= 0:
        raise DomainExceptionError("Budget limit must be greater than zero")
    return normalized


def get_month_bounds(month_start: date) -> tuple[datetime, datetime]:
    start = datetime(month_start.year, month_start.month, 1, tzinfo=UTC)
    if month_start.month == 12:
        end = datetime(month_start.year + 1, 1, 1, tzinfo=UTC)
    else:
        end = datetime(month_start.year, month_start.month + 1, 1, tzinfo=UTC)
    return start, end


def get_previous_month(month_start: date) -> date:
    if month_start.month == 1:
        return date(month_start.year - 1, 12, 1)
    return date(month_start.year, month_start.month - 1, 1)


@dataclass(frozen=True)
class BudgetProgressMetrics:
    percentage_used: float
    remaining_amount: Decimal
    status: BudgetStatus
    days_elapsed: int
    days_remaining: int
    daily_average: Decimal
    projected_spend: Decimal
    projected_diff: Decimal


def calculate_progress_metrics(
    *,
    limit_amount: Decimal,
    spent_amount: Decimal,
    month_start: date,
    now: datetime | None = None,
) -> BudgetProgressMetrics:
    if limit_amount <= 0:
        raise DomainExceptionError("Budget limit must be greater than zero")

    current = (now or datetime.now(UTC)).astimezone(UTC)
    start, end = get_month_bounds(month_start)
    days_in_month = monthrange(month_start.year, month_start.month)[1]

    if current < start:
        days_elapsed = 0
    elif current >= end:
        days_elapsed = days_in_month
    else:
        days_elapsed = (current.date() - start.date()).days + 1
    days_remaining = max(days_in_month - days_elapsed, 0)

    percentage_used = float((spent_amount / limit_amount) * Decimal("100"))
    remaining_amount = quantize_money(limit_amount - spent_amount)

    if percentage_used >= 100:
        status = BudgetStatus.EXCEEDED
    elif percentage_used >= 75:
        status = BudgetStatus.WARNING
    else:
        status = BudgetStatus.ON_TRACK

    if days_elapsed == 0:
        daily_average = Decimal("0.00")
    else:
        daily_average = quantize_money(spent_amount / Decimal(days_elapsed))
    projected_spend = quantize_money(daily_average * Decimal(days_in_month))
    projected_diff = quantize_money(projected_spend - limit_amount)

    return BudgetProgressMetrics(
        percentage_used=percentage_used,
        remaining_amount=remaining_amount,
        status=status,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        daily_average=daily_average,
        projected_spend=projected_spend,
        projected_diff=projected_diff,
    )
