from datetime import datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.keyboards.settings import SettingsCallback, settings_keyboard
from app.bot.routers.settings import format_settings, parse_push_time
from app.domain.time import UTC
from app.services.user_service import UserService


def make_user(**overrides):
    values = {
        "id": 1,
        "daily_push_enabled": True,
        "daily_push_time": time(8),
        "timezone": "Asia/Shanghai",
        "preferred_difficulty": "mixed",
        "next_push_at": datetime(2026, 7, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.parametrize("value", ["8:30", "08:3", "24:00", "12:60", "08:30:00", ""])
def test_parse_push_time_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_push_time(value)


def test_parse_push_time_accepts_24_hour_hh_mm() -> None:
    assert parse_push_time(" 08:30 ") == time(8, 30)


@pytest.mark.asyncio
async def test_toggle_push_clears_and_restores_next_schedule() -> None:
    user = make_user()
    service = UserService(SimpleNamespace())
    service.users = SimpleNamespace(get_by_id_for_update=AsyncMock(return_value=user))
    now = datetime(2026, 7, 11, 10, tzinfo=UTC)

    await service.toggle_daily_push(user_id=user.id, now=now)
    assert user.daily_push_enabled is False
    assert user.next_push_at is None

    await service.toggle_daily_push(user_id=user.id, now=now)
    assert user.daily_push_enabled is True
    assert user.next_push_at == datetime(2026, 7, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_timezone_change_validates_and_reschedules() -> None:
    user = make_user()
    service = UserService(SimpleNamespace())
    service.users = SimpleNamespace(get_by_id_for_update=AsyncMock(return_value=user))
    now = datetime(2026, 7, 11, 10, tzinfo=UTC)

    with pytest.raises(ValueError, match="Unknown IANA timezone"):
        await service.set_timezone(user_id=user.id, timezone_name="Mars/Olympus", now=now)

    await service.set_timezone(user_id=user.id, timezone_name="Europe/London", now=now)
    assert user.timezone == "Europe/London"
    assert user.next_push_at == datetime(2026, 7, 12, 7, tzinfo=UTC)


def test_settings_panel_and_callback_data_are_complete() -> None:
    user = make_user()
    text = format_settings(user)
    keyboard = settings_keyboard(push_enabled=True, preferred_difficulty="B2")

    assert "已开启" in text
    assert "Asia/Shanghai" in text
    assert "难度：混合" in text
    packed = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert SettingsCallback(action="toggle").pack() in packed
    assert SettingsCallback(action="time").pack() in packed
    assert SettingsCallback(action="timezone").pack() in packed
    assert SettingsCallback(action="difficulty", value="B1").pack() in packed
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "🎚️ 难度：B2" in labels
    assert "✅ B2" in labels


@pytest.mark.asyncio
async def test_set_preferred_difficulty_validates_values() -> None:
    user = make_user()
    service = UserService(SimpleNamespace())
    service.users = SimpleNamespace(get_by_id_for_update=AsyncMock(return_value=user))

    await service.set_preferred_difficulty(user_id=user.id, difficulty="b2")
    assert user.preferred_difficulty == "B2"

    await service.set_preferred_difficulty(user_id=user.id, difficulty="mixed")
    assert user.preferred_difficulty == "mixed"

    with pytest.raises(ValueError):
        await service.set_preferred_difficulty(user_id=user.id, difficulty="A1")
