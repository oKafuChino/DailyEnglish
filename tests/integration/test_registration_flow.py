import asyncio
from datetime import time

import pytest
from sqlalchemy import select

from app.config import Settings
from app.db.models import User
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_concurrent_user_creation_is_an_atomic_upsert(postgres_session_factory) -> None:
    settings = Settings(
        _env_file=None,
        app_timezone="Europe/London",
        default_push_hour=9,
        default_push_minute=30,
    )

    async def ensure_user() -> int:
        async with postgres_session_factory() as session:
            user = await UserService(session, settings=settings).ensure_user(
                telegram_user_id=123456,
                chat_id=123456,
                username="learner",
                first_name="Test",
                last_name=None,
            )
            await session.commit()
            return user.id

    first_id, second_id = await asyncio.gather(ensure_user(), ensure_user())

    assert first_id == second_id
    async with postgres_session_factory() as session:
        users = list(await session.scalars(select(User)))
        assert len(users) == 1
        assert users[0].timezone == "Europe/London"
        assert users[0].daily_push_time == time(9, 30)
