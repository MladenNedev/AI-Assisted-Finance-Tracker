from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.exceptions import (
    BudgetAlreadyExistsError,
    BudgetNotFoundError,
    CategoryNotFoundError,
    InvalidBudgetCategoryError,
)
from app.domain.budget import (
    calculate_progress_metrics,
    get_month_bounds,
    get_previous_month,
    parse_budget_month,
    validate_budget_limit,
)
from app.persistence.models import Budget
from app.persistence.repositories import BudgetRepository, CategoryRepository


class BudgetService:
    def __init__(
        self,
        session: AsyncSession,
        budget_repository: BudgetRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self.session = session
        self.budget_repository = budget_repository
        self.category_repository = category_repository

    async def create_budget(
        self,
        user_id: UUID,
        category_id: UUID,
        month: str,
        limit_amount: Decimal,
    ) -> Budget:
        month_start = parse_budget_month(month)
        normalized_limit = validate_budget_limit(limit_amount)

        category = await self.category_repository.get_by_id(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
        if category.is_income:
            raise InvalidBudgetCategoryError("Budgets currently support expense categories only")

        existing = await self.budget_repository.get_by_category_month(
            user_id, category_id, month_start
        )
        if existing is not None:
            raise BudgetAlreadyExistsError("Budget already exists for this category and month")

        try:
            budget = await self.budget_repository.create(
                user_id=user_id,
                category_id=category_id,
                month_start=month_start,
                limit_amount=normalized_limit,
            )
            await self.session.commit()
            await cache.bump_user_report_version(user_id)
        except IntegrityError as exc:
            await self.session.rollback()
            raise BudgetAlreadyExistsError(
                "Budget already exists for this category and month"
            ) from exc

        await self.session.refresh(budget)
        return budget

    async def list_budgets(
        self,
        user_id: UUID,
        *,
        month: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[date, list[Budget], int]:
        month_start = parse_budget_month(month) if month else _current_month_start()
        budgets = await self.budget_repository.list_by_month(
            user_id=user_id,
            month_start=month_start,
            limit=limit,
            offset=offset,
        )
        total = await self.budget_repository.count_by_month(user_id, month_start)
        return month_start, budgets, total

    async def get_budget(self, budget_id: UUID, user_id: UUID) -> Budget:
        budget = await self.budget_repository.get_by_id(budget_id, user_id)
        if budget is None:
            raise BudgetNotFoundError("Budget not found")
        return budget

    async def update_budget(
        self,
        budget_id: UUID,
        user_id: UUID,
        *,
        limit_amount: Decimal,
    ) -> Budget:
        budget = await self.budget_repository.update_limit(
            budget_id, user_id, validate_budget_limit(limit_amount)
        )
        if budget is None:
            raise BudgetNotFoundError("Budget not found")
        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        await self.session.refresh(budget)
        return budget

    async def delete_budget(self, budget_id: UUID, user_id: UUID) -> None:
        deleted = await self.budget_repository.delete(budget_id, user_id)
        if not deleted:
            raise BudgetNotFoundError("Budget not found")
        await self.session.commit()
        await cache.bump_user_report_version(user_id)

    async def copy_previous_month(self, user_id: UUID, target_month: str) -> tuple[date, date, int]:
        target_month_start = parse_budget_month(target_month)
        source_month_start = get_previous_month(target_month_start)

        source_budgets = await self.budget_repository.list_all_by_month(user_id, source_month_start)
        if not source_budgets:
            return source_month_start, target_month_start, 0

        existing_target = await self.budget_repository.list_all_by_month(
            user_id, target_month_start
        )
        existing_categories = {budget.category_id for budget in existing_target}

        created_count = 0
        for source_budget in source_budgets:
            if source_budget.category_id in existing_categories:
                continue
            await self.budget_repository.create(
                user_id=user_id,
                category_id=source_budget.category_id,
                month_start=target_month_start,
                limit_amount=source_budget.limit_amount,
            )
            created_count += 1

        if created_count > 0:
            await self.session.commit()
            await cache.bump_user_report_version(user_id)
        return source_month_start, target_month_start, created_count

    async def get_budget_progress(
        self, user_id: UUID, *, month: str | None = None
    ) -> tuple[date, list[dict[str, object]]]:
        month_start = parse_budget_month(month) if month else _current_month_start()
        range_start, range_end = get_month_bounds(month_start)
        rows = await self.budget_repository.list_month_progress(
            user_id=user_id,
            month_start=month_start,
            occurred_from=range_start,
            occurred_to=range_end,
        )

        now = datetime.now(UTC)
        output: list[dict[str, object]] = []
        for row in rows:
            limit_amount = row["limit_amount"]
            spent_amount = row["spent_amount"]
            if not isinstance(limit_amount, Decimal) or not isinstance(spent_amount, Decimal):
                continue
            metrics = calculate_progress_metrics(
                limit_amount=limit_amount,
                spent_amount=spent_amount,
                month_start=month_start,
                now=now,
            )
            output.append(
                {
                    **row,
                    "remaining_amount": metrics.remaining_amount,
                    "percentage_used": metrics.percentage_used,
                    "status": metrics.status,
                    "days_elapsed": metrics.days_elapsed,
                    "days_remaining": metrics.days_remaining,
                    "daily_average": metrics.daily_average,
                    "projected_spend": metrics.projected_spend,
                    "projected_diff": metrics.projected_diff,
                }
            )
        return month_start, output


def _current_month_start() -> date:
    now = datetime.now(UTC).date()
    return date(now.year, now.month, 1)
