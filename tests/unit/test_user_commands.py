from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.routers import user as user_router
from app.bot.routers.user import word


@pytest.mark.asyncio
async def test_word_command_uses_user_preferred_difficulties(monkeypatch) -> None:
    content = SimpleNamespace(id="content-id")
    get_content = AsyncMock(return_value=content)
    answer = AsyncMock()
    current_user = SimpleNamespace(preferred_difficulty="B2,C1")

    monkeypatch.setattr(user_router, "_get_content", get_content)
    monkeypatch.setattr(user_router, "format_word", lambda _: "formatted-word")
    monkeypatch.setattr(user_router, "favorite_keyboard", lambda _: "keyboard")

    await word(SimpleNamespace(answer=answer), current_user)

    get_content.assert_awaited_once_with("word", preferred_difficulty="B2,C1")
    answer.assert_awaited_once_with(
        "formatted-word",
        parse_mode="HTML",
        reply_markup="keyboard",
    )
