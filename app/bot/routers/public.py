from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="public")


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("DailyEnglish Bot is running. Registration will be available soon.")
