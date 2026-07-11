from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentItem
from app.db.repositories.contents import ContentRepository
from app.domain.enums import ContentType
from app.providers.base import ContentProvider
from app.providers.fallback import FallbackContentProvider


class ContentUnavailableError(RuntimeError):
    pass


class ContentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        fallback_provider: ContentProvider | None = None,
    ) -> None:
        self.contents = ContentRepository(session)
        self.fallback_provider = fallback_provider or FallbackContentProvider()

    async def get_random(
        self,
        content_type: ContentType,
        *,
        difficulty: str | None = None,
    ) -> ContentItem:
        normalized_difficulty = normalize_difficulty(difficulty)
        content = await self.contents.get_random_approved(
            content_type,
            difficulty=normalized_difficulty,
        )
        if content is None and normalized_difficulty is not None:
            content = await self.contents.get_random_approved(content_type)
        if content is not None:
            return content

        seeds = await self.fallback_provider.list_content(content_type)
        await self.contents.add_approved_seeds(seeds)
        content = await self.contents.get_random_approved(
            content_type,
            difficulty=normalized_difficulty,
        )
        if content is None and normalized_difficulty is not None:
            content = await self.contents.get_random_approved(content_type)
        if content is None:
            raise ContentUnavailableError(f"No approved {content_type.value} content available")
        return content

    async def sync_packaged_content(self) -> int:
        total = 0
        for content_type in (ContentType.WORD, ContentType.SENTENCE):
            seeds = await self.fallback_provider.list_content(content_type)
            await self.contents.add_approved_seeds(seeds)
            total += len(seeds)
        return total

    async def get_word(self, *, difficulty: str | None = None) -> ContentItem:
        return await self.get_random(ContentType.WORD, difficulty=difficulty)

    async def get_sentence(self, *, difficulty: str | None = None) -> ContentItem:
        return await self.get_random(ContentType.SENTENCE, difficulty=difficulty)


def normalize_difficulty(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper()
    return normalized if normalized in {"B1", "B2", "C1"} else None
