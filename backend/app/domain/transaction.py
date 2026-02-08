from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.exceptions import DomainExceptionError
from app.domain.money import TransactionDirection, quantize_money


def validate_transaction_amount(amount: Decimal) -> Decimal:
    normalized = quantize_money(amount)
    if normalized <= 0:
        raise DomainExceptionError("Transaction amount must be positive")
    return normalized


def validate_transaction_direction(direction: str | TransactionDirection) -> TransactionDirection:
    if isinstance(direction, TransactionDirection):
        return direction
    try:
        return TransactionDirection(direction.upper())
    except ValueError as exc:
        raise DomainExceptionError("Transaction direction must be IN or OUT") from exc


def normalize_occurred_at(occurred_at: datetime) -> datetime:
    normalized = occurred_at if occurred_at.tzinfo else occurred_at.replace(tzinfo=UTC)
    normalized = normalized.astimezone(UTC)
    # Allow a small clock skew window.
    if normalized > datetime.now(UTC) + timedelta(minutes=1):
        raise DomainExceptionError("Transaction date cannot be in the future")
    return normalized


def normalize_merchant(merchant: str | None) -> str | None:
    if merchant is None:
        return None
    normalized = merchant.strip()
    if not normalized:
        return None
    if len(normalized) > 200:
        raise DomainExceptionError("Merchant must be 200 characters or fewer")
    return normalized


def normalize_note(note: str | None) -> str | None:
    if note is None:
        return None
    normalized = note.strip()
    return normalized or None
