from datetime import date
from decimal import Decimal

from app.core.exceptions import DomainExceptionError
from app.domain.category import normalize_category_color, normalize_category_icon
from app.domain.money import AccountType, normalize_currency, quantize_money


def validate_account_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise DomainExceptionError("Account name cannot be empty")
    if len(normalized) > 100:
        raise DomainExceptionError("Account name must be 100 characters or fewer")
    return normalized


def validate_account_type(account_type: str | AccountType) -> AccountType:
    if isinstance(account_type, AccountType):
        return account_type
    try:
        return AccountType(account_type.upper())
    except ValueError as exc:
        raise DomainExceptionError("Invalid account type") from exc


def validate_opening_balance(opening_balance: Decimal) -> Decimal:
    return quantize_money(opening_balance)


def validate_account_currency(currency: str) -> str:
    return normalize_currency(currency)


def normalize_account_color(color: str | None) -> str | None:
    return normalize_category_color(color)


def normalize_account_icon(icon: str | None) -> str | None:
    return normalize_category_icon(icon)


def normalize_goal_name(name: str | None) -> str | None:
    if name is None:
        return None
    normalized = name.strip()
    if not normalized:
        return None
    if len(normalized) > 100:
        raise DomainExceptionError("Goal name must be 100 characters or fewer")
    return normalized


def validate_goal_target_amount(amount: Decimal | None) -> Decimal | None:
    if amount is None:
        return None
    if amount <= 0:
        raise DomainExceptionError("Goal target amount must be positive")
    return quantize_money(amount)


def validate_goal_target_date(target_date: date | None) -> date | None:
    if target_date is None:
        return None
    if target_date < date.today():
        raise DomainExceptionError("Goal target date cannot be in the past")
    return target_date
