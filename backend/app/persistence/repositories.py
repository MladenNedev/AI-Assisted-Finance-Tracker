from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, case, exists, func, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.money import TransactionDirection
from app.persistence.models import (
    Account,
    AuthSession,
    Budget,
    Category,
    RecurringTransaction,
    Transaction,
    TransactionAttachment,
    TransactionSplit,
    User,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return await self.session.scalar(stmt)

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email.lower(), hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()
        return user


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: UUID, token_hash: str, expires_at: datetime) -> AuthSession:
        auth_session = AuthSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(auth_session)
        await self.session.flush()
        return auth_session

    async def get_by_token_hash(self, token_hash: str) -> AuthSession | None:
        stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
        return await self.session.scalar(stmt)

    async def get_active_by_token_hash(self, token_hash: str, now: datetime) -> AuthSession | None:
        stmt = select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        return await self.session.scalar(stmt)

    def revoke(self, auth_session: AuthSession, revoked_at: datetime) -> None:
        auth_session.revoked_at = revoked_at


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: UUID,
        name: str,
        account_type: str,
        opening_balance: Decimal,
        currency: str,
    ) -> Account:
        account = Account(
            user_id=user_id,
            name=name,
            account_type=account_type,
            opening_balance=opening_balance,
            currency=currency,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_by_id(
        self,
        account_id: UUID,
        user_id: UUID,
        *,
        include_inactive: bool = False,
    ) -> Account | None:
        stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
        if not include_inactive:
            stmt = stmt.where(Account.is_active.is_(True))
        return await self.session.scalar(stmt)

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Account]:
        stmt = select(Account).where(Account.user_id == user_id)
        if not include_inactive:
            stmt = stmt.where(Account.is_active.is_(True))
        stmt = stmt.order_by(Account.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count_by_user(self, user_id: UUID, *, include_inactive: bool = False) -> int:
        stmt = select(func.count(Account.id)).where(Account.user_id == user_id)
        if not include_inactive:
            stmt = stmt.where(Account.is_active.is_(True))
        return int(await self.session.scalar(stmt) or 0)

    async def update(self, account_id: UUID, user_id: UUID, **updates: object) -> Account | None:
        account = await self.get_by_id(account_id, user_id, include_inactive=True)
        if account is None:
            return None

        for field_name, value in updates.items():
            setattr(account, field_name, value)

        await self.session.flush()
        return account

    async def deactivate(self, account_id: UUID, user_id: UUID) -> Account | None:
        account = await self.get_by_id(account_id, user_id, include_inactive=True)
        if account is None:
            return None
        account.is_active = False
        await self.session.flush()
        return account

    async def get_balances(self, account_ids: list[UUID]) -> dict[UUID, Decimal]:
        if not account_ids:
            return {}

        signed_sum = func.coalesce(
            func.sum(
                case(
                    (Transaction.direction == TransactionDirection.IN.value, Transaction.amount),
                    else_=-Transaction.amount,
                )
            ),
            Decimal("0"),
        )
        stmt = (
            select(Transaction.account_id, signed_sum)
            .where(Transaction.account_id.in_(account_ids))
            .group_by(Transaction.account_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {account_id: Decimal(total) for account_id, total in rows}


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        account_id: UUID,
        category_id: UUID | None,
        amount: Decimal,
        direction: str,
        occurred_at: datetime,
        merchant: str | None,
        note: str | None,
        tags: list[str] | None = None,
        transfer_id: UUID | None = None,
    ) -> Transaction:
        transaction = Transaction(
            account_id=account_id,
            category_id=category_id,
            transfer_id=transfer_id,
            amount=amount,
            direction=direction,
            occurred_at=occurred_at,
            merchant=merchant,
            note=note,
            tags=tags,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction | None:
        stmt = (
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Transaction.id == transaction_id, Account.user_id == user_id)
            .options(
                selectinload(Transaction.splits),
                selectinload(Transaction.attachments),
            )
        )
        return await self.session.scalar(stmt)

    def _build_list_stmt(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        tag: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        search: str | None = None,
    ) -> Select[tuple[Transaction]]:
        stmt = (
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == user_id)
        )
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if category_id is not None:
            split_subquery = select(TransactionSplit.transaction_id).where(
                TransactionSplit.category_id == category_id
            )
            stmt = stmt.where(
                or_(
                    Transaction.category_id == category_id,
                    Transaction.id.in_(split_subquery),
                )
            )
        if tag:
            stmt = stmt.where(Transaction.tags.any(tag))
        if occurred_from is not None:
            stmt = stmt.where(Transaction.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(Transaction.occurred_at <= occurred_to)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Transaction.merchant.ilike(pattern),
                    Transaction.note.ilike(pattern),
                )
            )
        return stmt

    async def list_by_user(
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
    ) -> list[Transaction]:
        stmt = self._build_list_stmt(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            tag=tag,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            search=search,
        )
        stmt = stmt.order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc())
        stmt = stmt.options(
            selectinload(Transaction.splits),
            selectinload(Transaction.attachments),
        )
        stmt = stmt.limit(limit).offset(offset)
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def count_by_user(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        tag: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        search: str | None = None,
    ) -> int:
        base_stmt = self._build_list_stmt(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            tag=tag,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            search=search,
        )
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        return int(await self.session.scalar(count_stmt) or 0)

    async def update(
        self, transaction_id: UUID, user_id: UUID, **updates: object
    ) -> Transaction | None:
        transaction = await self.get_by_id(transaction_id, user_id)
        if transaction is None:
            return None

        for field_name, value in updates.items():
            setattr(transaction, field_name, value)

        await self.session.flush()
        return transaction

    async def delete(self, transaction_id: UUID, user_id: UUID) -> bool:
        transaction = await self.get_by_id(transaction_id, user_id)
        if transaction is None:
            return False

        await self.session.delete(transaction)
        await self.session.flush()
        return True

    async def bulk_update_category(
        self,
        user_id: UUID,
        transaction_ids: list[UUID],
        category_id: UUID | None,
    ) -> int:
        if not transaction_ids:
            return 0
        allowed_ids = (
            select(Transaction.id)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == user_id, Transaction.id.in_(transaction_ids))
            .subquery()
        )
        stmt = (
            Transaction.__table__.update()
            .where(Transaction.id.in_(select(allowed_ids.c.id)))
            .values(category_id=category_id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)


class RecurringTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, recurring: RecurringTransaction) -> RecurringTransaction:
        self.session.add(recurring)
        await self.session.flush()
        return recurring

    async def get_by_id(
        self, recurring_id: UUID, user_id: UUID
    ) -> RecurringTransaction | None:
        stmt = select(RecurringTransaction).where(
            RecurringTransaction.id == recurring_id,
            RecurringTransaction.user_id == user_id,
        )
        return await self.session.scalar(stmt)

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        active_only: bool = False,
    ) -> list[RecurringTransaction]:
        stmt = select(RecurringTransaction).where(RecurringTransaction.user_id == user_id)
        if active_only:
            stmt = stmt.where(RecurringTransaction.is_active.is_(True))
        stmt = stmt.order_by(RecurringTransaction.next_run_at.asc())
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def list_due(
        self,
        user_id: UUID,
        now: datetime,
        *,
        limit: int = 100,
    ) -> list[RecurringTransaction]:
        stmt = (
            select(RecurringTransaction)
            .where(
                RecurringTransaction.user_id == user_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_run_at <= now,
            )
            .order_by(RecurringTransaction.next_run_at.asc())
            .limit(limit)
        )
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def delete(self, recurring: RecurringTransaction) -> None:
        await self.session.delete(recurring)


class TransactionAttachmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, attachment: TransactionAttachment) -> TransactionAttachment:
        self.session.add(attachment)
        await self.session.flush()
        return attachment

    async def list_by_transaction(
        self, transaction_id: UUID, user_id: UUID
    ) -> list[TransactionAttachment]:
        stmt = select(TransactionAttachment).where(
            TransactionAttachment.transaction_id == transaction_id,
            TransactionAttachment.user_id == user_id,
        )
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def get_by_id(
        self,
        attachment_id: UUID,
        transaction_id: UUID,
        user_id: UUID,
    ) -> TransactionAttachment | None:
        stmt = select(TransactionAttachment).where(
            TransactionAttachment.id == attachment_id,
            TransactionAttachment.transaction_id == transaction_id,
            TransactionAttachment.user_id == user_id,
        )
        return await self.session.scalar(stmt)

    async def delete(self, attachment: TransactionAttachment) -> None:
        await self.session.delete(attachment)


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: UUID,
        name: str,
        is_income: bool,
        color: str | None,
        icon: str | None,
    ) -> Category:
        category = Category(
            user_id=user_id,
            name=name,
            is_income=is_income,
            color=color,
            icon=icon,
        )
        self.session.add(category)
        await self.session.flush()
        return category

    async def get_by_id(self, category_id: UUID, user_id: UUID) -> Category | None:
        stmt = select(Category).where(Category.id == category_id, Category.user_id == user_id)
        return await self.session.scalar(stmt)

    async def get_by_name(self, user_id: UUID, name: str) -> Category | None:
        stmt = select(Category).where(Category.user_id == user_id, Category.name == name)
        return await self.session.scalar(stmt)

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Category]:
        stmt = (
            select(Category)
            .where(Category.user_id == user_id)
            .order_by(Category.name.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count(Category.id)).where(Category.user_id == user_id)
        return int(await self.session.scalar(stmt) or 0)

    async def update(self, category_id: UUID, user_id: UUID, **updates: object) -> Category | None:
        category = await self.get_by_id(category_id, user_id)
        if category is None:
            return None
        for field_name, value in updates.items():
            setattr(category, field_name, value)
        await self.session.flush()
        return category

    async def delete(self, category_id: UUID, user_id: UUID) -> bool:
        category = await self.get_by_id(category_id, user_id)
        if category is None:
            return False
        await self.session.delete(category)
        await self.session.flush()
        return True


def _category_amounts_subquery(
    *,
    user_id: UUID,
    direction: TransactionDirection,
    occurred_from: datetime,
    occurred_to: datetime,
    category_ids: list[UUID] | None = None,
) -> Select[tuple[UUID | None, Decimal]]:
    split_stmt = (
        select(
            TransactionSplit.category_id.label("category_id"),
            func.coalesce(func.sum(TransactionSplit.amount), Decimal("0")).label("amount"),
        )
        .select_from(TransactionSplit)
        .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.user_id == user_id,
            Transaction.direction == direction.value,
            Transaction.occurred_at >= occurred_from,
            Transaction.occurred_at < occurred_to,
        )
        .group_by(TransactionSplit.category_id)
    )

    no_split_stmt = (
        select(
            Transaction.category_id.label("category_id"),
            func.coalesce(func.sum(Transaction.amount), Decimal("0")).label("amount"),
        )
        .select_from(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.user_id == user_id,
            Transaction.direction == direction.value,
            Transaction.occurred_at >= occurred_from,
            Transaction.occurred_at < occurred_to,
            Transaction.category_id.is_not(None),
            ~exists().where(TransactionSplit.transaction_id == Transaction.id),
        )
        .group_by(Transaction.category_id)
    )

    combined = union_all(split_stmt, no_split_stmt).subquery()
    stmt = select(
        combined.c.category_id,
        func.coalesce(func.sum(combined.c.amount), Decimal("0")).label("amount"),
    ).group_by(combined.c.category_id)
    if category_ids:
        stmt = stmt.where(combined.c.category_id.in_(category_ids))
    return stmt


class BudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: UUID,
        category_id: UUID,
        month_start: date,
        limit_amount: Decimal,
        rollover_enabled: bool,
    ) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            month_start=month_start,
            limit_amount=limit_amount,
            rollover_enabled=rollover_enabled,
        )
        self.session.add(budget)
        await self.session.flush()
        return budget

    async def get_by_id(self, budget_id: UUID, user_id: UUID) -> Budget | None:
        stmt = select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        return await self.session.scalar(stmt)

    async def get_by_category_month(
        self,
        user_id: UUID,
        category_id: UUID,
        month_start: date,
    ) -> Budget | None:
        stmt = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month_start == month_start,
        )
        return await self.session.scalar(stmt)

    async def list_by_month(
        self,
        user_id: UUID,
        month_start: date,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Budget]:
        stmt = (
            select(Budget)
            .join(Category, Category.id == Budget.category_id)
            .where(Budget.user_id == user_id, Budget.month_start == month_start)
            .order_by(Category.name.asc(), Budget.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def list_all_by_month(self, user_id: UUID, month_start: date) -> list[Budget]:
        stmt = (
            select(Budget)
            .join(Category, Category.id == Budget.category_id)
            .where(Budget.user_id == user_id, Budget.month_start == month_start)
            .order_by(Category.name.asc(), Budget.created_at.asc())
        )
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def count_by_month(self, user_id: UUID, month_start: date) -> int:
        stmt = select(func.count(Budget.id)).where(
            Budget.user_id == user_id, Budget.month_start == month_start
        )
        return int(await self.session.scalar(stmt) or 0)

    async def sum_limits_for_month(self, user_id: UUID, month_start: date) -> Decimal:
        stmt = select(func.coalesce(func.sum(Budget.limit_amount), Decimal("0"))).where(
            Budget.user_id == user_id, Budget.month_start == month_start
        )
        return Decimal(await self.session.scalar(stmt) or 0)

    async def sum_spent_for_month(
        self,
        user_id: UUID,
        month_start: date,
        occurred_from: datetime,
        occurred_to: datetime,
    ) -> Decimal:
        spent_subquery = _category_amounts_subquery(
            user_id=user_id,
            direction=TransactionDirection.OUT,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        ).subquery()
        stmt = (
            select(func.coalesce(func.sum(spent_subquery.c.amount), Decimal("0")))
            .select_from(spent_subquery)
            .join(
                Budget,
                (Budget.category_id == spent_subquery.c.category_id)
                & (Budget.user_id == user_id)
                & (Budget.month_start == month_start),
            )
        )
        return Decimal(await self.session.scalar(stmt) or 0)

    async def update(
        self,
        budget_id: UUID,
        user_id: UUID,
        *,
        limit_amount: Decimal | None = None,
        rollover_enabled: bool | None = None,
    ) -> Budget | None:
        budget = await self.get_by_id(budget_id, user_id)
        if budget is None:
            return None
        if limit_amount is not None:
            budget.limit_amount = limit_amount
        if rollover_enabled is not None:
            budget.rollover_enabled = rollover_enabled
        await self.session.flush()
        return budget

    async def delete(self, budget_id: UUID, user_id: UUID) -> bool:
        budget = await self.get_by_id(budget_id, user_id)
        if budget is None:
            return False
        await self.session.delete(budget)
        await self.session.flush()
        return True

    async def list_month_progress(
        self,
        user_id: UUID,
        month_start: date,
        occurred_from: datetime,
        occurred_to: datetime,
    ) -> list[dict[str, object]]:
        spent_subquery = _category_amounts_subquery(
            user_id=user_id,
            direction=TransactionDirection.OUT,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        ).subquery()

        stmt = (
            select(
                Budget.id.label("budget_id"),
                Budget.category_id.label("category_id"),
                Budget.month_start.label("month_start"),
                Budget.limit_amount.label("limit_amount"),
                Budget.rollover_enabled.label("rollover_enabled"),
                Category.name.label("category_name"),
                Category.color.label("category_color"),
                Category.icon.label("category_icon"),
                func.coalesce(spent_subquery.c.amount, Decimal("0")).label("spent_amount"),
            )
            .select_from(Budget)
            .join(Category, Category.id == Budget.category_id)
            .outerjoin(spent_subquery, spent_subquery.c.category_id == Budget.category_id)
            .where(Budget.user_id == user_id, Budget.month_start == month_start)
            .order_by(Category.name.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "budget_id": row.budget_id,
                "category_id": row.category_id,
                "month_start": row.month_start,
                "limit_amount": Decimal(row.limit_amount),
                "rollover_enabled": bool(row.rollover_enabled),
                "category_name": row.category_name,
                "category_color": row.category_color,
                "category_icon": row.category_icon,
                "spent_amount": Decimal(row.spent_amount or 0),
            }
            for row in rows
        ]


class ReportingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_cashflow_summary(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
    ) -> dict[str, Decimal]:
        stmt = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.direction == TransactionDirection.IN.value,
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("income"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.direction == TransactionDirection.OUT.value,
                                Transaction.amount,
                            ),
                            else_=Decimal("0"),
                        )
                    ),
                    Decimal("0"),
                ).label("expenses"),
            )
            .select_from(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.user_id == user_id,
                Transaction.occurred_at >= from_date,
                Transaction.occurred_at < to_date,
            )
        )
        row = (await self.session.execute(stmt)).one()
        income = Decimal(row.income or 0)
        expenses = Decimal(row.expenses or 0)
        return {"income": income, "expenses": expenses, "net": income - expenses}

    async def get_cashflow_by_period(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        *,
        granularity: str,
    ) -> list[dict[str, Decimal | datetime]]:
        if granularity == "week":
            period_expr = func.date_trunc("week", Transaction.occurred_at)
        elif granularity == "month":
            period_expr = func.date_trunc("month", Transaction.occurred_at)
        else:
            period_expr = func.date_trunc("day", Transaction.occurred_at)

        income_expr = func.coalesce(
            func.sum(
                case(
                    (Transaction.direction == TransactionDirection.IN.value, Transaction.amount),
                    else_=Decimal("0"),
                )
            ),
            Decimal("0"),
        )
        expense_expr = func.coalesce(
            func.sum(
                case(
                    (Transaction.direction == TransactionDirection.OUT.value, Transaction.amount),
                    else_=Decimal("0"),
                )
            ),
            Decimal("0"),
        )

        stmt = (
            select(
                period_expr.label("period"),
                income_expr.label("income"),
                expense_expr.label("expenses"),
            )
            .select_from(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.user_id == user_id,
                Transaction.occurred_at >= from_date,
                Transaction.occurred_at < to_date,
            )
            .group_by(period_expr)
            .order_by(period_expr.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        points: list[dict[str, Decimal | datetime]] = []
        for row in rows:
            income = Decimal(row.income or 0)
            expenses = Decimal(row.expenses or 0)
            points.append(
                {
                    "period": row.period,
                    "income": income,
                    "expenses": expenses,
                    "net": income - expenses,
                }
            )
        return points

    async def get_category_breakdown(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        *,
        direction: TransactionDirection,
        limit: int,
    ) -> list[dict[str, object]]:
        amounts_subquery = _category_amounts_subquery(
            user_id=user_id,
            direction=direction,
            occurred_from=from_date,
            occurred_to=to_date,
        ).subquery()
        amount_expr = func.coalesce(amounts_subquery.c.amount, Decimal("0"))
        stmt = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                Category.color,
                Category.icon,
                amount_expr.label("amount"),
            )
            .select_from(amounts_subquery)
            .outerjoin(Category, Category.id == amounts_subquery.c.category_id)
            .order_by(amount_expr.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "category_id": row.category_id,
                "category_name": row.category_name or "Uncategorized",
                "color": row.color,
                "icon": row.icon,
                "amount": Decimal(row.amount or 0),
            }
            for row in rows
        ]

    async def get_account_balances_summary(self, user_id: UUID) -> list[dict[str, object]]:
        movement_subquery = (
            select(
                Transaction.account_id.label("account_id"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Transaction.direction == TransactionDirection.IN.value,
                                Transaction.amount,
                            ),
                            else_=-Transaction.amount,
                        )
                    ),
                    Decimal("0"),
                ).label("movement"),
            )
            .select_from(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == user_id)
            .group_by(Transaction.account_id)
            .subquery()
        )

        stmt = (
            select(
                Account.id,
                Account.name,
                Account.account_type,
                Account.currency,
                Account.opening_balance,
                func.coalesce(movement_subquery.c.movement, Decimal("0")).label("movement"),
            )
            .select_from(Account)
            .outerjoin(movement_subquery, movement_subquery.c.account_id == Account.id)
            .where(Account.user_id == user_id, Account.is_active.is_(True))
            .order_by(Account.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "account_id": row.id,
                "account_name": row.name,
                "account_type": row.account_type,
                "currency": row.currency,
                "balance": Decimal(row.opening_balance) + Decimal(row.movement or 0),
            }
            for row in rows
        ]

    async def get_category_trend(
        self,
        user_id: UUID,
        from_date: datetime,
        to_date: datetime,
        *,
        granularity: str,
        direction: TransactionDirection,
        category_ids: list[UUID] | None = None,
    ) -> list[dict[str, object]]:
        if granularity == "week":
            period_expr = func.date_trunc("week", Transaction.occurred_at)
        elif granularity == "month":
            period_expr = func.date_trunc("month", Transaction.occurred_at)
        else:
            period_expr = func.date_trunc("day", Transaction.occurred_at)

        split_stmt = (
            select(
                period_expr.label("period"),
                TransactionSplit.category_id.label("category_id"),
                func.coalesce(func.sum(TransactionSplit.amount), Decimal("0")).label("amount"),
            )
            .select_from(TransactionSplit)
            .join(Transaction, Transaction.id == TransactionSplit.transaction_id)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.user_id == user_id,
                Transaction.direction == direction.value,
                Transaction.occurred_at >= from_date,
                Transaction.occurred_at < to_date,
            )
            .group_by(period_expr, TransactionSplit.category_id)
        )

        no_split_stmt = (
            select(
                period_expr.label("period"),
                Transaction.category_id.label("category_id"),
                func.coalesce(func.sum(Transaction.amount), Decimal("0")).label("amount"),
            )
            .select_from(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.user_id == user_id,
                Transaction.direction == direction.value,
                Transaction.occurred_at >= from_date,
                Transaction.occurred_at < to_date,
                Transaction.category_id.is_not(None),
                ~exists().where(TransactionSplit.transaction_id == Transaction.id),
            )
            .group_by(period_expr, Transaction.category_id)
        )

        combined = union_all(split_stmt, no_split_stmt).subquery()
        amount_expr = func.coalesce(func.sum(combined.c.amount), Decimal("0"))
        stmt = (
            select(
                combined.c.period.label("period"),
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                Category.color,
                Category.icon,
                amount_expr.label("amount"),
            )
            .select_from(combined)
            .outerjoin(Category, Category.id == combined.c.category_id)
        )
        if category_ids:
            stmt = stmt.where(combined.c.category_id.in_(category_ids))
        stmt = stmt.group_by(
            combined.c.period, Category.id, Category.name, Category.color, Category.icon
        )
        stmt = stmt.order_by(combined.c.period.asc(), amount_expr.desc())
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "period": row.period,
                "category_id": row.category_id,
                "category_name": row.category_name or "Uncategorized",
                "color": row.color,
                "icon": row.icon,
                "amount": Decimal(row.amount or 0),
            }
            for row in rows
        ]
