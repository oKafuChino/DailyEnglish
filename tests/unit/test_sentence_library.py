from collections import Counter
from importlib.resources import files

from app.domain.enums import ContentType
from app.providers.fallback import FallbackContentProvider, load_sentence_library


def test_packaged_sentence_library_has_expected_distribution() -> None:
    resource = files("app.data").joinpath("sentences.jsonl")
    assert resource.is_file()

    sentences = load_sentence_library()
    counts = Counter(sentence.difficulty for sentence in sentences)

    assert len(sentences) == 300
    assert counts == {"B1": 100, "B2": 100, "C1": 100}
    assert len({sentence.text_en.casefold() for sentence in sentences}) == 300
    assert all(sentence.content_type == ContentType.SENTENCE for sentence in sentences)
    assert all(sentence.translation_zh.strip() for sentence in sentences)
    assert all(sentence.attribution == "DailyEnglish Original" for sentence in sentences)


async def test_fallback_provider_uses_packaged_sentences() -> None:
    sentences = await FallbackContentProvider().list_content(ContentType.SENTENCE)

    assert len(sentences) == 300
    assert {sentence.difficulty for sentence in sentences} == {"B1", "B2", "C1"}
