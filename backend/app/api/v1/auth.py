from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_auth_service, get_current_user
from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.core.security import generate_csrf_token
from app.persistence.models import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


async def enforce_login_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    await enforce_rate_limit(
        request,
        RateLimitPolicy(
            scope="auth_login",
            limit=settings.rate_limit_login_limit,
            window_seconds=settings.rate_limit_login_window_seconds,
        ),
    )


async def enforce_register_rate_limit(request: Request) -> None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return
    await enforce_rate_limit(
        request,
        RateLimitPolicy(
            scope="auth_register",
            limit=settings.rate_limit_register_limit,
            window_seconds=settings.rate_limit_register_window_seconds,
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
    token = await auth_service.login(email=payload.email, password=payload.password)
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
