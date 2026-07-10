from typing import Protocol

from app.domain.enums import ContentType
from app.domain.schemas import ContentSeed


class ContentProvider(Protocol):
    async def list_content(self, content_type: ContentType) -> list[ContentSeed]: ...
