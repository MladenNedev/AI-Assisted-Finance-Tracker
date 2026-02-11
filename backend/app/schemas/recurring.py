from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.money import TransactionDirection, quantize_money
from app.domain.recurring import RecurringCadence


class RecurringTransactionCreateRequest(BaseModel):
    account_id: UUID
    category_id: UUID | None = None
    amount: Decimal = Field(gt=0)
    direction: TransactionDirection
    cadence: RecurringCadence
    interval: int = Field(default=1, ge=1)
    start_at: datetime
    end_at: datetime | None = None
    merchant: str | None = Field(default=None, max_length=200)
    note: str | None = None
    tags: list[str] | None = None

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class RecurringTransactionUpdateRequest(BaseModel):
    category_id: UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    direction: TransactionDirection | None = None
    cadence: RecurringCadence | None = None
    interval: int | None = Field(default=None, ge=1)
    start_at: datetime | None = None
    end_at: datetime | None = None
    merchant: str | None = Field(default=None, max_length=200)
    note: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None

    @field_validator("amount")
    @classmethod
    def normalize_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return quantize_money(value)


class RecurringTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    account_id: UUID
    category_id: UUID | None
    amount: Decimal
    direction: TransactionDirection
    cadence: RecurringCadence
    interval: int
    start_at: datetime
    next_run_at: datetime
    end_at: datetime | None
    merchant: str | None
    note: str | None
    tags: list[str] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RecurringTransactionListResponse(BaseModel):
    items: list[RecurringTransactionResponse]


class RecurringRunResponse(BaseModel):
    created: int
    skipped: int
