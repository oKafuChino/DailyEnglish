import hashlib
from importlib.resources import files

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentItem
from app.db.repositories.app_state import AppStateRepository
from app.db.repositories.contents import ContentRepository
from app.domain.enums import ContentType
from app.providers.base import ContentProvider
from app.providers.fallback import FallbackContentProvider


class ContentUnavailableError(RuntimeError):
    pass


PACKAGED_CONTENT_STATE_KEY = "packaged_content_fingerprint"
PACKAGED_CONTENT_LOCK_ID = 202607110004


class ContentService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        fallback_provider: ContentProvider | None = None,
    ) -> None:
        self.session = session
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

        async for _ in self._sync_content_type(content_type):
            pass
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
        fingerprint = packaged_content_fingerprint()
        state = AppStateRepository(self.session)
        if await state.get(PACKAGED_CONTENT_STATE_KEY) == fingerprint:
            return 0

        lock_acquired = await self._try_packaged_content_lock()
        if not lock_acquired:
            return 0
        try:
            if await state.get(PACKAGED_CONTENT_STATE_KEY) == fingerprint:
                return 0
            total = 0
            for content_type in (ContentType.WORD, ContentType.SENTENCE):
                async for synchronized in self._sync_content_type(content_type):
                    total += synchronized
            await state.set(PACKAGED_CONTENT_STATE_KEY, fingerprint)
            return total
        finally:
            await self._unlock_packaged_content()

    async def _try_packaged_content_lock(self) -> bool:
        result = await self.contents.session.scalar(
            select(func.pg_try_advisory_xact_lock(PACKAGED_CONTENT_LOCK_ID))
        )
        return bool(result)

    async def _unlock_packaged_content(self) -> None:
        # Transaction-level advisory locks are released automatically on commit/rollback.
        return None

    async def get_word(self, *, difficulties: list[str] | str | None = None) -> ContentItem:
        return await self.get_random(ContentType.WORD, difficulties=difficulties)

    async def get_sentence(self, *, difficulties: list[str] | str | None = None) -> ContentItem:
        return await self.get_random(ContentType.SENTENCE, difficulties=difficulties)

    async def _sync_content_type(self, content_type: ContentType):
        batch = []
        active_hashes: set[str] = set()
        iterator = getattr(self.fallback_provider, "iter_content", None)
        if iterator is None:
            seeds = await self.fallback_provider.list_content(content_type)
            await self.contents.add_approved_seeds(seeds)
            active_hashes = {
                content_hash
                for seed in seeds
                if isinstance(content_hash := getattr(seed, "content_hash", None), str)
            }
            if content_type == ContentType.WORD:
                await self._reject_stale_packaged_words(active_hashes)
            yield len(seeds)
            return
        for seed in iterator(content_type):
            active_hashes.add(seed.content_hash)
            batch.append(seed)
            if len(batch) >= self.contents.SEED_BATCH_SIZE:
                await self.contents.add_approved_seeds(batch)
                yield len(batch)
                batch = []
        if batch:
            await self.contents.add_approved_seeds(batch)
            yield len(batch)
        if content_type == ContentType.WORD:
            await self._reject_stale_packaged_words(active_hashes)

    async def _reject_stale_packaged_words(self, active_hashes: set[str]) -> None:
        reject_stale = getattr(self.contents, "reject_packaged_content_not_in_hashes", None)
        if reject_stale is None:
            return
        await reject_stale(
            content_type=ContentType.WORD,
            source_prefix="ECDICT",
            content_hashes=active_hashes,
        )


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


def packaged_content_fingerprint() -> str:
    digest = hashlib.sha256()
    for filename in ("words.jsonl", "sentences.jsonl"):
        resource = files("app.data").joinpath(filename)
        digest.update(filename.encode())
        with resource.open("rb") as content_file:
            for chunk in iter(lambda: content_file.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()
