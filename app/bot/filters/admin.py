from aiogram.filters import BaseFilter
from aiogram.types import Message

from app.config import get_settings


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user and message.from_user.id == get_settings().owner_telegram_id)
