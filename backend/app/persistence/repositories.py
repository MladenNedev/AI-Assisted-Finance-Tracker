from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Select, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.money import TransactionDirection
from app.persistence.models import Account, AuthSession, Category, Transaction, User


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
    ) -> Transaction:
        transaction = Transaction(
            account_id=account_id,
            category_id=category_id,
            amount=amount,
            direction=direction,
            occurred_at=occurred_at,
            merchant=merchant,
            note=note,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def get_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction | None:
        stmt = (
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Transaction.id == transaction_id, Account.user_id == user_id)
        )
        return await self.session.scalar(stmt)

    def _build_list_stmt(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> Select[tuple[Transaction]]:
        stmt = (
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(Account.user_id == user_id)
        )
        if account_id is not None:
            stmt = stmt.where(Transaction.account_id == account_id)
        if category_id is not None:
            stmt = stmt.where(Transaction.category_id == category_id)
        if occurred_from is not None:
            stmt = stmt.where(Transaction.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(Transaction.occurred_at <= occurred_to)
        return stmt

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        stmt = self._build_list_stmt(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        stmt = stmt.order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        rows = await self.session.scalars(stmt)
        return list(rows.all())

    async def count_by_user(
        self,
        user_id: UUID,
        *,
        account_id: UUID | None = None,
        category_id: UUID | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> int:
        base_stmt = self._build_list_stmt(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
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
        amount_expr = func.coalesce(func.sum(Transaction.amount), Decimal("0"))
        stmt = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                Category.color,
                Category.icon,
                amount_expr.label("amount"),
            )
            .select_from(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(
                Account.user_id == user_id,
                Transaction.direction == direction.value,
                Transaction.occurred_at >= from_date,
                Transaction.occurred_at < to_date,
            )
            .group_by(Category.id, Category.name, Category.color, Category.icon)
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
