from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.category import normalize_category_color
from app.domain.money import AccountType, TransactionDirection, normalize_currency, quantize_money


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int


class AccountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    account_type: AccountType
    opening_balance: Decimal = Decimal("0")
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("opening_balance")
    @classmethod
    def normalize_opening_balance(cls, value: Decimal) -> Decimal:
        return quantize_money(value)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return normalize_currency(value)


class AccountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    account_type: AccountType | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_currency(value)


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    account_type: AccountType
    currency: str
    opening_balance: Decimal
    current_balance: Decimal = Decimal("0")
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountListResponse(PaginatedResponse):
    items: list[AccountResponse]


class AccountBalanceResponse(BaseModel):
    account_id: UUID
    balance: Decimal


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_income: bool = False
    color: str | None = Field(default=None, min_length=7, max_length=7)
    icon: str | None = Field(default=None, max_length=50)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        return normalize_category_color(value)


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_income: bool | None = None
    color: str | None = Field(default=None, min_length=7, max_length=7)
    icon: str | None = Field(default=None, max_length=50)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        return normalize_category_color(value)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    is_income: bool
    color: str | None
    icon: str | None
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(PaginatedResponse):
    items: list[CategoryResponse]


class TransactionCreateRequest(BaseModel):
    account_id: UUID
    category_id: UUID | None = None
    amount: Decimal = Field(gt=0)
    direction: TransactionDirection
    occurred_at: datetime
    merchant: str | None = Field(default=None, max_length=200)
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class TransactionUpdateRequest(BaseModel):
    category_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    direction: TransactionDirection | None = None
    occurred_at: datetime | None = None
    merchant: str | None = Field(default=None, max_length=200)
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return quantize_money(value)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    category_id: UUID | None
    amount: Decimal
    direction: TransactionDirection
    signed_amount: Decimal
    merchant: str | None
    note: str | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(PaginatedResponse):
    items: list[TransactionResponse]
