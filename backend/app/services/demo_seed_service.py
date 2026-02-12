from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.config import get_settings
from app.domain.budget import parse_budget_month, validate_budget_limit
from app.domain.category import (
    normalize_category_color,
    normalize_category_icon,
    validate_category_name,
)
from app.domain.money import AccountType, TransactionDirection, normalize_currency, quantize_money
from app.domain.recurring import RecurringCadence, align_next_run, normalize_start_at
from app.domain.transaction import (
    normalize_merchant,
    normalize_note,
    normalize_occurred_at,
    validate_transaction_amount,
    validate_transaction_direction,
)
from app.persistence.models import (
    Account,
    Budget,
    Category,
    RecurringTransaction,
    Transaction,
    TransactionAttachment,
    TransactionSplit,
    User,
)
from app.persistence.repositories import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    RecurringTransactionRepository,
    TransactionRepository,
)


class DemoSeedService:
    def __init__(
        self,
        session: AsyncSession,
        account_repository: AccountRepository,
        category_repository: CategoryRepository,
        budget_repository: BudgetRepository,
        transaction_repository: TransactionRepository,
        recurring_repository: RecurringTransactionRepository,
    ) -> None:
        self.session = session
        self.account_repository = account_repository
        self.category_repository = category_repository
        self.budget_repository = budget_repository
        self.transaction_repository = transaction_repository
        self.recurring_repository = recurring_repository
        self.settings = get_settings()

    async def seed_if_needed(self, user: User) -> bool:
        if not self.settings.demo_seed_enabled:
            return False

        if user.email.lower() != self.settings.demo_email.lower():
            return False

        existing_accounts = await self.account_repository.count_by_user(
            user.id, include_inactive=True
        )
        if existing_accounts > 0:
            return False

        await self._seed(user.id)
        return True

    async def reset_demo(self, user: User) -> bool:
        if not self.settings.demo_seed_enabled:
            return False

        if user.email.lower() != self.settings.demo_email.lower():
            return False

        await self._clear_user_data(user.id)
        await self._seed(user.id)
        return True

    async def _clear_user_data(self, user_id: UUID) -> None:
        account_rows = await self.session.execute(
            select(Account.id).where(Account.user_id == user_id)
        )
        account_ids = [row[0] for row in account_rows.all()]

        if account_ids:
            transaction_rows = await self.session.execute(
                select(Transaction.id).where(Transaction.account_id.in_(account_ids))
            )
            transaction_ids = [row[0] for row in transaction_rows.all()]

            if transaction_ids:
                await self.session.execute(
                    delete(TransactionAttachment).where(
                        TransactionAttachment.transaction_id.in_(transaction_ids)
                    )
                )
                await self.session.execute(
                    delete(TransactionSplit).where(
                        TransactionSplit.transaction_id.in_(transaction_ids)
                    )
                )
                await self.session.execute(
                    delete(Transaction).where(Transaction.id.in_(transaction_ids))
                )

        await self.session.execute(
            delete(RecurringTransaction).where(RecurringTransaction.user_id == user_id)
        )
        await self.session.execute(delete(Budget).where(Budget.user_id == user_id))
        await self.session.execute(delete(Category).where(Category.user_id == user_id))
        await self.session.execute(delete(Account).where(Account.user_id == user_id))

    async def _seed(self, user_id: UUID) -> None:
        now = datetime.now(UTC)
        current_month_start = date(now.year, now.month, 1)

        accounts = await self._create_accounts(user_id)
        categories = await self._create_categories(user_id)
        await self._create_budgets(user_id, categories, current_month_start)
        await self._create_recurring(user_id, accounts, categories, now)
        await self._create_transactions(user_id, accounts, categories, now)

        await self.session.commit()
        await cache.bump_user_report_version(user_id)

    async def _create_accounts(self, user_id: UUID) -> dict[str, UUID]:
        currency = normalize_currency("USD")
        checking = await self.account_repository.create(
            user_id=user_id,
            name="Everyday Checking",
            account_type=AccountType.CHECKING.value,
            opening_balance=quantize_money(Decimal("1200.00")),
            currency=currency,
            color="#2E86AB",
            icon="🏦",
        )
        savings = await self.account_repository.create(
            user_id=user_id,
            name="Rainy Day Savings",
            account_type=AccountType.SAVINGS.value,
            opening_balance=quantize_money(Decimal("3000.00")),
            currency=currency,
            color="#5FAD56",
            icon="💰",
            goal_name="Emergency Fund",
            goal_target_amount=quantize_money(Decimal("5000.00")),
            goal_target_date=date.today() + timedelta(days=180),
        )
        credit = await self.account_repository.create(
            user_id=user_id,
            name="Everyday Credit Card",
            account_type=AccountType.CREDIT_CARD.value,
            opening_balance=quantize_money(Decimal("-600.00")),
            currency=currency,
            color="#C73E1D",
            icon="💳",
        )
        return {
            "checking": checking.id,
            "savings": savings.id,
            "credit": credit.id,
        }

    async def _create_categories(self, user_id: UUID) -> dict[str, UUID]:
        expense_categories = [
            ("Rent", "#E76F51", "🏠"),
            ("Groceries", "#2A9D8F", "🛒"),
            ("Utilities", "#457B9D", "💡"),
            ("Dining", "#F4A261", "🍽️"),
            ("Transport", "#6D597A", "🚗"),
            ("Entertainment", "#B56576", "🎬"),
            ("Shopping", "#A8DADC", "🛍️"),
            ("Health", "#4D908E", "🩺"),
        ]
        income_categories = [
            ("Salary", "#2F9E44", "💼"),
            ("Interest", "#1C7ED6", "🏦"),
        ]

        mapping: dict[str, UUID] = {}
        for name, color, icon in expense_categories:
            category = await self.category_repository.create(
                user_id=user_id,
                name=validate_category_name(name),
                is_income=False,
                color=normalize_category_color(color),
                icon=normalize_category_icon(icon),
            )
            mapping[name] = category.id
        for name, color, icon in income_categories:
            category = await self.category_repository.create(
                user_id=user_id,
                name=validate_category_name(name),
                is_income=True,
                color=normalize_category_color(color),
                icon=normalize_category_icon(icon),
            )
            mapping[name] = category.id
        return mapping

    async def _create_budgets(
        self,
        user_id: UUID,
        categories: dict[str, UUID],
        month_start: date,
    ) -> None:
        budget_config = [
            ("Rent", "1200.00", False),
            ("Groceries", "450.00", True),
            ("Dining", "200.00", False),
            ("Utilities", "180.00", False),
            ("Entertainment", "150.00", False),
        ]
        month_key = month_start.strftime("%Y-%m")
        for name, limit, rollover in budget_config:
            await self.budget_repository.create(
                user_id=user_id,
                category_id=categories[name],
                month_start=parse_budget_month(month_key),
                limit_amount=validate_budget_limit(Decimal(limit)),
                rollover_enabled=rollover,
            )

    async def _create_recurring(
        self,
        user_id: UUID,
        accounts: dict[str, UUID],
        categories: dict[str, UUID],
        now: datetime,
    ) -> None:
        start_at = normalize_start_at(datetime(now.year, now.month, 1, tzinfo=UTC))
        for direction, amount, account_key, category_key, merchant in [
            (TransactionDirection.IN, "3200.00", "checking", "Salary", "Salary"),
            (TransactionDirection.OUT, "1200.00", "checking", "Rent", "Rent"),
            (TransactionDirection.OUT, "150.00", "checking", "Utilities", "Utilities"),
        ]:
            recurring = RecurringTransaction(
                user_id=user_id,
                account_id=accounts[account_key],
                category_id=categories[category_key],
                amount=validate_transaction_amount(Decimal(amount)),
                direction=direction.value,
                cadence=RecurringCadence.MONTHLY.value,
                interval=1,
                start_at=start_at,
                next_run_at=align_next_run(start_at, RecurringCadence.MONTHLY, 1, now),
                end_at=None,
                merchant=normalize_merchant(merchant),
                note=None,
                tags=None,
                is_active=True,
            )
            await self.recurring_repository.create(recurring)

    async def _create_transactions(
        self,
        user_id: UUID,
        accounts: dict[str, UUID],
        categories: dict[str, UUID],
        now: datetime,
    ) -> None:
        checking_id = accounts["checking"]
        savings_id = accounts["savings"]

        def month_date(months_back: int, day: int) -> datetime:
            year = now.year
            month = now.month - months_back
            while month <= 0:
                month += 12
                year -= 1
            days_in_month = monthrange(year, month)[1]
            if months_back == 0:
                safe_day = min(day, max(1, now.day - 1))
            else:
                safe_day = min(day, days_in_month)
            return datetime(year, month, safe_day, tzinfo=UTC)

        await self._add_transaction(
            account_id=checking_id,
            category_id=categories["Salary"],
            amount="3200.00",
            direction=TransactionDirection.IN,
            occurred_at=month_date(0, 1),
            merchant="Salary",
            note="Monthly paycheck",
        )
        await self._add_transaction(
            account_id=savings_id,
            category_id=categories["Interest"],
            amount="12.00",
            direction=TransactionDirection.IN,
            occurred_at=month_date(0, 15),
            merchant="Interest",
            note="Savings interest",
        )
        await self._add_transaction(
            account_id=checking_id,
            category_id=categories["Rent"],
            amount="800.00",
            direction=TransactionDirection.OUT,
            occurred_at=month_date(0, 3),
            merchant="Rent",
        )
        await self._add_transaction(
            account_id=checking_id,
            category_id=categories["Utilities"],
            amount="60.00",
            direction=TransactionDirection.OUT,
            occurred_at=month_date(0, 6),
            merchant="Comcast",
        )
        await self._add_transaction(
            account_id=checking_id,
            category_id=categories["Utilities"],
            amount="30.00",
            direction=TransactionDirection.OUT,
            occurred_at=month_date(0, 8),
            merchant="City Power",
        )

        groceries = [
            (5, "Whole Foods", "180.00"),
            (12, "Trader Joe's", "120.00"),
            (20, "Safeway", "60.00"),
        ]
        for day, merchant, amount in groceries:
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Groceries"],
                amount=amount,
                direction=TransactionDirection.OUT,
                occurred_at=month_date(0, day),
                merchant=merchant,
            )

        dining = [
            (8, "Starbucks", "25.00"),
            (10, "Starbucks", "18.00"),
            (14, "Starbucks", "22.00"),
            (16, "Starbucks", "15.00"),
            (18, "Local Bistro", "60.00"),
            (21, "Sushi Place", "50.00"),
            (24, "Coffee Corner", "50.00"),
        ]
        for day, merchant, amount in dining:
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Dining"],
                amount=amount,
                direction=TransactionDirection.OUT,
                occurred_at=month_date(0, day),
                merchant=merchant,
            )

        entertainment = [
            (18, "Netflix", "15.00"),
            (20, "Spotify", "10.00"),
            (23, "Cinema", "35.00"),
        ]
        for day, merchant, amount in entertainment:
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Entertainment"],
                amount=amount,
                direction=TransactionDirection.OUT,
                occurred_at=month_date(0, day),
                merchant=merchant,
            )

        transport = [
            (9, "Uber", "60.00"),
            (11, "Shell", "60.00"),
        ]
        for day, merchant, amount in transport:
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Transport"],
                amount=amount,
                direction=TransactionDirection.OUT,
                occurred_at=month_date(0, day),
                merchant=merchant,
            )

        shopping = [
            (13, "Amazon", "120.00"),
            (25, "Target", "30.00"),
        ]
        for day, merchant, amount in shopping:
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Shopping"],
                amount=amount,
                direction=TransactionDirection.OUT,
                occurred_at=month_date(0, day),
                merchant=merchant,
            )

        await self._add_transaction(
            account_id=checking_id,
            category_id=categories["Health"],
            amount="40.00",
            direction=TransactionDirection.OUT,
            occurred_at=month_date(0, 17),
            merchant="CVS",
        )

        for months_back in (1, 2):
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Salary"],
                amount="3200.00",
                direction=TransactionDirection.IN,
                occurred_at=month_date(months_back, 1),
                merchant="Salary",
            )
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Rent"],
                amount="1200.00",
                direction=TransactionDirection.OUT,
                occurred_at=month_date(months_back, 3),
                merchant="Rent",
            )
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Utilities"],
                amount="150.00",
                direction=TransactionDirection.OUT,
                occurred_at=month_date(months_back, 6),
                merchant="Utilities",
            )
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Groceries"],
                amount="300.00",
                direction=TransactionDirection.OUT,
                occurred_at=month_date(months_back, 12),
                merchant="Whole Foods",
            )
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Dining"],
                amount="180.00",
                direction=TransactionDirection.OUT,
                occurred_at=month_date(months_back, 18),
                merchant="Starbucks",
            )

        transfer_id = uuid4()
        await self._add_transaction(
            account_id=checking_id,
            category_id=None,
            amount="500.00",
            direction=TransactionDirection.OUT,
            occurred_at=month_date(0, 10),
            merchant="Transfer",
            note="Move to savings",
            transfer_id=transfer_id,
        )
        await self._add_transaction(
            account_id=savings_id,
            category_id=None,
            amount="500.00",
            direction=TransactionDirection.IN,
            occurred_at=month_date(0, 10),
            merchant="Transfer",
            note="Move from checking",
            transfer_id=transfer_id,
        )

        for day_offset in range(35, 90, 4):
            occurred_at = now - timedelta(days=day_offset)
            amount = Decimal("6.00") + Decimal(day_offset % 5)
            await self._add_transaction(
                account_id=checking_id,
                category_id=categories["Transport"],
                amount=str(amount),
                direction=TransactionDirection.OUT,
                occurred_at=occurred_at,
                merchant="Metro",
            )

    async def _add_transaction(
        self,
        *,
        account_id: UUID,
        category_id: UUID | None,
        amount: str,
        direction: TransactionDirection,
        occurred_at: datetime,
        merchant: str | None,
        note: str | None = None,
        transfer_id: UUID | None = None,
    ) -> None:
        await self.transaction_repository.create(
            account_id=account_id,
            category_id=category_id,
            amount=validate_transaction_amount(Decimal(amount)),
            direction=validate_transaction_direction(direction.value).value,
            occurred_at=normalize_occurred_at(occurred_at),
            merchant=normalize_merchant(merchant),
            note=normalize_note(note),
            tags=None,
            transfer_id=transfer_id,
        )
