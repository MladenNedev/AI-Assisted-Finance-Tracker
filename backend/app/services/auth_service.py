from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    SessionExpiredError,
)
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.domain.user import normalize_email, validate_password_strength
from app.persistence.models import User
from app.persistence.repositories import SessionRepository, UserRepository


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        session_repository: SessionRepository,
    ) -> None:
        self.session = session
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.settings = get_settings()

    async def register(self, email: str, password: str) -> User:
        normalized_email = normalize_email(email)
        validate_password_strength(password)

        existing_user = await self.user_repository.get_by_email(normalized_email)
        if existing_user is not None:
            raise EmailAlreadyExistsError("Email is already registered")

        try:
            user = await self.user_repository.create(
                email=normalized_email,
                hashed_password=hash_password(password),
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise EmailAlreadyExistsError("Email is already registered") from exc

        await self.session.refresh(user)
        return user

    async def login(self, email: str, password: str) -> str:
        normalized_email = normalize_email(email)
        user = await self.user_repository.get_by_email(normalized_email)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        token = generate_session_token()
        token_hash = hash_session_token(token)
        expires_at = datetime.now(UTC) + timedelta(seconds=self.settings.session_max_age_seconds)
        await self.session_repository.create(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self.session.commit()
        return token

    async def logout(self, token: str) -> None:
        token_hash = hash_session_token(token)
        auth_session = await self.session_repository.get_by_token_hash(token_hash)
        if auth_session is None or auth_session.revoked_at is not None:
            return

        self.session_repository.revoke(auth_session, revoked_at=datetime.now(UTC))
        await self.session.commit()

    async def get_current_user_from_session(self, token: str) -> User:
        token_hash = hash_session_token(token)
        now = datetime.now(UTC)
        auth_session = await self.session_repository.get_active_by_token_hash(token_hash, now)
        if auth_session is None:
            raise SessionExpiredError("Session is invalid or expired")

        user = await self.user_repository.get_by_id(auth_session.user_id)
        if user is None:
            raise AuthenticationError("User not found for session")

        return user
