from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import get_settings
from app.db.repositories.users import UserRepository
from app.db.session import session_scope
from app.domain.enums import UserStatus
from app.services.user_service import UserService


class RegistrationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)) or event.from_user is None:
            return await handler(event, data)

        current_user = None
        async with session_scope() as session:
            users = UserRepository(session)
            user = await users.get_by_telegram_id(event.from_user.id)
            if event.from_user.id == get_settings().owner_telegram_id and user is None:
                chat_id = (
                    event.chat.id
                    if isinstance(event, Message)
                    else event.message.chat.id
                    if event.message
                    else event.from_user.id
                )
                user = await UserService(session).ensure_user(
                    telegram_user_id=event.from_user.id,
                    chat_id=chat_id,
                    username=event.from_user.username,
                    first_name=event.from_user.first_name,
                    last_name=event.from_user.last_name,
                )
                await users.activate(user)
            if user is not None and user.status == UserStatus.ACTIVE:
                current_user = user

        if current_user is not None:
            data["current_user"] = current_user
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            await event.answer("请先完成注册。", show_alert=True)
        else:
            await event.answer("请先使用 /register <邀请码> 完成注册。")
        return None
