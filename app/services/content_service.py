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
        difficulties: list[str] | str | None = None,
    ) -> ContentItem:
        normalized_difficulties = normalize_difficulties(difficulties)
        content = await self.contents.get_random_approved(
            content_type,
            difficulties=normalized_difficulties,
        )
        if content is None and normalized_difficulties is not None:
            content = await self.contents.get_random_approved(content_type)
        if content is not None:
            return content

        seeds = await self.fallback_provider.list_content(content_type)
        await self.contents.add_approved_seeds(seeds)
        content = await self.contents.get_random_approved(
            content_type,
            difficulties=normalized_difficulties,
        )
        if content is None and normalized_difficulties is not None:
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

    async def get_word(self, *, difficulties: list[str] | str | None = None) -> ContentItem:
        return await self.get_random(ContentType.WORD, difficulties=difficulties)

    async def get_sentence(self, *, difficulties: list[str] | str | None = None) -> ContentItem:
        return await self.get_random(ContentType.SENTENCE, difficulties=difficulties)


def normalize_difficulties(value: list[str] | str | None) -> list[str] | None:
    if value is None:
        return None
    raw_values = value.split(",") if isinstance(value, str) else value
    normalized = []
    for item in raw_values:
        level = item.strip().upper()
        if level in {"B1", "B2", "C1"} and level not in normalized:
            normalized.append(level)
    return normalized or None
