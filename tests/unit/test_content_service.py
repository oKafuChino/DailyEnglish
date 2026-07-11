from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql

from app.db.repositories.contents import ContentRepository
from app.domain.enums import ContentType
from app.providers.fallback import BUILTIN_CONTENT
from app.services.content_service import ContentService, ContentUnavailableError


def make_service(*, first=None, second=None, seeds=None) -> ContentService:
    service = ContentService(SimpleNamespace())
    service.contents = SimpleNamespace(
        get_random_approved=AsyncMock(side_effect=[first, second]),
        add_approved_seeds=AsyncMock(),
    )
    service.fallback_provider = SimpleNamespace(list_content=AsyncMock(return_value=seeds or []))
    return service


@pytest.mark.asyncio
async def test_get_random_returns_existing_approved_content() -> None:
    content = SimpleNamespace(text_en="resilient")
    service = make_service(first=content)

    result = await service.get_word()

    assert result is content
    service.fallback_provider.list_content.assert_not_awaited()
    service.contents.add_approved_seeds.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_random_uses_requested_difficulty_and_falls_back() -> None:
    content = SimpleNamespace(text_en="resilient")
    service = ContentService(SimpleNamespace())
    service.contents = SimpleNamespace(
        get_random_approved=AsyncMock(side_effect=[None, content]),
        add_approved_seeds=AsyncMock(),
    )
    service.fallback_provider = SimpleNamespace(list_content=AsyncMock())

    result = await service.get_random(ContentType.WORD, difficulties=["B2", "C1"])

    assert result is content
    assert service.contents.get_random_approved.await_args_list == [
        ((ContentType.WORD,), {"difficulties": ["B2", "C1"]}),
        ((ContentType.WORD,),),
    ]
    service.fallback_provider.list_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_random_seeds_database_when_content_is_empty() -> None:
    content = SimpleNamespace(text_en="resilient")
    seeds = [SimpleNamespace(text_en="resilient")]
    service = make_service(first=None, second=content, seeds=seeds)

    result = await service.get_random(ContentType.WORD)

    assert result is content
    service.fallback_provider.list_content.assert_awaited_once_with(ContentType.WORD)
    service.contents.add_approved_seeds.assert_awaited_once_with(seeds)


@pytest.mark.asyncio
async def test_get_random_raises_when_no_content_is_available() -> None:
    service = make_service(first=None, second=None)

    with pytest.raises(ContentUnavailableError):
        await service.get_sentence()


@pytest.mark.asyncio
async def test_sync_packaged_content_seeds_words_and_sentences(monkeypatch) -> None:
    word_seeds = [
        SimpleNamespace(text_en="word-1", content_hash="word-hash-1"),
        SimpleNamespace(text_en="word-2", content_hash="word-hash-2"),
    ]
    sentence_seeds = [SimpleNamespace(text_en="sentence-1", content_hash="sentence-hash-1")]
    service = ContentService(SimpleNamespace())
    service.contents = SimpleNamespace(
        add_approved_seeds=AsyncMock(),
        reject_packaged_content_not_in_hashes=AsyncMock(),
    )
    service.fallback_provider = SimpleNamespace(
        list_content=AsyncMock(side_effect=[word_seeds, sentence_seeds])
    )
    service._try_packaged_content_lock = AsyncMock(return_value=True)
    state = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
    monkeypatch.setattr("app.services.content_service.AppStateRepository", lambda _: state)

    total = await service.sync_packaged_content()

    assert total == 3
    assert service.fallback_provider.list_content.await_args_list == [
        ((ContentType.WORD,),),
        ((ContentType.SENTENCE,),),
    ]
    assert service.contents.add_approved_seeds.await_args_list == [
        ((word_seeds,),),
        ((sentence_seeds,),),
    ]
    service.contents.reject_packaged_content_not_in_hashes.assert_awaited_once_with(
        content_type=ContentType.WORD,
        source_prefix="ECDICT",
        content_hashes={"word-hash-1", "word-hash-2"},
    )


@pytest.mark.asyncio
async def test_sync_packaged_content_skips_when_fingerprint_matches(monkeypatch) -> None:
    session = SimpleNamespace()
    service = ContentService(session)
    service.contents = SimpleNamespace(session=session, add_approved_seeds=AsyncMock())
    service.fallback_provider = SimpleNamespace(list_content=AsyncMock())

    state = SimpleNamespace(get=AsyncMock(return_value="fingerprint"), set=AsyncMock())
    monkeypatch.setattr(
        "app.services.content_service.packaged_content_fingerprint",
        lambda: "fingerprint",
    )
    monkeypatch.setattr("app.services.content_service.AppStateRepository", lambda _: state)

    total = await service.sync_packaged_content()

    assert total == 0
    service.fallback_provider.list_content.assert_not_awaited()
    service.contents.add_approved_seeds.assert_not_awaited()
    state.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_packaged_content_skips_when_lock_is_busy(monkeypatch) -> None:
    session = SimpleNamespace()
    service = ContentService(session)
    service.contents = SimpleNamespace(session=session, add_approved_seeds=AsyncMock())
    service.fallback_provider = SimpleNamespace(list_content=AsyncMock())
    service._try_packaged_content_lock = AsyncMock(return_value=False)

    state = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
    monkeypatch.setattr("app.services.content_service.packaged_content_fingerprint", lambda: "new")
    monkeypatch.setattr("app.services.content_service.AppStateRepository", lambda _: state)

    total = await service.sync_packaged_content()

    assert total == 0
    service.fallback_provider.list_content.assert_not_awaited()
    state.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_insert_uses_mapped_metadata_attribute() -> None:
    session = SimpleNamespace(execute=AsyncMock(), flush=AsyncMock())
    repository = ContentRepository(session)

    await repository.add_approved_seeds([BUILTIN_CONTENT[0]])

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "metadata" in sql
    assert "ON CONFLICT" in sql
    assert "example_en" in sql
    session.flush.assert_awaited_once()
