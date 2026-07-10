from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.domain.enums import UserStatus
from app.domain.time import UTC


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )

    async def get_or_create_pending(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user = await self.get_by_telegram_id(telegram_user_id)
        now = datetime.now(UTC)
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                status=UserStatus.PENDING,
                last_active_at=now,
            )
            self.session.add(user)
            await self.session.flush()
            return user

        user.chat_id = chat_id
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.last_active_at = now
        return user

    async def activate(self, user: User, *, at: datetime) -> None:
        user.status = UserStatus.ACTIVE
        user.registered_at = user.registered_at or at
        user.last_active_at = at
