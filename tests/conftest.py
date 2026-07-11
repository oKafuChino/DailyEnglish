import os

import pytest
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base

RESET_CONFIRMATION = "dailyenglish-test-database-reset"


def validate_test_database_target(database_url: str, confirmation: str | None) -> URL:
    if confirmation != RESET_CONFIRMATION:
        raise RuntimeError(
            "Refusing to reset database: set TEST_DATABASE_RESET_CONFIRM to the documented "
            "test-only confirmation value"
        )
    try:
        parsed = make_url(database_url)
    except ValueError as exc:
        raise RuntimeError("Refusing to reset database: TEST_DATABASE_URL is invalid") from exc
    if parsed.drivername != "postgresql+asyncpg":
        raise RuntimeError(
            "Refusing to reset database: TEST_DATABASE_URL must use postgresql+asyncpg"
        )

    database_name = (parsed.database or "").lower()
    explicitly_test_named = database_name.startswith("test_") or database_name.endswith("_test")
    if not explicitly_test_named:
        raise RuntimeError(
            "Refusing to reset database: database name must start with 'test_' or end with '_test'"
        )
    return parsed


@pytest.fixture
async def postgres_session_factory():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    validate_test_database_target(
        database_url,
        os.getenv("TEST_DATABASE_RESET_CONFIRM"),
    )

    engine = create_async_engine(database_url, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
