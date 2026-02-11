from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.persistence.models import User
from app.persistence.repositories import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    RecurringTransactionRepository,
    ReportingRepository,
    SessionRepository,
    TransactionAttachmentRepository,
    TransactionRepository,
    UserRepository,
)
from app.persistence.session import AsyncSessionLocal
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.budget_service import BudgetService
from app.services.category_service import CategoryService
from app.services.recurring_service import RecurringTransactionService
from app.services.reporting_service import ReportingService
from app.services.transaction_service import TransactionService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserRepository:
    return UserRepository(session)


def get_session_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SessionRepository:
    return SessionRepository(session)


def get_account_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AccountRepository:
    return AccountRepository(session)


def get_transaction_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TransactionRepository:
    return TransactionRepository(session)


def get_recurring_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RecurringTransactionRepository:
    return RecurringTransactionRepository(session)


def get_attachment_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TransactionAttachmentRepository:
    return TransactionAttachmentRepository(session)


def get_category_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryRepository:
    return CategoryRepository(session)


def get_budget_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BudgetRepository:
    return BudgetRepository(session)


def get_reporting_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReportingRepository:
    return ReportingRepository(session)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
) -> AuthService:
    return AuthService(
        session=session,
        user_repository=user_repository,
        session_repository=session_repository,
    )


def get_account_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    account_repository: Annotated[AccountRepository, Depends(get_account_repository)],
) -> AccountService:
    return AccountService(session=session, account_repository=account_repository)


def get_transaction_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    account_repository: Annotated[AccountRepository, Depends(get_account_repository)],
    transaction_repository: Annotated[TransactionRepository, Depends(get_transaction_repository)],
    category_repository: Annotated[CategoryRepository, Depends(get_category_repository)],
    attachment_repository: Annotated[TransactionAttachmentRepository, Depends(get_attachment_repository)],
) -> TransactionService:
    return TransactionService(
        session=session,
        account_repository=account_repository,
        transaction_repository=transaction_repository,
        category_repository=category_repository,
        attachment_repository=attachment_repository,
    )


def get_recurring_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    recurring_repository: Annotated[
        RecurringTransactionRepository, Depends(get_recurring_repository)
    ],
    account_repository: Annotated[AccountRepository, Depends(get_account_repository)],
    category_repository: Annotated[CategoryRepository, Depends(get_category_repository)],
    transaction_repository: Annotated[TransactionRepository, Depends(get_transaction_repository)],
) -> RecurringTransactionService:
    return RecurringTransactionService(
        session=session,
        recurring_repository=recurring_repository,
        account_repository=account_repository,
        category_repository=category_repository,
        transaction_repository=transaction_repository,
    )


def get_category_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    category_repository: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> CategoryService:
    return CategoryService(session=session, category_repository=category_repository)


def get_budget_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    budget_repository: Annotated[BudgetRepository, Depends(get_budget_repository)],
    category_repository: Annotated[CategoryRepository, Depends(get_category_repository)],
) -> BudgetService:
    return BudgetService(
        session=session,
        budget_repository=budget_repository,
        category_repository=category_repository,
    )


def get_reporting_service(
    reporting_repository: Annotated[ReportingRepository, Depends(get_reporting_repository)],
) -> ReportingService:
    return ReportingService(reporting_repository=reporting_repository)


async def get_current_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    cookie_name = get_settings().cookie_name
    token = request.cookies.get(cookie_name)
    if token is None:
        raise AuthenticationError("Not authenticated")
    user = await auth_service.get_current_user_from_session(token)
    request.state.user_id = str(user.id)
    return user
