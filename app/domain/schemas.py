import hashlib

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ContentType


class ContentSeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_type: ContentType
    text_en: str
    translation_zh: str
    phonetic: str | None = None
    part_of_speech: str | None = None
    example_en: str | None = None
    example_zh: str | None = None
    attribution: str | None = None
    source: str = "builtin"
    difficulty: str | None = None
    extra_data: dict[str, object] = Field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        canonical = f"{self.content_type.value}:{self.text_en.strip().casefold()}"
        return hashlib.sha256(canonical.encode()).hexdigest()
