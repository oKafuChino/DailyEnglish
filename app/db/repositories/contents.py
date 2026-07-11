import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentItem
from app.domain.enums import ContentStatus, ContentType
from app.domain.schemas import ContentSeed


class ContentRepository:
    SEED_BATCH_SIZE = 500

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_random_approved(
        self,
        content_type: ContentType,
        *,
        difficulties: list[str] | None = None,
    ) -> ContentItem | None:
        count = await self.count_approved(content_type, difficulties=difficulties)
        if count <= 0:
            return None
        offset = uuid.uuid4().int % count
        filters = [
            ContentItem.content_type == content_type,
            ContentItem.status == ContentStatus.APPROVED,
        ]
        if difficulties:
            filters.append(ContentItem.difficulty.in_(difficulties))
        return await self.session.scalar(
            select(ContentItem)
            .where(*filters)
            .order_by(ContentItem.created_at, ContentItem.id)
            .offset(offset)
            .limit(1)
        )

    async def count_approved(
        self,
        content_type: ContentType,
        *,
        difficulties: list[str] | None = None,
    ) -> int:
        filters = [
            ContentItem.content_type == content_type,
            ContentItem.status == ContentStatus.APPROVED,
        ]
        if difficulties:
            filters.append(ContentItem.difficulty.in_(difficulties))
        return (
            await self.session.scalar(select(func.count()).select_from(ContentItem).where(*filters))
            or 0
        )

    async def get_by_id(self, content_id: uuid.UUID) -> ContentItem | None:
        return await self.session.get(ContentItem, content_id)

    async def add_approved_seeds(self, seeds: Sequence[ContentSeed]) -> None:
        if not seeds:
            return
        for start in range(0, len(seeds), self.SEED_BATCH_SIZE):
            batch = seeds[start : start + self.SEED_BATCH_SIZE]
            values = [
                {
                    "id": uuid.uuid4(),
                    **seed.model_dump(),
                    "content_hash": seed.content_hash,
                    "status": ContentStatus.APPROVED,
                }
                for seed in batch
            ]
            statement = insert(ContentItem).values(values)
            statement = statement.on_conflict_do_update(
                index_elements=["content_hash"],
                set_={
                    "example_en": func.coalesce(
                        ContentItem.example_en,
                        statement.excluded.example_en,
                    ),
                    "example_zh": func.coalesce(
                        ContentItem.example_zh,
                        statement.excluded.example_zh,
                    ),
                },
            )
            await self.session.execute(statement)
        await self.session.flush()
