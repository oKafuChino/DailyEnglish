from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_new_user_receives_configured_push_defaults() -> None:
    settings = Settings(
        _env_file=None,
        app_timezone="Europe/London",
        default_push_hour=9,
        default_push_minute=30,
    )
    service = UserService(SimpleNamespace(), settings=settings)
    service.users = SimpleNamespace(get_or_create_pending=AsyncMock(return_value="user"))

    result = await service.ensure_user(
        telegram_user_id=1,
        chat_id=1,
        username=None,
        first_name="Test",
        last_name=None,
    )

    assert result == "user"
    call = service.users.get_or_create_pending.await_args.kwargs
    assert call["default_timezone"] == "Europe/London"
    assert call["default_push_time"].isoformat() == "09:30:00"
