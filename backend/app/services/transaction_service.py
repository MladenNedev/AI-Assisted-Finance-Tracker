import csv
import io
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.exceptions import (
    AccountNotFoundError,
    CategoryNotFoundError,
    TransactionNotFoundError,
)
from app.domain.transaction import (
    normalize_merchant,
    normalize_note,
    normalize_occurred_at,
    validate_transaction_amount,
    validate_transaction_direction,
)
from app.persistence.models import Transaction
from app.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    TransactionRepository,
)

_UNSET = object()


class TransactionService:
    def __init__(
        self,
        session: AsyncSession,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        category_repository: CategoryRepository,
    ) -> None:
        self.session = session
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository

    async def create_transaction(
        self,
        user_id: UUID,
        account_id: UUID,
        amount: Decimal,
        direction: str,
        occurred_at: datetime,
        merchant: str | None,
        note: str | None,
        category_id: UUID | None = None,
    ) -> Transaction:
        await self._ensure_account_access(user_id, account_id)
        await self._ensure_category_access(user_id, category_id)

        transaction = await self.transaction_repository.create(
            account_id=account_id,
            category_id=category_id,
            amount=validate_transaction_amount(amount),
            direction=validate_transaction_direction(direction).value,
            occurred_at=normalize_occurred_at(occurred_at),
            merchant=normalize_merchant(merchant),
            note=normalize_note(note),
        )
        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        await self.session.refresh(transaction)
        return transaction

    async def get_transaction(self, transaction_id: UUID, user_id: UUID) -> Transaction:
        transaction = await self.transaction_repository.get_by_id(transaction_id, user_id)
        if transaction is None:
            raise TransactionNotFoundError("Transaction not found")
        return transaction

    async def list_transactions(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        if account_id is not None:
            await self._ensure_account_access(user_id, account_id)
        if category_id is not None:
            await self._ensure_category_access(user_id, category_id)

        normalized_from = normalize_occurred_at(occurred_from) if occurred_from else None
        normalized_to = normalize_occurred_at(occurred_to) if occurred_to else None

        normalized_search = search.strip() if search else None
        if normalized_search == "":
            normalized_search = None

        transactions = await self.transaction_repository.list_by_user(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            occurred_from=normalized_from,
            occurred_to=normalized_to,
            search=normalized_search,
            limit=limit,
            offset=offset,
        )
        total = await self.transaction_repository.count_by_user(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            occurred_from=normalized_from,
            occurred_to=normalized_to,
            search=normalized_search,
        )
        return transactions, total

    async def export_transactions_csv(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        search: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> str:
        if account_id is not None:
            await self._ensure_account_access(user_id, account_id)
        if category_id is not None:
            await self._ensure_category_access(user_id, category_id)

        normalized_from = normalize_occurred_at(occurred_from) if occurred_from else None
        normalized_to = normalize_occurred_at(occurred_to) if occurred_to else None

        normalized_search = search.strip() if search else None
        if normalized_search == "":
            normalized_search = None

        transactions = await self.transaction_repository.list_by_user(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            occurred_from=normalized_from,
            occurred_to=normalized_to,
            search=normalized_search,
            limit=limit,
            offset=offset,
        )

        accounts = await self.account_repository.list_by_user(
            user_id,
            include_inactive=True,
            limit=5000,
            offset=0,
        )
        categories = await self.category_repository.list_by_user(user_id, limit=5000, offset=0)
        account_lookup = {account.id: account for account in accounts}
        category_lookup = {category.id: category for category in categories}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "occurred_at",
                "direction",
                "amount",
                "account_name",
                "account_id",
                "category_name",
                "category_id",
                "merchant",
                "note",
            ]
        )

        for transaction in transactions:
            account = account_lookup.get(transaction.account_id)
            category = (
                category_lookup.get(transaction.category_id) if transaction.category_id else None
            )
            writer.writerow(
                [
                    transaction.occurred_at.isoformat(),
                    transaction.direction,
                    f"{transaction.amount:.2f}",
                    account.name if account else "",
                    str(transaction.account_id),
                    category.name if category else "",
                    str(transaction.category_id) if transaction.category_id else "",
                    transaction.merchant or "",
                    transaction.note or "",
                ]
            )

        return output.getvalue()

    async def update_transaction(
        self,
        transaction_id: UUID,
        user_id: UUID,
        **updates: object,
    ) -> Transaction:
        existing = await self.transaction_repository.get_by_id(transaction_id, user_id)
        if existing is None:
            raise TransactionNotFoundError("Transaction not found")

        amount = updates.get("amount", existing.amount)
        direction = updates.get("direction", existing.direction)
        occurred_at = updates.get("occurred_at", existing.occurred_at)
        merchant = updates.get("merchant", _UNSET)
        note = updates.get("note", _UNSET)
        category_id = updates.get("category_id", _UNSET)

        resolved_updates: dict[str, object] = {
            "amount": validate_transaction_amount(
                amount if isinstance(amount, Decimal) else Decimal(amount)
            ),
            "direction": validate_transaction_direction(str(direction)).value,
            "occurred_at": normalize_occurred_at(
                occurred_at
                if isinstance(occurred_at, datetime)
                else datetime.fromisoformat(str(occurred_at))
            ),
        }

        if merchant is not _UNSET:
            resolved_updates["merchant"] = normalize_merchant(
                merchant if isinstance(merchant, str) else None
            )
        if note is not _UNSET:
            resolved_updates["note"] = normalize_note(note if isinstance(note, str) else None)
        if category_id is not _UNSET:
            typed_category_id = category_id if isinstance(category_id, UUID) else None
            await self._ensure_category_access(user_id, typed_category_id)
            resolved_updates["category_id"] = typed_category_id

        updated = await self.transaction_repository.update(
            transaction_id, user_id, **resolved_updates
        )
        if updated is None:
            raise TransactionNotFoundError("Transaction not found")

        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        await self.session.refresh(updated)
        return updated

    async def delete_transaction(self, transaction_id: UUID, user_id: UUID) -> None:
        was_deleted = await self.transaction_repository.delete(transaction_id, user_id)
        if not was_deleted:
            raise TransactionNotFoundError("Transaction not found")
        await self.session.commit()
        await cache.bump_user_report_version(user_id)

    async def _ensure_account_access(self, user_id: UUID, account_id: UUID) -> None:
        account = await self.account_repository.get_by_id(
            account_id, user_id, include_inactive=False
        )
        if account is None:
            raise AccountNotFoundError("Account not found")

    async def _ensure_category_access(self, user_id: UUID, category_id: UUID | None) -> None:
        if category_id is None:
            return
        category = await self.category_repository.get_by_id(category_id, user_id)
        if category is None:
            raise CategoryNotFoundError("Category not found")
