import asyncio

from aiogram import Bot, Dispatcher

from app.bot.routers import admin, public, user
from app.config import get_settings
from app.db.session import close_database
from app.logging import configure_logging


async def main() -> None:
    settings = get_settings()
    settings.validate_bot_runtime()
    configure_logging(settings.log_level)

    bot = Bot(token=settings.bot_token.get_secret_value())
    dispatcher = Dispatcher()
    dispatcher.include_routers(public.router, user.router, admin.router)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await close_database()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
