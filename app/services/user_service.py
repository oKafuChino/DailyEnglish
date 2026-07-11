from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import User
from app.db.repositories.users import UserRepository
from app.domain.scheduling import next_daily_push_at
from app.domain.time import UTC

ALLOWED_DIFFICULTIES = {"B1", "B2", "C1"}
DEFAULT_DIFFICULTIES = ("B1", "B2", "C1")


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

    async def set_push_time(
        self,
        *,
        user_id: int,
        push_time: time,
        now: datetime | None = None,
    ) -> User:
        user = await self._get_for_update(user_id)
        user.daily_push_time = push_time
        self._reschedule(user, now=now)
        return user

    async def set_timezone(
        self,
        *,
        user_id: int,
        timezone_name: str,
        now: datetime | None = None,
    ) -> User:
        if len(timezone_name) > 64:
            raise ValueError("Timezone name is too long")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown IANA timezone") from exc
        user = await self._get_for_update(user_id)
        user.timezone = timezone_name
        self._reschedule(user, now=now)
        return user

    async def toggle_daily_push(
        self,
        *,
        user_id: int,
        now: datetime | None = None,
    ) -> User:
        user = await self._get_for_update(user_id)
        user.daily_push_enabled = not user.daily_push_enabled
        self._reschedule(user, now=now)
        return user

    async def toggle_preferred_difficulty(
        self,
        *,
        user_id: int,
        difficulty: str,
    ) -> User:
        normalized = difficulty.strip().upper()
        if normalized not in ALLOWED_DIFFICULTIES:
            raise ValueError("Unsupported difficulty")
        user = await self._get_for_update(user_id)
        selected = parse_preferred_difficulties(user.preferred_difficulty)
        if normalized in selected:
            if len(selected) == 1:
                raise ValueError("At least one difficulty must remain selected")
            selected.remove(normalized)
        else:
            selected.append(normalized)
        user.preferred_difficulty = format_preferred_difficulties(selected)
        return user

    async def _get_for_update(self, user_id: int) -> User:
        user = await self.users.get_by_id_for_update(user_id)
        if user is None:
            raise LookupError("User does not exist")
        return user

    @staticmethod
    def _reschedule(user: User, *, now: datetime | None) -> None:
        if not user.daily_push_enabled:
            user.next_push_at = None
            return
        user.next_push_at = next_daily_push_at(
            timezone_name=user.timezone,
            push_time=user.daily_push_time,
            after=now or datetime.now(UTC),
        )


def parse_preferred_difficulties(value: str | None) -> list[str]:
    if not value or value == "mixed":
        return list(DEFAULT_DIFFICULTIES)
    selected: list[str] = []
    for item in value.split(","):
        difficulty = item.strip().upper()
        if difficulty in ALLOWED_DIFFICULTIES and difficulty not in selected:
            selected.append(difficulty)
    return selected or list(DEFAULT_DIFFICULTIES)


def format_preferred_difficulties(values: list[str]) -> str:
    order = {difficulty: index for index, difficulty in enumerate(DEFAULT_DIFFICULTIES)}
    normalized = [
        difficulty
        for difficulty in sorted(set(values), key=lambda item: order.get(item, 99))
        if difficulty in ALLOWED_DIFFICULTIES
    ]
    if not normalized:
        raise ValueError("At least one difficulty must remain selected")
    return ",".join(normalized)
