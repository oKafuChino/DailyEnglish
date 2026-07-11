import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Favorite
from app.db.repositories.contents import ContentRepository
from app.db.repositories.favorites import FavoriteRepository
from app.exceptions import FavoriteContentNotFoundError


class FavoriteService:
    def __init__(self, session: AsyncSession) -> None:
        self.contents = ContentRepository(session)
        self.favorites = FavoriteRepository(session)

    async def add(self, *, user_id: int, content_id: uuid.UUID) -> bool:
        if await self.contents.get_by_id(content_id) is None:
            raise FavoriteContentNotFoundError
        return await self.favorites.add(user_id=user_id, content_id=content_id)

    async def remove(self, *, user_id: int, content_id: uuid.UUID) -> bool:
        return await self.favorites.remove(user_id=user_id, content_id=content_id)

    async def list_page(
        self,
        *,
        user_id: int,
        page: int,
        page_size: int = 5,
    ) -> tuple[list[Favorite], int]:
        if page < 1:
            raise ValueError("Page must be positive")
        total = await self.favorites.count_for_user(user_id)
        items = await self.favorites.list_for_user(
            user_id=user_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return items, total

    async def list_word_favorites(self, *, user_id: int) -> list[Favorite]:
        return await self.favorites.list_word_favorites_for_user(user_id=user_id)
