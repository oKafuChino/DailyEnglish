from functools import lru_cache
from importlib.resources import files

from app.domain.enums import ContentType
from app.domain.schemas import ContentSeed

BUILTIN_CONTENT = (
    ContentSeed(
        content_type=ContentType.WORD,
        text_en="resilient",
        phonetic="/rɪˈzɪliənt/",
        part_of_speech="adjective",
        translation_zh="有韧性的；能迅速恢复的",
        example_en="She remained resilient in the face of every setback.",
        example_zh="面对每一次挫折，她都保持着坚韧。",
        difficulty="B2",
    ),
    ContentSeed(
        content_type=ContentType.WORD,
        text_en="serendipity",
        phonetic="/ˌserənˈdɪpəti/",
        part_of_speech="noun",
        translation_zh="意外发现美好事物的运气；机缘巧合",
        example_en="Meeting my closest friend was pure serendipity.",
        example_zh="遇见我最亲密的朋友纯属美好的巧合。",
        difficulty="C1",
    ),
    ContentSeed(
        content_type=ContentType.WORD,
        text_en="endeavor",
        phonetic="/ɪnˈdevər/",
        part_of_speech="noun / verb",
        translation_zh="努力；尽力尝试",
        example_en="Every meaningful endeavor begins with a small step.",
        example_zh="每一份有意义的努力都始于一小步。",
        difficulty="B2",
    ),
    ContentSeed(
        content_type=ContentType.WORD,
        text_en="curious",
        phonetic="/ˈkjʊriəs/",
        part_of_speech="adjective",
        translation_zh="好奇的；求知欲强的",
        example_en="Stay curious and keep asking thoughtful questions.",
        example_zh="保持好奇，并不断提出有思考的问题。",
        difficulty="B1",
    ),
    ContentSeed(
        content_type=ContentType.WORD,
        text_en="thrive",
        phonetic="/θraɪv/",
        part_of_speech="verb",
        translation_zh="茁壮成长；蓬勃发展",
        example_en="People thrive when they feel trusted and supported.",
        example_zh="当人们感受到信任与支持时，便会蓬勃成长。",
        difficulty="B2",
    ),
    ContentSeed(
        content_type=ContentType.SENTENCE,
        text_en="The secret of getting ahead is getting started.",
        translation_zh="取得进展的秘诀，就是开始行动。",
        attribution="Mark Twain",
    ),
    ContentSeed(
        content_type=ContentType.SENTENCE,
        text_en="Great things are done by a series of small things brought together.",
        translation_zh="伟大的成就，是由一系列微小努力汇聚而成的。",
        attribution="Vincent van Gogh",
    ),
    ContentSeed(
        content_type=ContentType.SENTENCE,
        text_en="It always seems impossible until it is done.",
        translation_zh="在事情完成之前，它看起来总是不可能。",
        attribution="Nelson Mandela",
    ),
    ContentSeed(
        content_type=ContentType.SENTENCE,
        text_en="Do what you can, with what you have, where you are.",
        translation_zh="在你所在之处，用你拥有的条件，做你能做的事。",
        attribution="Theodore Roosevelt",
    ),
    ContentSeed(
        content_type=ContentType.SENTENCE,
        text_en="A person who never made a mistake never tried anything new.",
        translation_zh="从不犯错的人，也从未尝试过新事物。",
        attribution="Albert Einstein",
    ),
)


@lru_cache(maxsize=1)
def load_word_library() -> tuple[ContentSeed, ...]:
    resource = files("app.data").joinpath("words.jsonl")
    with resource.open("r", encoding="utf-8") as word_file:
        return tuple(ContentSeed.model_validate_json(line) for line in word_file if line.strip())


@lru_cache(maxsize=1)
def load_sentence_library() -> tuple[ContentSeed, ...]:
    resource = files("app.data").joinpath("sentences.jsonl")
    with resource.open("r", encoding="utf-8") as sentence_file:
        return tuple(
            ContentSeed.model_validate_json(line) for line in sentence_file if line.strip()
        )


class FallbackContentProvider:
    async def list_content(self, content_type: ContentType) -> list[ContentSeed]:
        if content_type == ContentType.WORD:
            return list(load_word_library())
        if content_type == ContentType.SENTENCE:
            return list(load_sentence_library())
        return [item for item in BUILTIN_CONTENT if item.content_type == content_type]
