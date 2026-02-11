from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.core.cache import CacheService, cache, report_cache_key
from app.core.config import get_settings
from app.core.exceptions import DomainExceptionError
from app.domain.money import TransactionDirection
from app.domain.reporting import (
    CategoryBreakdownType,
    ReportGranularity,
    ReportPeriod,
    get_period_bounds,
    normalize_report_datetime,
    validate_date_range,
)
from app.persistence.repositories import ReportingRepository
from app.schemas.reporting import (
    AccountBalanceSummaryItem,
    CashflowPoint,
    CashflowTrendResponse,
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    CategoryTrendPoint,
    CategoryTrendResponse,
    DashboardSummaryResponse,
    NetWorthPoint,
    NetWorthTrendResponse,
)


class ReportingService:
    def __init__(
        self,
        reporting_repository: ReportingRepository,
        *,
        cache_service: CacheService = cache,
    ) -> None:
        self.reporting_repository = reporting_repository
        self.cache = cache_service
        self.settings = get_settings()

    async def get_dashboard_summary(
        self,
        user_id: UUID,
        period: ReportPeriod,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> DashboardSummaryResponse:
        if from_date or to_date:
            if from_date is None or to_date is None:
                raise DomainExceptionError("from_date and to_date must be provided together")
            from_date, to_date = validate_date_range(from_date, to_date)
            period = ReportPeriod.CUSTOM
        else:
            from_date, to_date = get_period_bounds(period)
        key = await self._build_cache_key(
            user_id,
            "dashboard",
            {
                "period": period.value,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
            },
        )
        cached = await self.cache.get_json(key)
        if cached is not None:
            return DashboardSummaryResponse.model_validate(cached)

        cashflow = await self.reporting_repository.get_cashflow_summary(user_id, from_date, to_date)
        accounts_raw = await self.reporting_repository.get_account_balances_summary(user_id)
        accounts = [AccountBalanceSummaryItem.model_validate(item) for item in accounts_raw]
        total_balance = sum((account.balance for account in accounts), start=Decimal("0"))

        response = DashboardSummaryResponse(
            period=period,
            from_date=from_date,
            to_date=to_date,
            income=cashflow["income"],
            expenses=cashflow["expenses"],
            net=cashflow["net"],
            total_balance=total_balance,
            account_count=len(accounts),
            accounts=accounts,
        )
        await self.cache.set_json(
            key,
            response.model_dump(mode="json"),
            ttl_seconds=self.settings.report_cache_ttl_seconds,
        )
        return response

    async def get_cashflow_trend(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        granularity: ReportGranularity,
    ) -> CashflowTrendResponse:
        from_date, to_date = validate_date_range(from_date, to_date)
        key = await self._build_cache_key(
            user_id,
            "cashflow",
            {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "granularity": granularity.value,
            },
        )
        cached = await self.cache.get_json(key)
        if cached is not None:
            return CashflowTrendResponse.model_validate(cached)

        rows = await self.reporting_repository.get_cashflow_by_period(
            user_id,
            from_date,
            to_date,
            granularity=granularity.value,
        )
        rows_by_period = {
            normalize_report_datetime(row["period"]): row
            for row in rows
            if isinstance(row["period"], datetime)
        }

        points: list[CashflowPoint] = []
        current = _align_to_bucket(from_date, granularity)
        step = _granularity_step(granularity)
        while current < to_date:
            row = rows_by_period.get(current)
            if row is None:
                income = Decimal("0")
                expenses = Decimal("0")
                net = Decimal("0")
            else:
                income = Decimal(row["income"])
                expenses = Decimal(row["expenses"])
                net = Decimal(row["net"])
            points.append(CashflowPoint(period=current, income=income, expenses=expenses, net=net))
            current = _align_to_bucket(current + step, granularity)

        response = CashflowTrendResponse(
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
            points=points,
        )
        await self.cache.set_json(
            key,
            response.model_dump(mode="json"),
            ttl_seconds=self.settings.report_cache_ttl_seconds,
        )
        return response

    async def get_net_worth_trend(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        granularity: ReportGranularity,
    ) -> NetWorthTrendResponse:
        from_date, to_date = validate_date_range(from_date, to_date)
        key = await self._build_cache_key(
            user_id,
            "net_worth",
            {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "granularity": granularity.value,
            },
        )
        cached = await self.cache.get_json(key)
        if cached is not None:
            return NetWorthTrendResponse.model_validate(cached)

        base_balance = await self.reporting_repository.get_net_worth_base(user_id, as_of=from_date)
        deltas = await self.reporting_repository.get_net_worth_deltas(
            user_id,
            from_date,
            to_date,
            granularity=granularity.value,
        )
        delta_by_period = {
            normalize_report_datetime(row["period"]): Decimal(row["delta"])
            for row in deltas
            if isinstance(row.get("period"), datetime)
        }

        points: list[NetWorthPoint] = []
        current = _align_to_bucket(from_date, granularity)
        step = _granularity_step(granularity)
        running = Decimal(base_balance)
        while current < to_date:
            running += Decimal(delta_by_period.get(current, Decimal("0")))
            points.append(NetWorthPoint(period=current, balance=running))
            current = _align_to_bucket(current + step, granularity)

        response = NetWorthTrendResponse(
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
            points=points,
        )
        await self.cache.set_json(
            key,
            response.model_dump(mode="json"),
            ttl_seconds=self.settings.report_cache_ttl_seconds,
        )
        return response

    async def get_category_breakdown(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        breakdown_type: CategoryBreakdownType,
        *,
        limit: int = 10,
    ) -> CategoryBreakdownResponse:
        from_date, to_date = validate_date_range(from_date, to_date)
        key = await self._build_cache_key(
            user_id,
            "categories",
            {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "type": breakdown_type.value,
                "limit": limit,
            },
        )
        cached = await self.cache.get_json(key)
        if cached is not None:
            return CategoryBreakdownResponse.model_validate(cached)

        direction = (
            TransactionDirection.OUT
            if breakdown_type == CategoryBreakdownType.EXPENSE
            else TransactionDirection.IN
        )
        rows = await self.reporting_repository.get_category_breakdown(
            user_id,
            from_date,
            to_date,
            direction=direction,
            limit=limit,
        )

        total = sum((Decimal(row["amount"]) for row in rows), start=Decimal("0"))
        items: list[CategoryBreakdownItem] = []
        for row in rows:
            amount = Decimal(row["amount"])
            percentage = float((amount / total * Decimal("100")) if total > 0 else Decimal("0"))
            items.append(
                CategoryBreakdownItem(
                    category_id=row["category_id"],
                    category_name=str(row["category_name"]),
                    color=row["color"] if isinstance(row["color"], str) else None,
                    icon=row["icon"] if isinstance(row["icon"], str) else None,
                    amount=amount,
                    percentage=percentage,
                )
            )

        response = CategoryBreakdownResponse(
            from_date=from_date,
            to_date=to_date,
            breakdown_type=breakdown_type,
            total=total,
            categories=items,
        )
        await self.cache.set_json(
            key,
            response.model_dump(mode="json"),
            ttl_seconds=self.settings.report_cache_ttl_seconds,
        )
        return response

    async def get_category_trend(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        granularity: ReportGranularity,
        breakdown_type: CategoryBreakdownType,
        *,
        limit: int = 5,
    ) -> CategoryTrendResponse:
        from_date, to_date = validate_date_range(from_date, to_date)
        key = await self._build_cache_key(
            user_id,
            "category_trend",
            {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "granularity": granularity.value,
                "type": breakdown_type.value,
                "limit": limit,
            },
        )
        cached = await self.cache.get_json(key)
        if cached is not None:
            return CategoryTrendResponse.model_validate(cached)

        direction = (
            TransactionDirection.OUT
            if breakdown_type == CategoryBreakdownType.EXPENSE
            else TransactionDirection.IN
        )
        top_categories = await self.reporting_repository.get_category_breakdown(
            user_id,
            from_date,
            to_date,
            direction=direction,
            limit=limit,
        )
        category_ids = [
            row["category_id"] for row in top_categories if row.get("category_id") is not None
        ]
        rows = await self.reporting_repository.get_category_trend(
            user_id,
            from_date,
            to_date,
            granularity=granularity.value,
            direction=direction,
            category_ids=category_ids if category_ids else None,
        )

        points = [
            CategoryTrendPoint(
                period=row["period"],
                category_id=row["category_id"],
                category_name=str(row["category_name"]),
                color=row["color"] if isinstance(row["color"], str) else None,
                icon=row["icon"] if isinstance(row["icon"], str) else None,
                amount=Decimal(row["amount"]),
            )
            for row in rows
            if isinstance(row["period"], datetime)
        ]

        response = CategoryTrendResponse(
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
            breakdown_type=breakdown_type,
            points=points,
        )
        await self.cache.set_json(
            key,
            response.model_dump(mode="json"),
            ttl_seconds=self.settings.report_cache_ttl_seconds,
        )
        return response

    async def invalidate_user_cache(self, user_id: UUID) -> None:
        await self.cache.bump_user_report_version(user_id)

    async def _build_cache_key(
        self,
        user_id: UUID,
        prefix: str,
        params: dict[str, str | int],
    ) -> str:
        version = await self.cache.get_user_report_version(user_id)
        return report_cache_key(user_id, version, prefix, params)


def _align_to_bucket(value: datetime, granularity: ReportGranularity) -> datetime:
    normalized = normalize_report_datetime(value)
    if granularity == ReportGranularity.DAY:
        return normalized.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity == ReportGranularity.WEEK:
        start = normalized - timedelta(days=normalized.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    # month
    return normalized.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _granularity_step(granularity: ReportGranularity) -> timedelta:
    if granularity == ReportGranularity.DAY:
        return timedelta(days=1)
    if granularity == ReportGranularity.WEEK:
        return timedelta(days=7)
    # month buckets are normalized to day=1 and can safely step by 32 days then re-align.
    return timedelta(days=32)
