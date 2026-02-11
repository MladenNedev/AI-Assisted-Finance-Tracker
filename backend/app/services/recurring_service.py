from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.exceptions import (
    AccountNotFoundError,
    CategoryNotFoundError,
    DomainExceptionError,
    RecurringNotFoundError,
)
from app.domain.recurring import (
    RecurringCadence,
    advance_run,
    align_next_run,
    normalize_end_at,
    normalize_interval,
    normalize_start_at,
)
from app.domain.transaction import (
    normalize_merchant,
    normalize_note,
    normalize_tags,
    validate_transaction_amount,
    validate_transaction_direction,
)
from app.persistence.models import RecurringTransaction
from app.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    RecurringTransactionRepository,
    TransactionRepository,
)


class RecurringTransactionService:
    def __init__(
        self,
        session: AsyncSession,
        recurring_repository: RecurringTransactionRepository,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self.session = session
        self.recurring_repository = recurring_repository
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.transaction_repository = transaction_repository

    async def create_recurring_transaction(
        self,
        user_id: UUID,
        account_id: UUID,
        amount: Decimal,
        direction: str,
        cadence: RecurringCadence,
        interval: int,
        start_at: datetime,
        end_at: datetime | None,
        category_id: UUID | None,
        merchant: str | None,
        note: str | None,
        tags: list[str] | None,
    ) -> RecurringTransaction:
        await self._ensure_account_access(user_id, account_id)
        await self._ensure_category_access(user_id, category_id)

        normalized_start = normalize_start_at(start_at)
        normalized_end = normalize_end_at(end_at)
        normalized_interval = normalize_interval(interval)

        if normalized_end and normalized_end <= normalized_start:
            raise DomainExceptionError("End date must be after start date")

        now = datetime.now(UTC)
        next_run_at = align_next_run(normalized_start, cadence, normalized_interval, now)

        recurring = RecurringTransaction(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            amount=validate_transaction_amount(amount),
            direction=validate_transaction_direction(direction).value,
            cadence=cadence.value,
            interval=normalized_interval,
            start_at=normalized_start,
            next_run_at=next_run_at,
            end_at=normalized_end,
            merchant=normalize_merchant(merchant),
            note=normalize_note(note),
            tags=normalize_tags(tags),
            is_active=True,
        )
        await self.recurring_repository.create(recurring)
        await self.session.commit()
        await self.session.refresh(recurring)
        return recurring

    async def list_recurring_transactions(
        self, user_id: UUID, *, active_only: bool = False
    ) -> list[RecurringTransaction]:
        return await self.recurring_repository.list_by_user(user_id, active_only=active_only)

    async def get_recurring_transaction(
        self, recurring_id: UUID, user_id: UUID
    ) -> RecurringTransaction:
        recurring = await self.recurring_repository.get_by_id(recurring_id, user_id)
        if recurring is None:
            raise RecurringNotFoundError("Recurring transaction not found")
        return recurring

    async def update_recurring_transaction(
        self,
        recurring_id: UUID,
        user_id: UUID,
        **updates: object,
    ) -> RecurringTransaction:
        recurring = await self.recurring_repository.get_by_id(recurring_id, user_id)
        if recurring is None:
            raise RecurringNotFoundError("Recurring transaction not found")

        cadence = updates.get("cadence", _UNSET)
        interval = updates.get("interval", _UNSET)
        start_at = updates.get("start_at", _UNSET)
        end_at = updates.get("end_at", _UNSET)
        amount = updates.get("amount", _UNSET)
        direction = updates.get("direction", _UNSET)
        merchant = updates.get("merchant", _UNSET)
        note = updates.get("note", _UNSET)
        tags = updates.get("tags", _UNSET)
        category_id = updates.get("category_id", _UNSET)
        is_active = updates.get("is_active", _UNSET)

        if category_id is not _UNSET:
            await self._ensure_category_access(
                user_id, category_id if isinstance(category_id, UUID) else None
            )
            recurring.category_id = category_id if isinstance(category_id, UUID) else None

        if amount is not _UNSET:
            recurring.amount = validate_transaction_amount(
                amount if isinstance(amount, Decimal) else Decimal(str(amount))
            )
        if direction is not _UNSET:
            recurring.direction = validate_transaction_direction(str(direction)).value
        if merchant is not _UNSET:
            recurring.merchant = normalize_merchant(merchant if isinstance(merchant, str) else None)
        if note is not _UNSET:
            recurring.note = normalize_note(note if isinstance(note, str) else None)
        if tags is not _UNSET:
            recurring.tags = normalize_tags(tags if isinstance(tags, list) else None)
        if is_active is not _UNSET and isinstance(is_active, bool):
            recurring.is_active = is_active

        cadence_value = RecurringCadence(recurring.cadence)
        interval_value = recurring.interval
        start_value = recurring.start_at

        if cadence is not _UNSET:
            cadence_value = RecurringCadence(str(cadence))
            recurring.cadence = cadence_value.value
        if interval is not _UNSET:
            interval_value = normalize_interval(int(interval))
            recurring.interval = interval_value
        if start_at is not _UNSET:
            start_value = normalize_start_at(
                start_at
                if isinstance(start_at, datetime)
                else datetime.fromisoformat(str(start_at))
            )
            recurring.start_at = start_value
        if end_at is not _UNSET:
            end_value = normalize_end_at(
                end_at if isinstance(end_at, datetime) else datetime.fromisoformat(str(end_at))
            )
            if end_value and end_value <= start_value:
                raise DomainExceptionError("End date must be after start date")
            recurring.end_at = end_value

        if cadence is not _UNSET or interval is not _UNSET or start_at is not _UNSET:
            recurring.next_run_at = align_next_run(
                start_value, cadence_value, interval_value, datetime.now(UTC)
            )

        await self.session.commit()
        await self.session.refresh(recurring)
        return recurring

    async def delete_recurring_transaction(self, recurring_id: UUID, user_id: UUID) -> None:
        recurring = await self.recurring_repository.get_by_id(recurring_id, user_id)
        if recurring is None:
            raise RecurringNotFoundError("Recurring transaction not found")
        await self.recurring_repository.delete(recurring)
        await self.session.commit()

    async def run_due(self, user_id: UUID) -> tuple[int, int]:
        now = datetime.now(UTC)
        due = await self.recurring_repository.list_due(user_id, now)
        created = 0
        skipped = 0

        for recurring in due:
            await self._ensure_account_access(user_id, recurring.account_id)
            await self._ensure_category_access(user_id, recurring.category_id)

            cadence = RecurringCadence(recurring.cadence)
            while recurring.is_active and recurring.next_run_at <= now:
                if recurring.end_at and recurring.next_run_at > recurring.end_at:
                    recurring.is_active = False
                    break

                await self.transaction_repository.create(
                    account_id=recurring.account_id,
                    category_id=recurring.category_id,
                    amount=recurring.amount,
                    direction=recurring.direction,
                    occurred_at=recurring.next_run_at,
                    merchant=recurring.merchant,
                    note=recurring.note,
                    tags=recurring.tags,
                )
                created += 1
                recurring.next_run_at = advance_run(
                    recurring.next_run_at, cadence, recurring.interval
                )

                if created > 500:
                    skipped += 1
                    break

        if created:
            await self.session.commit()
            await cache.bump_user_report_version(user_id)
        return created, skipped

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


_UNSET = object()
