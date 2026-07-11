import asyncio
import logging

from aiogram import Bot

from app.config import get_settings
from app.db.session import close_database, session_scope
from app.logging import configure_logging
from app.services.content_service import ContentService
from app.workers.daily_push import DailyPushWorker

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    settings.validate_bot_runtime()
    configure_logging(settings.log_level)
    async with session_scope() as session:
        synchronized = await ContentService(session).sync_packaged_content()
    logger.info("Packaged content synchronized entries=%d", synchronized)
    logger.info("DailyEnglish worker started")
    bot = Bot(token=settings.bot_token.get_secret_value())
    worker = DailyPushWorker(
        retry_minutes=settings.delivery_retry_minutes,
        max_attempts=settings.delivery_max_attempts,
        alert_failure_threshold=settings.alert_failure_threshold,
        owner_telegram_id=settings.owner_telegram_id,
    )

    try:
        while True:
            try:
                processed = await worker.run_once(bot)
                if processed:
                    logger.info("Processed %d due users", processed)
            except Exception:
                logger.exception("Daily push polling cycle failed")
            await asyncio.sleep(settings.worker_poll_interval_seconds)
    finally:
        await bot.session.close()
        await close_database()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
