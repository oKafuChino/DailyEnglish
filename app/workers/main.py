import asyncio
import logging

from sqlalchemy import text

from app.config import get_settings
from app.db.session import close_database, get_engine
from app.logging import configure_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("DailyEnglish worker started")

    try:
        while True:
            async with get_engine().connect() as connection:
                await connection.execute(text("SELECT 1"))
            await asyncio.sleep(settings.worker_poll_interval_seconds)
    finally:
        await close_database()


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
