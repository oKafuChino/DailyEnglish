from collections import Counter
from importlib.resources import files

from app.domain.enums import ContentType
from app.providers.fallback import FallbackContentProvider, load_word_library


def test_packaged_word_library_has_expected_distribution() -> None:
    resource = files("app.data").joinpath("words.jsonl")
    assert resource.is_file()

    words = load_word_library()
    counts = Counter(word.difficulty for word in words)

    assert len(words) == 50_000
    assert counts == {"B1": 15000, "B2": 20000, "C1": 15000}
    assert len({word.text_en.casefold() for word in words}) == 50_000
    assert all(word.content_type == ContentType.WORD for word in words)
    assert all(word.translation_zh.strip() for word in words)
    assert all(word.example_en and word.example_en.strip() for word in words)
    assert all(word.source.startswith("ECDICT") for word in words)
    assert all("source_frequency_rank" in word.extra_data for word in words)


async def test_fallback_provider_uses_packaged_words() -> None:
    words = await FallbackContentProvider().list_content(ContentType.WORD)

    assert len(words) == 50_000
    assert {word.difficulty for word in words} == {"B1", "B2", "C1"}
