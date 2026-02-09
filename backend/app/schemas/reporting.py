from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.domain.money import AccountType
from app.domain.reporting import CategoryBreakdownType, ReportGranularity, ReportPeriod


class AccountBalanceSummaryItem(BaseModel):
    account_id: UUID
    account_name: str
    account_type: AccountType
    currency: str
    balance: Decimal


class DashboardSummaryResponse(BaseModel):
    period: ReportPeriod
    from_date: datetime
    to_date: datetime
    income: Decimal
    expenses: Decimal
    net: Decimal
    total_balance: Decimal
    account_count: int
    accounts: list[AccountBalanceSummaryItem]


class CashflowPoint(BaseModel):
    period: datetime
    income: Decimal
    expenses: Decimal
    net: Decimal


class CashflowTrendResponse(BaseModel):
    from_date: datetime
    to_date: datetime
    granularity: ReportGranularity
    points: list[CashflowPoint]


class CategoryBreakdownItem(BaseModel):
    category_id: UUID | None
    category_name: str
    color: str | None
    icon: str | None
    amount: Decimal
    percentage: float


class CategoryBreakdownResponse(BaseModel):
    from_date: datetime
    to_date: datetime
    breakdown_type: CategoryBreakdownType
    total: Decimal
    categories: list[CategoryBreakdownItem]
