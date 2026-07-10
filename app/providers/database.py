from app.db.models import ContentItem
from app.db.repositories.contents import ContentRepository
from app.domain.enums import ContentType


class DatabaseContentProvider:
    def __init__(self, repository: ContentRepository) -> None:
        self.repository = repository

    async def get_random(self, content_type: ContentType) -> ContentItem | None:
        return await self.repository.get_random_approved(content_type)
