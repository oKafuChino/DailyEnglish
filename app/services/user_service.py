from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.users import UserRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

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
        )
