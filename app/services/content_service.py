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

    async def get_random(self, content_type: ContentType) -> ContentItem:
        content = await self.contents.get_random_approved(content_type)
        if content is not None:
            return content

        seeds = await self.fallback_provider.list_content(content_type)
        await self.contents.add_approved_seeds(seeds)
        content = await self.contents.get_random_approved(content_type)
        if content is None:
            raise ContentUnavailableError(f"No approved {content_type.value} content available")
        return content

    async def get_word(self) -> ContentItem:
        return await self.get_random(ContentType.WORD)

    async def get_sentence(self) -> ContentItem:
        return await self.get_random(ContentType.SENTENCE)
