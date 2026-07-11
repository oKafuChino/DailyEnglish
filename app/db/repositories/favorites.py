import uuid

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ContentItem, Favorite
from app.domain.enums import ContentType


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, *, user_id: int, content_id: uuid.UUID) -> bool:
        statement = (
            insert(Favorite)
            .values(user_id=user_id, content_id=content_id)
            .on_conflict_do_nothing(index_elements=["user_id", "content_id"])
            .returning(Favorite.id)
        )
        return await self.session.scalar(statement) is not None

    async def remove(self, *, user_id: int, content_id: uuid.UUID) -> bool:
        statement = (
            delete(Favorite)
            .where(Favorite.user_id == user_id, Favorite.content_id == content_id)
            .returning(Favorite.id)
        )
        return await self.session.scalar(statement) is not None

    async def list_for_user(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
    ) -> list[Favorite]:
        result = await self.session.scalars(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .options(selectinload(Favorite.content))
            .order_by(Favorite.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result)

    async def count_for_user(self, user_id: int) -> int:
        from sqlalchemy import func

        return int(
            await self.session.scalar(
                select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
            )
            or 0
        )

    async def list_word_favorites_for_user(self, *, user_id: int) -> list[Favorite]:
        result = await self.session.scalars(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .join(Favorite.content)
            .where(ContentItem.content_type == ContentType.WORD)
            .options(selectinload(Favorite.content))
            .order_by(Favorite.created_at.desc())
        )
        return list(result)
