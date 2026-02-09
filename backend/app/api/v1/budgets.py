from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_budget_service, get_current_user
from app.core.exceptions import DomainExceptionError
from app.domain.budget import format_budget_month
from app.persistence.models import Budget, User
from app.schemas.budget import (
    BudgetCreateRequest,
    BudgetListResponse,
    BudgetProgressItem,
    BudgetProgressResponse,
    BudgetResponse,
    BudgetUpdateRequest,
    CopyBudgetsRequest,
    CopyBudgetsResponse,
)
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _serialize_budget(budget: Budget) -> BudgetResponse:
    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        month=format_budget_month(budget.month_start),
        limit_amount=budget.limit_amount,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    payload: BudgetCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetResponse:
    budget = await budget_service.create_budget(
        user_id=current_user.id,
        category_id=payload.category_id,
        month=payload.month,
        limit_amount=payload.limit_amount,
    )
    return _serialize_budget(budget)


@router.get("", response_model=BudgetListResponse)
async def list_budgets(
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BudgetListResponse:
    _, budgets, total = await budget_service.list_budgets(
        user_id=current_user.id, month=month, limit=limit, offset=offset
    )
    return BudgetListResponse(
        items=[_serialize_budget(budget) for budget in budgets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/progress", response_model=BudgetProgressResponse)
async def get_budget_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> BudgetProgressResponse:
    month_start, progress_rows = await budget_service.get_budget_progress(
        user_id=current_user.id, month=month
    )
    formatted_month = format_budget_month(month_start)
    return BudgetProgressResponse(
        month=formatted_month,
        items=[
            BudgetProgressItem.model_validate({**row, "month": formatted_month})
            for row in progress_rows
        ],
    )


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetResponse:
    budget = await budget_service.get_budget(budget_id, current_user.id)
    return _serialize_budget(budget)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    payload: BudgetUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> BudgetResponse:
    if payload.limit_amount is None:
        raise DomainExceptionError("No fields were provided for update")
    budget = await budget_service.update_budget(
        budget_id=budget_id,
        user_id=current_user.id,
        limit_amount=payload.limit_amount,
    )
    return _serialize_budget(budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> Response:
    await budget_service.delete_budget(budget_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/copy-previous", response_model=CopyBudgetsResponse)
async def copy_previous_month_budgets(
    payload: CopyBudgetsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    budget_service: Annotated[BudgetService, Depends(get_budget_service)],
) -> CopyBudgetsResponse:
    source_month, target_month, created_count = await budget_service.copy_previous_month(
        user_id=current_user.id,
        target_month=payload.target_month,
    )
    return CopyBudgetsResponse(
        source_month=format_budget_month(source_month),
        target_month=format_budget_month(target_month),
        created_count=created_count,
    )
