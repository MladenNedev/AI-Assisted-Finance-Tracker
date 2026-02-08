import asyncio
from collections.abc import Generator

import pytest
from app.core.config import get_settings
from app.main import app
from app.persistence.models import Base
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def _make_test_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)


async def _create_schema() -> None:
    engine = _make_test_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _drop_schema() -> None:
    engine = _make_test_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _truncate_tables() -> None:
    engine = _make_test_engine()
    async with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(table.delete())
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    asyncio.run(_drop_schema())
    asyncio.run(_create_schema())
    yield
    asyncio.run(_drop_schema())


@pytest.fixture(autouse=True)
def clear_database() -> Generator[None, None, None]:
    asyncio.run(_truncate_tables())
    yield
    asyncio.run(_truncate_tables())


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clear_client_cookies(client: TestClient) -> Generator[None, None, None]:
    client.cookies.clear()
    yield
    client.cookies.clear()
