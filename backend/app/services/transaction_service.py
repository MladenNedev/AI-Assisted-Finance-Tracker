import csv
import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import get_settings
from app.core.exceptions import (
    AccountNotFoundError,
    AttachmentNotFoundError,
    CategoryNotFoundError,
    DomainExceptionError,
    TransactionNotFoundError,
)
from app.domain.transaction import (
    normalize_merchant,
    normalize_note,
    normalize_occurred_at,
    normalize_split_amount,
    normalize_tags,
    validate_transaction_amount,
    validate_transaction_direction,
)
from app.persistence.models import Transaction, TransactionAttachment, TransactionSplit
from app.persistence.repositories import (
    AccountRepository,
    CategoryRepository,
    TransactionAttachmentRepository,
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
        attachment_repository: TransactionAttachmentRepository,
    ) -> None:
        self.session = session
        self.account_repository = account_repository
        self.transaction_repository = transaction_repository
        self.category_repository = category_repository
        self.attachment_repository = attachment_repository

    async def create_transaction(
        self,
        user_id: UUID,
        account_id: UUID,
        amount: Decimal,
        direction: str,
        occurred_at: datetime,
        merchant: str | None,
        note: str | None,
        tags: list[str] | None = None,
        splits: list[object] | None = None,
        category_id: UUID | None = None,
    ) -> Transaction:
        await self._ensure_account_access(user_id, account_id)
        normalized_amount = validate_transaction_amount(amount)
        normalized_direction = validate_transaction_direction(direction).value
        normalized_occurred_at = normalize_occurred_at(occurred_at)

        normalized_splits: list[TransactionSplit] = []
        if splits:
            if category_id is not None:
                raise DomainExceptionError(
                    "Category must be omitted when transaction splits are provided"
                )
            normalized_splits, split_total = await self._normalize_splits(user_id, splits)
            if split_total != normalized_amount:
                raise DomainExceptionError(
                    "Split amounts must equal the transaction amount",
                )
        else:
            await self._ensure_category_access(user_id, category_id)

        transaction = await self.transaction_repository.create(
            account_id=account_id,
            category_id=None if splits else category_id,
            amount=normalized_amount,
            direction=normalized_direction,
            occurred_at=normalized_occurred_at,
            merchant=normalize_merchant(merchant),
            note=normalize_note(note),
            tags=normalize_tags(tags),
        )
        if normalized_splits:
            transaction.splits = normalized_splits
            await self.session.flush()
        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        reloaded = await self.transaction_repository.get_by_id(transaction.id, user_id)
        if reloaded is None:
            raise TransactionNotFoundError("Transaction not found")
        return reloaded

    async def create_transfer(
        self,
        user_id: UUID,
        from_account_id: UUID,
        to_account_id: UUID,
        amount: Decimal,
        occurred_at: datetime,
        note: str | None,
    ) -> tuple[UUID, Transaction, Transaction]:
        if from_account_id == to_account_id:
            raise DomainExceptionError("Transfer accounts must be different")

        await self._ensure_account_access(user_id, from_account_id)
        await self._ensure_account_access(user_id, to_account_id)

        transfer_id = uuid4()
        normalized_amount = validate_transaction_amount(amount)
        normalized_occurred_at = normalize_occurred_at(occurred_at)
        normalized_note = normalize_note(note)

        transfer_ctx = (
            self.session.begin_nested() if self.session.in_transaction() else self.session.begin()
        )
        async with transfer_ctx:
            outgoing = await self.transaction_repository.create(
                account_id=from_account_id,
                category_id=None,
                amount=normalized_amount,
                direction=validate_transaction_direction("OUT").value,
                occurred_at=normalized_occurred_at,
                merchant="Transfer",
                note=normalized_note,
                transfer_id=transfer_id,
            )
            incoming = await self.transaction_repository.create(
                account_id=to_account_id,
                category_id=None,
                amount=normalized_amount,
                direction=validate_transaction_direction("IN").value,
                occurred_at=normalized_occurred_at,
                merchant="Transfer",
                note=normalized_note,
                transfer_id=transfer_id,
            )
        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        reloaded_outgoing = await self.transaction_repository.get_by_id(outgoing.id, user_id)
        reloaded_incoming = await self.transaction_repository.get_by_id(incoming.id, user_id)
        if reloaded_outgoing is None or reloaded_incoming is None:
            raise TransactionNotFoundError("Transfer transactions not found")
        return transfer_id, reloaded_outgoing, reloaded_incoming

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
        tag: str | None = None,
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
        normalized_tag = tag.strip().lower() if tag else None

        normalized_search = search.strip() if search else None
        if normalized_search == "":
            normalized_search = None

        transactions = await self.transaction_repository.list_by_user(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            tag=normalized_tag,
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
            tag=normalized_tag,
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
        tag: str | None = None,
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
        normalized_tag = tag.strip().lower() if tag else None

        normalized_search = search.strip() if search else None
        if normalized_search == "":
            normalized_search = None

        transactions = await self.transaction_repository.list_by_user(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            tag=normalized_tag,
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
                "tags",
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
                    ",".join(transaction.tags or []),
                ]
            )

        return output.getvalue()

    async def import_transactions_csv(
        self,
        user_id: UUID,
        csv_payload: str,
    ) -> tuple[int, int, list[dict[str, object]]]:
        reader = csv.DictReader(io.StringIO(csv_payload))
        accounts = await self.account_repository.list_by_user(
            user_id, include_inactive=True, limit=5000, offset=0
        )
        categories = await self.category_repository.list_by_user(user_id, limit=5000, offset=0)
        account_by_id = {str(account.id): account for account in accounts}
        account_by_name = {account.name.strip().lower(): account for account in accounts}
        category_by_id = {str(category.id): category for category in categories}
        category_by_name = {category.name.strip().lower(): category for category in categories}

        imported = 0
        skipped = 0
        errors: list[dict[str, object]] = []

        transaction_ctx = (
            self.session.begin_nested() if self.session.in_transaction() else self.session.begin()
        )
        async with transaction_ctx:
            for index, row in enumerate(reader, start=2):
                try:
                    account_id = _resolve_uuid(
                        row.get("account_id"),
                        account_by_id,
                        account_by_name,
                        field="account",
                        required=True,
                    )

                    category_id = _resolve_uuid(
                        row.get("category_id"),
                        category_by_id,
                        category_by_name,
                        field="category",
                        required=False,
                    )

                    occurred_raw = row.get("occurred_at")
                    if not occurred_raw:
                        raise ValueError("Occurred_at is required")
                    occurred_at = normalize_occurred_at(datetime.fromisoformat(occurred_raw))

                    amount_raw = row.get("amount")
                    if not amount_raw:
                        raise ValueError("Amount is required")
                    amount = validate_transaction_amount(Decimal(amount_raw))

                    direction = validate_transaction_direction(row.get("direction", "")).value

                    merchant = normalize_merchant(row.get("merchant"))
                    note = normalize_note(row.get("note"))
                    tags = normalize_tags(parse_tags(row.get("tags")))

                    await self._ensure_account_access(user_id, account_id)
                    await self._ensure_category_access(user_id, category_id)

                    await self.transaction_repository.create(
                        account_id=account_id,
                        category_id=category_id,
                        amount=amount,
                        direction=direction,
                        occurred_at=occurred_at,
                        merchant=merchant,
                        note=note,
                        tags=tags,
                    )
                    imported += 1
                except Exception as exc:  # noqa: BLE001
                    skipped += 1
                    errors.append({"row": index, "message": str(exc)})

        if imported:
            if self.session.in_transaction():
                await self.session.commit()
            await cache.bump_user_report_version(user_id)
        return imported, skipped, errors

    async def bulk_update_category(
        self,
        user_id: UUID,
        transaction_ids: list[UUID],
        category_id: UUID | None,
    ) -> int:
        await self._ensure_category_access(user_id, category_id)
        updated = await self.transaction_repository.bulk_update_category(
            user_id=user_id,
            transaction_ids=transaction_ids,
            category_id=category_id,
        )
        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        return updated

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
        tags = updates.get("tags", _UNSET)
        splits = updates.get("splits", _UNSET)

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
            if splits is _UNSET:
                await self._ensure_category_access(user_id, typed_category_id)
                resolved_updates["category_id"] = typed_category_id
        if tags is not _UNSET:
            resolved_updates["tags"] = normalize_tags(tags if isinstance(tags, list) else None)

        if splits is _UNSET and existing.splits:
            if category_id is not _UNSET and category_id is not None:
                raise DomainExceptionError("Clear splits before assigning a transaction category")
            if "amount" in updates:
                raise DomainExceptionError("Update splits when changing the transaction amount")

        if splits is not _UNSET:
            if splits:
                normalized_splits, split_total = await self._normalize_splits(user_id, splits)
                if category_id is not _UNSET and category_id is not None:
                    raise DomainExceptionError(
                        "Category must be omitted when transaction splits are provided"
                    )
                if "amount" in updates:
                    if resolved_updates["amount"] != split_total:
                        raise DomainExceptionError(
                            "Split amounts must equal the transaction amount"
                        )
                else:
                    resolved_updates["amount"] = split_total
                resolved_updates["category_id"] = None
                existing.splits = normalized_splits
            else:
                existing.splits = []

        updated = await self.transaction_repository.update(
            transaction_id, user_id, **resolved_updates
        )
        if updated is None:
            raise TransactionNotFoundError("Transaction not found")

        await self.session.commit()
        await cache.bump_user_report_version(user_id)
        reloaded = await self.transaction_repository.get_by_id(updated.id, user_id)
        if reloaded is None:
            raise TransactionNotFoundError("Transaction not found")
        return reloaded

    async def delete_transaction(self, transaction_id: UUID, user_id: UUID) -> None:
        was_deleted = await self.transaction_repository.delete(transaction_id, user_id)
        if not was_deleted:
            raise TransactionNotFoundError("Transaction not found")
        await self.session.commit()
        await cache.bump_user_report_version(user_id)

    async def list_attachments(
        self, user_id: UUID, transaction_id: UUID
    ) -> list[TransactionAttachment]:
        await self._ensure_transaction_access(user_id, transaction_id)
        return await self.attachment_repository.list_by_transaction(transaction_id, user_id)

    async def create_attachment(
        self,
        user_id: UUID,
        transaction_id: UUID,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> TransactionAttachment:
        await self._ensure_transaction_access(user_id, transaction_id)
        settings = get_settings()

        if content_type not in settings.attachment_allowed_type_list:
            raise DomainExceptionError("Unsupported attachment type")
        if len(content) > settings.attachment_max_bytes:
            raise DomainExceptionError("Attachment exceeds size limit")

        safe_name = Path(filename).name or "attachment"
        attachment_id = uuid4()
        storage_key = f"{user_id}/{transaction_id}/{attachment_id}_{safe_name}"

        base_dir = Path(settings.attachments_dir)
        file_path = base_dir / storage_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

        attachment = TransactionAttachment(
            id=attachment_id,
            transaction_id=transaction_id,
            user_id=user_id,
            filename=safe_name,
            content_type=content_type,
            storage_key=storage_key,
            size_bytes=len(content),
        )
        await self.attachment_repository.create(attachment)
        await self.session.commit()
        return attachment

    async def get_attachment(
        self, user_id: UUID, transaction_id: UUID, attachment_id: UUID
    ) -> TransactionAttachment:
        attachment = await self.attachment_repository.get_by_id(
            attachment_id, transaction_id, user_id
        )
        if attachment is None:
            raise AttachmentNotFoundError("Attachment not found")
        return attachment

    async def delete_attachment(
        self, user_id: UUID, transaction_id: UUID, attachment_id: UUID
    ) -> None:
        attachment = await self.attachment_repository.get_by_id(
            attachment_id, transaction_id, user_id
        )
        if attachment is None:
            raise AttachmentNotFoundError("Attachment not found")
        settings = get_settings()
        file_path = Path(settings.attachments_dir) / attachment.storage_key
        if file_path.exists():
            file_path.unlink()
        await self.attachment_repository.delete(attachment)
        await self.session.commit()

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

    async def _ensure_transaction_access(self, user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = await self.transaction_repository.get_by_id(transaction_id, user_id)
        if transaction is None:
            raise TransactionNotFoundError("Transaction not found")
        return transaction

    async def _normalize_splits(
        self, user_id: UUID, raw_splits: list[object]
    ) -> tuple[list[TransactionSplit], Decimal]:
        if not raw_splits:
            return [], Decimal("0")
        if len(raw_splits) > 50:
            raise DomainExceptionError("No more than 50 splits are allowed")

        normalized_splits: list[TransactionSplit] = []
        total = Decimal("0")

        for raw_split in raw_splits:
            if isinstance(raw_split, dict):
                category_id = raw_split.get("category_id")
                amount_raw = raw_split.get("amount")
                note_raw = raw_split.get("note")
            else:
                category_id = getattr(raw_split, "category_id", None)
                amount_raw = getattr(raw_split, "amount", None)
                note_raw = getattr(raw_split, "note", None)

            if amount_raw is None:
                raise DomainExceptionError("Split amount is required")

            await self._ensure_category_access(user_id, category_id)

            amount = normalize_split_amount(
                amount_raw if isinstance(amount_raw, Decimal) else Decimal(str(amount_raw))
            )
            total += amount
            normalized_splits.append(
                TransactionSplit(
                    category_id=category_id,
                    amount=amount,
                    note=normalize_note(note_raw if isinstance(note_raw, str) else None),
                )
            )

        total = validate_transaction_amount(total)
        return normalized_splits, total


def _resolve_uuid(
    raw_value: object,
    by_id: dict[str, object],
    by_name: dict[str, object],
    *,
    field: str,
    required: bool,
) -> UUID | None:
    if raw_value is None:
        if required:
            raise ValueError(f"{field.capitalize()} is required")
        return None
    candidate = str(raw_value).strip()
    if not candidate:
        if required:
            raise ValueError(f"{field.capitalize()} is required")
        return None
    if candidate in by_id:
        return by_id[candidate].id
    lowered = candidate.lower()
    if lowered in by_name:
        return by_name[lowered].id
    raise ValueError(f"Unknown {field}: {candidate}")


def parse_tags(raw_value: object) -> list[str] | None:
    if raw_value is None:
        return None
    candidate = str(raw_value).strip()
    if not candidate:
        return None
    parts = [part.strip() for part in candidate.split(",")]
    return [part for part in parts if part]
