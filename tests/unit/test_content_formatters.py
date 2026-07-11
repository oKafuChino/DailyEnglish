from types import SimpleNamespace

from app.bot.formatters import format_sentence, format_word


def test_format_word_includes_learning_details_and_escapes_html() -> None:
    content = SimpleNamespace(
        text_en="thrive <grow>",
        phonetic="/θraɪv/",
        part_of_speech="verb",
        difficulty="B2",
        translation_zh="茁壮成长",
        example_en="People thrive with trust & support.",
        example_zh="信任和支持帮助人成长。",
    )

    result = format_word(content)

    assert "thrive &lt;grow&gt;" in result
    assert "/θraɪv/ · verb · B2" in result
    assert "trust &amp; support" in result


def test_format_sentence_includes_translation_and_attribution() -> None:
    content = SimpleNamespace(
        text_en="It always seems impossible until it is done.",
        translation_zh="在事情完成之前，它看起来总是不可能。",
        attribution="Nelson Mandela",
    )

    result = format_sentence(content)

    assert "在事情完成之前" in result
    assert "— Nelson Mandela" in result
