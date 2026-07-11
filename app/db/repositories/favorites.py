import uuid
from datetime import datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ContentItem, Favorite
from app.domain.enums import ContentStatus, ContentType


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

    async def list_review_candidates_for_user(
        self,
        *,
        user_id: int,
        limit: int,
        now: datetime,
    ) -> list[Favorite]:
        filters = [
            Favorite.user_id == user_id,
            ContentItem.content_type == ContentType.WORD,
            ContentItem.status == ContentStatus.APPROVED,
            or_(Favorite.reviewed_until.is_(None), Favorite.reviewed_until <= now),
        ]
        count = int(
            await self.session.scalar(
                select(func.count(Favorite.id)).join(Favorite.content).where(*filters)
            )
            or 0
        )
        if count <= 0:
            return []
        window_size = min(max(limit * 5, limit), count)
        offset = uuid.uuid4().int % max(count - window_size + 1, 1)
        result = await self.session.scalars(
            select(Favorite)
            .join(Favorite.content)
            .where(*filters)
            .options(selectinload(Favorite.content))
            .order_by(Favorite.created_at.desc())
            .offset(offset)
            .limit(window_size)
        )
        return list(result)

    async def list_review_distractors(
        self,
        *,
        exclude_content_id: uuid.UUID,
        limit: int,
    ) -> list[ContentItem]:
        filters = [
            ContentItem.content_type == ContentType.WORD,
            ContentItem.status == ContentStatus.APPROVED,
            ContentItem.id != exclude_content_id,
        ]
        count = int(
            await self.session.scalar(select(func.count(ContentItem.id)).where(*filters)) or 0
        )
        if count <= 0:
            return []
        offset = uuid.uuid4().int % max(count - limit + 1, 1)
        result = await self.session.scalars(
            select(ContentItem)
            .where(*filters)
            .order_by(ContentItem.created_at, ContentItem.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result)

    async def reset_word_review_cooldowns_for_user(
        self,
        *,
        user_id: int,
        now: datetime,
    ) -> int:
        word_content_ids = select(ContentItem.id).where(
            ContentItem.content_type == ContentType.WORD,
            ContentItem.status == ContentStatus.APPROVED,
        )
        result = await self.session.execute(
            update(Favorite)
            .where(
                Favorite.user_id == user_id,
                Favorite.reviewed_until.is_not(None),
                Favorite.reviewed_until > now,
                Favorite.content_id.in_(word_content_ids),
            )
            .values(reviewed_until=None)
        )
        await self.session.flush()
        return result.rowcount or 0

    async def mark_review_result(
        self,
        *,
        favorite_id: int,
        user_id: int,
        passed: bool,
        reviewed_until: datetime | None,
        now: datetime,
    ) -> bool:
        values = {
            "reviewed_until": reviewed_until,
            "review_last_at": now,
        }
        if passed:
            values["review_success_count"] = Favorite.review_success_count + 1
        else:
            values["review_fail_count"] = Favorite.review_fail_count + 1
        statement = (
            update(Favorite)
            .where(Favorite.id == favorite_id, Favorite.user_id == user_id)
            .values(**values)
            .returning(Favorite.id)
        )
        return await self.session.scalar(statement) is not None
