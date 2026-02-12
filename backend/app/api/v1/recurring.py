from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_current_user, get_recurring_service
from app.persistence.models import User
from app.schemas.recurring import (
    RecurringRunResponse,
    RecurringTransactionCreateRequest,
    RecurringTransactionListResponse,
    RecurringTransactionResponse,
    RecurringTransactionUpdateRequest,
)
from app.services.recurring_service import RecurringTransactionService

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.post("", response_model=RecurringTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    payload: RecurringTransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    recurring_service: Annotated[RecurringTransactionService, Depends(get_recurring_service)],
) -> RecurringTransactionResponse:
    recurring = await recurring_service.create_recurring_transaction(
        user_id=current_user.id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        amount=payload.amount,
        direction=payload.direction.value,
        cadence=payload.cadence,
        interval=payload.interval,
        start_at=payload.start_at,
        end_at=payload.end_at,
        merchant=payload.merchant,
        note=payload.note,
        tags=payload.tags,
    )
    return RecurringTransactionResponse.model_validate(recurring)


@router.get("", response_model=RecurringTransactionListResponse)
async def list_recurring(
    current_user: Annotated[User, Depends(get_current_user)],
    recurring_service: Annotated[RecurringTransactionService, Depends(get_recurring_service)],
    active_only: Annotated[bool, Query()] = False,
) -> RecurringTransactionListResponse:
    items = await recurring_service.list_recurring_transactions(
        current_user.id, active_only=active_only
    )
    return RecurringTransactionListResponse(
        items=[RecurringTransactionResponse.model_validate(item) for item in items]
    )


@router.get("/{recurring_id}", response_model=RecurringTransactionResponse)
async def get_recurring(
    recurring_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    recurring_service: Annotated[RecurringTransactionService, Depends(get_recurring_service)],
) -> RecurringTransactionResponse:
    recurring = await recurring_service.get_recurring_transaction(recurring_id, current_user.id)
    return RecurringTransactionResponse.model_validate(recurring)


@router.patch("/{recurring_id}", response_model=RecurringTransactionResponse)
async def update_recurring(
    recurring_id: UUID,
    payload: RecurringTransactionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    recurring_service: Annotated[RecurringTransactionService, Depends(get_recurring_service)],
) -> RecurringTransactionResponse:
    updates = payload.model_dump(exclude_unset=True)
    if "direction" in updates and payload.direction is not None:
        updates["direction"] = payload.direction.value
    if "cadence" in updates and payload.cadence is not None:
        updates["cadence"] = payload.cadence.value
    recurring = await recurring_service.update_recurring_transaction(
        recurring_id, current_user.id, **updates
    )
    return RecurringTransactionResponse.model_validate(recurring)


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurring_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    recurring_service: Annotated[RecurringTransactionService, Depends(get_recurring_service)],
) -> None:
    await recurring_service.delete_recurring_transaction(recurring_id, current_user.id)


@router.post("/run", response_model=RecurringRunResponse)
async def run_due(
    current_user: Annotated[User, Depends(get_current_user)],
    recurring_service: Annotated[RecurringTransactionService, Depends(get_recurring_service)],
) -> RecurringRunResponse:
    created, skipped = await recurring_service.run_due(current_user.id)
    return RecurringRunResponse(created=created, skipped=skipped)
