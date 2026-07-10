import asyncio

from sqlalchemy import text

from app.db.session import close_database, get_engine


async def check() -> None:
    try:
        async with get_engine().connect() as connection:
            await asyncio.wait_for(connection.execute(text("SELECT 1")), timeout=5)
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(check())
