from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccountNotFoundError
from app.domain.account import (
    validate_account_currency,
    validate_account_name,
    validate_account_type,
    validate_opening_balance,
)
from app.persistence.models import Account
from app.persistence.repositories import AccountRepository


class AccountService:
    def __init__(self, session: AsyncSession, account_repository: AccountRepository) -> None:
        self.session = session
        self.account_repository = account_repository

    async def create_account(
        self,
        user_id: UUID,
        name: str,
        account_type: str,
        opening_balance: Decimal,
        currency: str,
    ) -> Account:
        account = await self.account_repository.create(
            user_id=user_id,
            name=validate_account_name(name),
            account_type=validate_account_type(account_type).value,
            opening_balance=validate_opening_balance(opening_balance),
            currency=validate_account_currency(currency),
        )
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def list_accounts(
        self,
        user_id: UUID,
        *,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Account], int]:
        accounts = await self.account_repository.list_by_user(
            user_id=user_id,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )
        total = await self.account_repository.count_by_user(
            user_id=user_id,
            include_inactive=include_inactive,
        )
        return accounts, total

    async def get_account(self, account_id: UUID, user_id: UUID) -> Account:
        account = await self.account_repository.get_by_id(
            account_id, user_id, include_inactive=True
        )
        if account is None:
            raise AccountNotFoundError("Account not found")
        return account

    async def update_account(
        self,
        account_id: UUID,
        user_id: UUID,
        *,
        name: str | None = None,
        account_type: str | None = None,
        currency: str | None = None,
    ) -> Account:
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = validate_account_name(name)
        if account_type is not None:
            updates["account_type"] = validate_account_type(account_type).value
        if currency is not None:
            updates["currency"] = validate_account_currency(currency)

        account = await self.account_repository.update(account_id, user_id, **updates)
        if account is None:
            raise AccountNotFoundError("Account not found")

        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def deactivate_account(self, account_id: UUID, user_id: UUID) -> None:
        account = await self.account_repository.deactivate(account_id, user_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        await self.session.commit()

    async def get_balance(self, account_id: UUID, user_id: UUID) -> Decimal:
        account = await self.account_repository.get_by_id(
            account_id, user_id, include_inactive=True
        )
        if account is None:
            raise AccountNotFoundError("Account not found")

        totals = await self.account_repository.get_balances([account_id])
        return validate_opening_balance(
            account.opening_balance + totals.get(account_id, Decimal("0"))
        )

    async def get_balances(self, accounts: list[Account]) -> dict[UUID, Decimal]:
        account_ids = [account.id for account in accounts]
        totals = await self.account_repository.get_balances(account_ids)
        balances: dict[UUID, Decimal] = {}
        for account in accounts:
            balances[account.id] = validate_opening_balance(
                account.opening_balance + totals.get(account.id, Decimal("0"))
            )
        return balances
