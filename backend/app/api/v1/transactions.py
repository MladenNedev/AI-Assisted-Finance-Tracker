from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_current_user, get_transaction_service
from app.persistence.models import User
from app.schemas.ledger import (
    TransactionCreateRequest,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdateRequest,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    transaction = await transaction_service.create_transaction(
        user_id=current_user.id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        amount=payload.amount,
        direction=payload.direction.value,
        occurred_at=payload.occurred_at,
        merchant=payload.merchant,
        note=payload.note,
    )
    return TransactionResponse.model_validate(transaction)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    account_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionListResponse:
    transactions, total = await transaction_service.list_transactions(
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(transaction) for transaction in transactions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/export", response_class=Response)
async def export_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
    account_id: Annotated[UUID | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    csv_payload = await transaction_service.export_transactions_csv(
        user_id=current_user.id,
        account_id=account_id,
        category_id=category_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        search=search,
        limit=limit,
        offset=offset,
    )
    filename = f"transactions_{current_user.id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_payload, media_type="text/csv", headers=headers)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    transaction = await transaction_service.get_transaction(transaction_id, current_user.id)
    return TransactionResponse.model_validate(transaction)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> TransactionResponse:
    updates = payload.model_dump(exclude_unset=True)
    if "direction" in updates and payload.direction is not None:
        updates["direction"] = payload.direction.value
    transaction = await transaction_service.update_transaction(
        transaction_id=transaction_id, user_id=current_user.id, **updates
    )
    return TransactionResponse.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    transaction_service: Annotated[TransactionService, Depends(get_transaction_service)],
) -> Response:
    await transaction_service.delete_transaction(transaction_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
