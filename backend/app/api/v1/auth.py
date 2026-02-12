import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_auth_service, get_current_user
from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.core.security import generate_csrf_token
from app.persistence.models import User
from app.persistence.repositories import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    RecurringTransactionRepository,
    TransactionRepository,
)
from app.schemas.auth import (
    DemoResetResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.demo_seed_service import DemoSeedService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


async def enforce_login_rate_limit(request: Request) -> None:
    await _enforce_rate_limit(
        request,
        scope="auth_login",
        limit=get_settings().rate_limit_login_limit,
        window_seconds=get_settings().rate_limit_login_window_seconds,
    )


async def enforce_register_rate_limit(request: Request) -> None:
    await _enforce_rate_limit(
        request,
        scope="auth_register",
        limit=get_settings().rate_limit_register_limit,
        window_seconds=get_settings().rate_limit_register_window_seconds,
    )


async def _enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    await enforce_rate_limit(
        request,
        RateLimitPolicy(
            scope=scope,
            limit=limit,
            window_seconds=window_seconds,
            fail_closed_on_unavailable=settings.rate_limit_auth_fail_closed,
        ),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[None, Depends(enforce_register_rate_limit)],
) -> UserResponse:
    user = await auth_service.register(email=payload.email, password=payload.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _: Annotated[None, Depends(enforce_login_rate_limit)],
) -> LoginResponse:
    await auth_service.ensure_demo_user(email=payload.email, password=payload.password)
    token, user = await auth_service.login(email=payload.email, password=payload.password)
    settings = get_settings()
    csrf_token = generate_csrf_token()

    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        secure=settings.environment.lower() == "production",
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,
        secure=settings.environment.lower() == "production",
        samesite="lax",
        max_age=settings.session_max_age_seconds,
        path="/",
    )
    response.headers[settings.csrf_header_name] = csrf_token

    if settings.demo_seed_enabled and user.email.lower() == settings.demo_email.lower():
        seeder = DemoSeedService(
            session=auth_service.session,
            account_repository=AccountRepository(auth_service.session),
            category_repository=CategoryRepository(auth_service.session),
            budget_repository=BudgetRepository(auth_service.session),
            transaction_repository=TransactionRepository(auth_service.session),
            recurring_repository=RecurringTransactionRepository(auth_service.session),
        )
        try:
            await seeder.seed_if_needed(user)
        except Exception:
            logger.exception("Failed to seed demo user data")

    return LoginResponse(status="ok")


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LogoutResponse:
    settings = get_settings()
    token = request.cookies.get(settings.cookie_name)
    if token is not None:
        await auth_service.logout(token)

    response.delete_cookie(
        key=settings.cookie_name,
        secure=settings.environment.lower() == "production",
        httponly=True,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        secure=settings.environment.lower() == "production",
        httponly=False,
        samesite="lax",
        path="/",
    )
    return LogoutResponse(status="ok")


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/demo/reset", response_model=DemoResetResponse)
async def reset_demo(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> DemoResetResponse:
    settings = get_settings()
    if not settings.demo_seed_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo disabled")
    if current_user.email.lower() != settings.demo_email.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    seeder = DemoSeedService(
        session=auth_service.session,
        account_repository=AccountRepository(auth_service.session),
        category_repository=CategoryRepository(auth_service.session),
        budget_repository=BudgetRepository(auth_service.session),
        transaction_repository=TransactionRepository(auth_service.session),
        recurring_repository=RecurringTransactionRepository(auth_service.session),
    )
    await seeder.reset_demo(current_user)
    return DemoResetResponse(status="ok")
