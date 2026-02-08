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
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    cookie_name: str = Field(default="finance_session", alias="COOKIE_NAME")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.environment.lower() == "production":
            if self.secret_key in {"change-me", "change-me-generate-with-openssl-rand-hex-32"}:
                raise ValueError("SECRET_KEY must be explicitly configured in production")
            if not self.database_url.lower().startswith("postgresql"):
                raise ValueError("DATABASE_URL must use PostgreSQL in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
