from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.deps import get_current_user, get_reporting_service
from app.core.config import get_settings
from app.core.exceptions import DomainExceptionError
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.domain.reporting import (
    CategoryBreakdownType,
    ReportExportType,
    ReportGranularity,
    ReportPeriod,
)
from app.persistence.models import User
from app.schemas.reporting import (
    CashflowTrendResponse,
    CategoryBreakdownResponse,
    CategoryTrendResponse,
    DashboardSummaryResponse,
    NetWorthTrendResponse,
)
from app.services.reporting_service import ReportingService

router = APIRouter(prefix="/reporting", tags=["reporting"])


async def enforce_reporting_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    await enforce_rate_limit(
        request,
        RateLimitPolicy(
            scope="reporting",
            limit=settings.rate_limit_reporting_limit,
            window_seconds=settings.rate_limit_reporting_window_seconds,
            fail_closed_on_unavailable=settings.rate_limit_reporting_fail_closed,
        ),
    )


@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    _: Annotated[None, Depends(enforce_reporting_rate_limit)],
    period: Annotated[ReportPeriod, Query()] = ReportPeriod.MONTH,
    from_date: Annotated[datetime | None, Query()] = None,
    to_date: Annotated[datetime | None, Query()] = None,
) -> DashboardSummaryResponse:
    return await reporting_service.get_dashboard_summary(
        current_user.id,
        period,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/cashflow", response_model=CashflowTrendResponse)
async def get_cashflow_trend(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    _: Annotated[None, Depends(enforce_reporting_rate_limit)],
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
    _: Annotated[None, Depends(enforce_reporting_rate_limit)],
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


@router.get("/category-trend", response_model=CategoryTrendResponse)
async def get_category_trend(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    _: Annotated[None, Depends(enforce_reporting_rate_limit)],
    from_date: Annotated[datetime, Query()],
    to_date: Annotated[datetime, Query()],
    granularity: Annotated[ReportGranularity, Query()] = ReportGranularity.WEEK,
    breakdown_type: Annotated[CategoryBreakdownType, Query()] = CategoryBreakdownType.EXPENSE,
    limit: Annotated[int, Query(ge=1, le=10)] = 5,
) -> CategoryTrendResponse:
    return await reporting_service.get_category_trend(
        current_user.id,
        from_date,
        to_date,
        granularity,
        breakdown_type,
        limit=limit,
    )


@router.get("/net-worth", response_model=NetWorthTrendResponse)
async def get_net_worth_trend(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    _: Annotated[None, Depends(enforce_reporting_rate_limit)],
    from_date: Annotated[datetime, Query()],
    to_date: Annotated[datetime, Query()],
    granularity: Annotated[ReportGranularity, Query()] = ReportGranularity.MONTH,
) -> NetWorthTrendResponse:
    return await reporting_service.get_net_worth_trend(
        current_user.id,
        from_date,
        to_date,
        granularity,
    )


@router.get("/export", response_class=Response)
async def export_reporting_csv(
    current_user: Annotated[User, Depends(get_current_user)],
    reporting_service: Annotated[ReportingService, Depends(get_reporting_service)],
    _: Annotated[None, Depends(enforce_reporting_rate_limit)],
    report_type: Annotated[ReportExportType, Query()],
    from_date: Annotated[datetime | None, Query()] = None,
    to_date: Annotated[datetime | None, Query()] = None,
    granularity: Annotated[ReportGranularity, Query()] = ReportGranularity.DAY,
    breakdown_type: Annotated[CategoryBreakdownType, Query()] = CategoryBreakdownType.EXPENSE,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    period: Annotated[ReportPeriod, Query()] = ReportPeriod.MONTH,
) -> Response:
    if report_type == ReportExportType.DASHBOARD:
        csv_payload = await reporting_service.export_dashboard_csv(
            current_user.id,
            period,
            from_date=from_date,
            to_date=to_date,
        )
    else:
        if from_date is None or to_date is None:
            raise DomainExceptionError("from_date and to_date are required for this export")
        if report_type == ReportExportType.CASHFLOW:
            csv_payload = await reporting_service.export_cashflow_csv(
                current_user.id, from_date, to_date, granularity
            )
        elif report_type == ReportExportType.CATEGORIES:
            csv_payload = await reporting_service.export_category_breakdown_csv(
                current_user.id,
                from_date,
                to_date,
                breakdown_type,
                limit=limit,
            )
        elif report_type == ReportExportType.CATEGORY_TREND:
            csv_payload = await reporting_service.export_category_trend_csv(
                current_user.id,
                from_date,
                to_date,
                granularity,
                breakdown_type,
                limit=limit,
            )
        else:
            raise DomainExceptionError("Unsupported report export type")

    filename = f"report_{report_type.value}_{current_user.id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_payload, media_type="text/csv", headers=headers)
