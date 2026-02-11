from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.exceptions import AccountNotFoundError
from app.domain.account import (
    normalize_account_color,
    normalize_account_icon,
    normalize_goal_name,
    validate_account_currency,
    validate_account_name,
    validate_account_type,
    validate_goal_target_amount,
    validate_goal_target_date,
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
        color: str | None,
        icon: str | None,
        goal_name: str | None,
        goal_target_amount: Decimal | None,
        goal_target_date: date | None,
    ) -> Account:
        account = await self.account_repository.create(
            user_id=user_id,
            name=validate_account_name(name),
            account_type=validate_account_type(account_type).value,
            opening_balance=validate_opening_balance(opening_balance),
            currency=validate_account_currency(currency),
            color=normalize_account_color(color),
            icon=normalize_account_icon(icon),
            goal_name=normalize_goal_name(goal_name),
            goal_target_amount=validate_goal_target_amount(goal_target_amount),
            goal_target_date=validate_goal_target_date(goal_target_date),
        )
        await self.session.commit()
        await cache.bump_user_report_version(user_id)
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
        color: str | None = None,
        icon: str | None = None,
        goal_name: str | None = None,
        goal_target_amount: Decimal | None = None,
        goal_target_date: date | None = None,
    ) -> Account:
        updates: dict[str, object] = {}
        if name is not None:
            updates["name"] = validate_account_name(name)
        if account_type is not None:
            updates["account_type"] = validate_account_type(account_type).value
        if currency is not None:
            updates["currency"] = validate_account_currency(currency)
        if color is not None:
            updates["color"] = normalize_account_color(color)
        if icon is not None:
            updates["icon"] = normalize_account_icon(icon)
        if goal_name is not None:
            updates["goal_name"] = normalize_goal_name(goal_name)
        if goal_target_amount is not None:
            updates["goal_target_amount"] = validate_goal_target_amount(goal_target_amount)
        if goal_target_date is not None:
            updates["goal_target_date"] = validate_goal_target_date(goal_target_date)

        account = await self.account_repository.update(account_id, user_id, **updates)
        if account is None:
            raise AccountNotFoundError("Account not found")

        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        await self.session.refresh(account)
        return account

    async def deactivate_account(self, account_id: UUID, user_id: UUID) -> None:
        account = await self.account_repository.deactivate(account_id, user_id)
        if account is None:
            raise AccountNotFoundError("Account not found")
        await self.session.commit()
        await cache.bump_user_report_version(user_id)

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
