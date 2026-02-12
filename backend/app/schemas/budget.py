from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.budget import BudgetStatus
from app.domain.money import quantize_money
from app.schemas.ledger import PaginatedResponse


class BudgetCreateRequest(BaseModel):
    category_id: UUID
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    limit_amount: Decimal = Field(gt=0)
    rollover_enabled: bool = False

    @field_validator("limit_amount")
    @classmethod
    def normalize_limit_amount(cls, value: Decimal) -> Decimal:
        return quantize_money(value)


class BudgetUpdateRequest(BaseModel):
    limit_amount: Decimal | None = Field(default=None, gt=0)
    rollover_enabled: bool | None = None

    @field_validator("limit_amount")
    @classmethod
    def normalize_limit_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        return quantize_money(value)


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    category_id: UUID
    month: str
    limit_amount: Decimal
    rollover_enabled: bool
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(PaginatedResponse):
    items: list[BudgetResponse]


class BudgetProgressItem(BaseModel):
    budget_id: UUID
    category_id: UUID
    category_name: str
    category_color: str | None
    category_icon: str | None
    month: str
    limit_amount: Decimal
    effective_limit: Decimal
    rollover_amount: Decimal
    rollover_enabled: bool
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: float
    status: BudgetStatus
    days_elapsed: int
    days_remaining: int
    daily_average: Decimal
    projected_spend: Decimal
    projected_diff: Decimal


class BudgetProgressResponse(BaseModel):
    month: str
    items: list[BudgetProgressItem]


class CopyBudgetsRequest(BaseModel):
    target_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class CopyBudgetsResponse(BaseModel):
    source_month: str
    target_month: str
    created_count: int


class BudgetSummaryItem(BaseModel):
    month: str
    budgeted: Decimal
    spent: Decimal
    variance: Decimal


class BudgetSummaryResponse(BaseModel):
    items: list[BudgetSummaryItem]
