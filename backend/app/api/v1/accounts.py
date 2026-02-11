from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import get_account_service, get_current_user
from app.persistence.models import User
from app.schemas.ledger import (
    AccountBalanceResponse,
    AccountCreateRequest,
    AccountListResponse,
    AccountResponse,
    AccountUpdateRequest,
)
from app.services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _serialize_account(account: object, current_balance: object) -> AccountResponse:
    payload = AccountResponse.model_validate(account)
    return payload.model_copy(update={"current_balance": current_balance})


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    account = await account_service.create_account(
        user_id=current_user.id,
        name=payload.name,
        account_type=payload.account_type.value,
        opening_balance=payload.opening_balance,
        currency=payload.currency,
        color=payload.color,
        icon=payload.icon,
        goal_name=payload.goal_name,
        goal_target_amount=payload.goal_target_amount,
        goal_target_date=payload.goal_target_date,
    )
    balance = await account_service.get_balance(account.id, current_user.id)
    return _serialize_account(account, balance)


@router.get("", response_model=AccountListResponse)
async def list_accounts(
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
    include_inactive: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AccountListResponse:
    accounts, total = await account_service.list_accounts(
        user_id=current_user.id,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    balances = await account_service.get_balances(accounts)
    return AccountListResponse(
        items=[_serialize_account(account, balances[account.id]) for account in accounts],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    account = await account_service.get_account(account_id, current_user.id)
    balance = await account_service.get_balance(account_id, current_user.id)
    return _serialize_account(account, balance)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: UUID,
    payload: AccountUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountResponse:
    account = await account_service.update_account(
        account_id=account_id,
        user_id=current_user.id,
        name=payload.name,
        account_type=payload.account_type.value if payload.account_type else None,
        currency=payload.currency,
        color=payload.color,
        icon=payload.icon,
        goal_name=payload.goal_name,
        goal_target_amount=payload.goal_target_amount,
        goal_target_date=payload.goal_target_date,
    )
    balance = await account_service.get_balance(account.id, current_user.id)
    return _serialize_account(account, balance)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> Response:
    await account_service.deactivate_account(account_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{account_id}/balance", response_model=AccountBalanceResponse)
async def get_account_balance(
    account_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    account_service: Annotated[AccountService, Depends(get_account_service)],
) -> AccountBalanceResponse:
    balance = await account_service.get_balance(account_id, current_user.id)
    return AccountBalanceResponse(account_id=account_id, balance=balance)
