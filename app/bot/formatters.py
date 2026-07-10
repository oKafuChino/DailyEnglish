from html import escape

from app.db.models import ContentItem


def format_word(content: ContentItem) -> str:
    lines = [f"📖 <b>{escape(content.text_en)}</b>"]
    details = " · ".join(
        escape(value)
        for value in (content.phonetic, content.part_of_speech, content.difficulty)
        if value
    )
    if details:
        lines.append(details)
    lines.extend(("", f"🇨🇳 {escape(content.translation_zh)}"))
    if content.example_en:
        lines.extend(("", f"💬 <i>{escape(content.example_en)}</i>"))
    if content.example_zh:
        lines.append(escape(content.example_zh))
    return "\n".join(lines)


def format_sentence(content: ContentItem) -> str:
    lines = [f"💬 <b>{escape(content.text_en)}</b>", "", f"🇨🇳 {escape(content.translation_zh)}"]
    if content.attribution:
        lines.extend(("", f"— {escape(content.attribution)}"))
    return "\n".join(lines)
