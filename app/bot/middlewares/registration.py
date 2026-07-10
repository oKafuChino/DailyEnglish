from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import get_settings
from app.db.repositories.users import UserRepository
from app.db.session import session_scope
from app.domain.enums import UserStatus


class RegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)
        if event.from_user.id == get_settings().owner_telegram_id:
            return await handler(event, data)

        async with session_scope() as session:
            user = await UserRepository(session).get_by_telegram_id(event.from_user.id)
            if user is not None and user.status == UserStatus.ACTIVE:
                data["current_user"] = user
                return await handler(event, data)

        await event.answer("请先使用 /register <邀请码> 完成注册。")
        return None
