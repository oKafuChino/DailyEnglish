import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, ErrorEvent, Message

from app.bot.middlewares.rate_limit import RateLimitMiddleware
from app.bot.routers import admin, public, review, user
from app.bot.routers import settings as settings_router
from app.config import get_settings
from app.db.session import close_database, session_scope
from app.logging import configure_logging
from app.services.content_service import ContentService

logger = logging.getLogger(__name__)


async def handle_error(event: ErrorEvent) -> bool:
    exception = event.exception
    logger.error(
        "Unhandled update error update_id=%s exception=%s",
        event.update.update_id,
        type(exception).__name__,
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    target: Message | CallbackQuery | None = event.update.callback_query or event.update.message
    try:
        if isinstance(target, CallbackQuery):
            await target.answer("处理请求时发生错误，请稍后再试。", show_alert=True)
        elif isinstance(target, Message):
            await target.answer("处理请求时发生错误，请稍后再试。")
    except Exception:
        logger.warning("Unable to send generic error response update_id=%s", event.update.update_id)
    return True


async def main() -> None:
    settings = get_settings()
    settings.validate_bot_runtime()
    configure_logging(settings.log_level)

    async with session_scope() as session:
        synchronized = await ContentService(session).sync_packaged_content()
    logger.info("Packaged content synchronized entries=%d", synchronized)

    bot = Bot(token=settings.bot_token.get_secret_value())
    dispatcher = Dispatcher()
    rate_limiter = RateLimitMiddleware(settings=settings)
    dispatcher.message.middleware(rate_limiter)
    dispatcher.callback_query.middleware(rate_limiter)
    dispatcher.errors.register(handle_error)
    dispatcher.include_routers(
        admin.router,
        public.router,
        review.router,
        settings_router.router,
        user.router,
    )

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        await close_database()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
