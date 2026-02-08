from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.core.exceptions import DomainExceptionError

TWOPLACES = Decimal("0.01")


class AccountType(StrEnum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CREDIT_CARD = "CREDIT_CARD"
    CASH = "CASH"
    INVESTMENT = "INVESTMENT"


class TransactionDirection(StrEnum):
    IN = "IN"
    OUT = "OUT"


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def normalize_currency(currency: str) -> str:
    normalized = currency.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise DomainExceptionError("Currency must be a 3-letter ISO code")
    return normalized
