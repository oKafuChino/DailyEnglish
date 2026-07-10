from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.domain.enums import UserStatus
from app.domain.scheduling import next_daily_push_at
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

    async def activate(self, user: User, *, at: datetime | None = None) -> None:
        at = at or datetime.now(UTC)
        user.status = UserStatus.ACTIVE
        user.registered_at = user.registered_at or at
        user.last_active_at = at
        if user.daily_push_enabled and user.next_push_at is None:
            user.next_push_at = next_daily_push_at(
                timezone_name=user.timezone,
                push_time=user.daily_push_time,
                after=at,
            )

    async def initialize_missing_push_schedules(self, *, now: datetime) -> int:
        users = list(
            await self.session.scalars(
                select(User).where(
                    User.status == UserStatus.ACTIVE,
                    User.daily_push_enabled.is_(True),
                    User.next_push_at.is_(None),
                )
            )
        )
        for user in users:
            user.next_push_at = next_daily_push_at(
                timezone_name=user.timezone,
                push_time=user.daily_push_time,
                after=now,
            )
        return len(users)
