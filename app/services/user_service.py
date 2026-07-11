from datetime import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import User
from app.db.repositories.users import UserRepository


class UserService:
    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self.users = UserRepository(session)
        self.settings = settings or get_settings()

    async def ensure_user(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        return await self.users.get_or_create_pending(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            default_timezone=self.settings.app_timezone,
            default_push_time=time(
                self.settings.default_push_hour,
                self.settings.default_push_minute,
            ),
        )
