from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_reporting_service
from app.domain.reporting import CategoryBreakdownType, ReportGranularity, ReportPeriod
from app.persistence.models import User
from app.schemas.reporting import (
    CashflowTrendResponse,
    CategoryBreakdownResponse,
    DashboardSummaryResponse,
)
from app.services.reporting_service import ReportingService

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    period: Annotated[ReportPeriod, Query()] = ReportPeriod.MONTH,
) -> DashboardSummaryResponse:
    return await reporting_service.get_dashboard_summary(current_user.id, period)


@router.get("/cashflow", response_model=CashflowTrendResponse)
async def get_cashflow_trend(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    from_date: Annotated[datetime, Query()],
    to_date: Annotated[datetime, Query()],
    granularity: Annotated[ReportGranularity, Query()] = ReportGranularity.DAY,
) -> CashflowTrendResponse:
    return await reporting_service.get_cashflow_trend(
        current_user.id,
        from_date,
        to_date,
        granularity,
    )


@router.get("/categories", response_model=CategoryBreakdownResponse)
async def get_category_breakdown(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    from_date: Annotated[datetime, Query()],
    to_date: Annotated[datetime, Query()],
    breakdown_type: Annotated[CategoryBreakdownType, Query()] = CategoryBreakdownType.EXPENSE,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> CategoryBreakdownResponse:
    return await reporting_service.get_category_breakdown(
        current_user.id,
        from_date,
        to_date,
        breakdown_type,
        limit=limit,
    )
