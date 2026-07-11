from datetime import datetime, time

import pytest

from app.db.repositories.users import UserRepository
from app.domain.enums import ContentType
from app.domain.time import UTC
from app.services.delivery_service import DeliveryService


@pytest.mark.asyncio
async def test_daily_delivery_slot_is_reused(postgres_session_factory) -> None:
    async with postgres_session_factory() as session:
        user = await UserRepository(session).get_or_create_pending(
            telegram_user_id=2001,
            chat_id=2001,
            username=None,
            first_name="Daily",
            last_name=None,
            default_timezone="UTC",
            default_push_time=time(8),
        )
        service = DeliveryService(session)
        scheduled = datetime(2026, 7, 12, 8, tzinfo=UTC)
        first = await service.get_or_create_daily(
            user=user,
            content_type=ContentType.WORD,
            local_date=scheduled.date(),
            scheduled_for=scheduled,
        )
        second = await service.get_or_create_daily(
            user=user,
            content_type=ContentType.WORD,
            local_date=scheduled.date(),
            scheduled_for=scheduled,
        )

        assert first.id == second.id
