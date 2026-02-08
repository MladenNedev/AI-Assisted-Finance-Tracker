from decimal import Decimal

from app.core.exceptions import DomainExceptionError
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
