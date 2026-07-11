import asyncio
from datetime import time

import pytest

from app.db.models import User
from app.db.repositories.users import UserRepository
from app.exceptions import InviteCodeRedeemedError
from app.services.invite_service import InviteService


@pytest.mark.asyncio
async def test_invite_can_only_be_redeemed_once_under_concurrency(
    postgres_session_factory,
) -> None:
    pepper = "integration-pepper-with-at-least-32-characters"
    async with postgres_session_factory() as session:
        users = UserRepository(session)
        first = await users.get_or_create_pending(
            telegram_user_id=1001,
            chat_id=1001,
            username=None,
            first_name="One",
            last_name=None,
            default_timezone="UTC",
            default_push_time=time(8),
        )
        second = await users.get_or_create_pending(
            telegram_user_id=1002,
            chat_id=1002,
            username=None,
            first_name="Two",
            last_name=None,
            default_timezone="UTC",
            default_push_time=time(8),
        )
        created = await InviteService(session, pepper=pepper).create_invite(admin_telegram_id=42)
        first_id, second_id = first.id, second.id
        await session.commit()

    async def redeem(user_id: int):
        async with postgres_session_factory() as session:
            user = await session.get(User, user_id)
            try:
                await InviteService(session, pepper=pepper).redeem(
                    code=created.plain_code,
                    user=user,
                )
                await session.commit()
                return "redeemed"
            except Exception as exc:
                await session.rollback()
                return exc

    results = await asyncio.gather(redeem(first_id), redeem(second_id))

    assert results.count("redeemed") == 1
    assert sum(isinstance(result, InviteCodeRedeemedError) for result in results) == 1
