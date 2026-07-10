from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message


class PrivateChatFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if isinstance(event, Message):
            return event.chat.type == "private"
        return bool(event.message and event.message.chat.type == "private")
