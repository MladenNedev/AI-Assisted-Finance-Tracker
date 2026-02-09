from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/finance_tracker",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    report_cache_ttl_seconds: int = Field(default=300, alias="REPORT_CACHE_TTL_SECONDS")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    cookie_name: str = Field(default="finance_session", alias="COOKIE_NAME")
    csrf_enabled: bool = Field(default=True, alias="CSRF_ENABLED")
    csrf_cookie_name: str = Field(default="finance_csrf", alias="CSRF_COOKIE_NAME")
    csrf_header_name: str = Field(default="X-CSRF-Token", alias="CSRF_HEADER_NAME")
    session_max_age_seconds: int = Field(default=86400, alias="SESSION_MAX_AGE_SECONDS")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_login_limit: int = Field(default=200, alias="RATE_LIMIT_LOGIN_LIMIT")
    rate_limit_login_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_LOGIN_WINDOW_SECONDS"
    )
    rate_limit_register_limit: int = Field(default=100, alias="RATE_LIMIT_REGISTER_LIMIT")
    rate_limit_register_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_REGISTER_WINDOW_SECONDS"
    )
    rate_limit_reporting_limit: int = Field(default=400, alias="RATE_LIMIT_REPORTING_LIMIT")
    rate_limit_reporting_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_REPORTING_WINDOW_SECONDS"
    )

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.environment.lower() == "production":
            if self.secret_key in {"change-me", "change-me-generate-with-openssl-rand-hex-32"}:
                raise ValueError("SECRET_KEY must be explicitly configured in production")
            if not self.database_url.lower().startswith("postgresql"):
                raise ValueError("DATABASE_URL must use PostgreSQL in production")
        if self.rate_limit_login_limit <= 0 or self.rate_limit_login_window_seconds <= 0:
            raise ValueError("Login rate limit values must be greater than zero")
        if self.rate_limit_register_limit <= 0 or self.rate_limit_register_window_seconds <= 0:
            raise ValueError("Register rate limit values must be greater than zero")
        if self.rate_limit_reporting_limit <= 0 or self.rate_limit_reporting_window_seconds <= 0:
            raise ValueError("Reporting rate limit values must be greater than zero")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
