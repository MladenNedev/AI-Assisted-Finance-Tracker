from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.persistence.models import User
from app.persistence.repositories import SessionRepository, UserRepository
from app.persistence.session import AsyncSessionLocal
from app.services.auth_service import AuthService


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


async def get_current_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    cookie_name = get_settings().cookie_name
    token = request.cookies.get(cookie_name)
    if token is None:
        raise AuthenticationError("Not authenticated")
    return await auth_service.get_current_user_from_session(token)
