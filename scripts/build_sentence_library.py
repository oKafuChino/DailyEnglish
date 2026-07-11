import json
from collections import Counter
from pathlib import Path

OUTPUT = Path("app/data/sentences.jsonl")

LEVELS = {
    "B1": {
        "themes": (
            ("small choices", "微小的选择"),
            ("honest effort", "真诚的努力"),
            ("steady practice", "持续的练习"),
            ("quiet courage", "沉静的勇气"),
            ("patient learning", "耐心的学习"),
            ("a clear purpose", "清晰的目标"),
            ("a kind action", "善意的行动"),
            ("an open mind", "开放的心态"),
            ("daily reflection", "每日的反思"),
            ("shared trust", "彼此的信任"),
        ),
        "templates": (
            ("{cap} can change the way we grow.", "{zh}能够改变我们成长的方式。"),
            ("Make room for {en}, even on a busy day.", "即使生活忙碌，也要为{zh}留出空间。"),
            ("We move forward when we value {en}.", "当我们珍视{zh}时，就会不断前进。"),
            ("A better day often begins with {en}.", "更好的一天往往始于{zh}。"),
            (
                "Remember the value of {en} when the road feels long.",
                "当道路漫长时，请记得{zh}的价值。",
            ),
            ("There is real strength in {en}.", "{zh}之中蕴含着真正的力量。"),
            ("Let {en} guide your next step.", "让{zh}指引你的下一步。"),
            ("With {en}, hard days become easier to face.", "拥有{zh}，艰难的日子也更容易面对。"),
            (
                "Choose to make {en} part of your life.",
                "选择让{zh}成为生活的一部分。",
            ),
            ("The future becomes brighter through {en}.", "未来会因{zh}而变得更加明亮。"),
        ),
    },
    "B2": {
        "themes": (
            ("consistent discipline", "始终如一的自律"),
            ("thoughtful communication", "深思熟虑的沟通"),
            ("genuine curiosity", "真正的好奇心"),
            ("calm persistence", "从容的坚持"),
            ("meaningful progress", "有意义的进步"),
            ("mutual respect", "相互尊重"),
            ("practical wisdom", "务实的智慧"),
            ("creative patience", "富有创造力的耐心"),
            ("responsible freedom", "负责任的自由"),
            ("balanced ambition", "平衡有度的抱负"),
        ),
        "templates": (
            (
                "{cap} turns ordinary moments into opportunities to improve.",
                "{zh}能把平凡的时刻变成提升自我的机会。",
            ),
            ("Lasting confidence is often built through {en}.", "持久的自信往往通过{zh}建立起来。"),
            (
                "When circumstances change, {en} helps us adapt without losing direction.",
                "当环境变化时，{zh}帮助我们在适应中不失方向。",
            ),
            (
                "The quality of our decisions reflects how deeply we value {en}.",
                "我们决策的质量，反映了我们对{zh}的重视程度。",
            ),
            (
                "Real growth becomes possible when {en} replaces the fear of failure.",
                "当{zh}取代对失败的恐惧时，真正的成长才成为可能。",
            ),
            (
                "A demanding goal becomes manageable when supported by {en}.",
                "有了{zh}的支撑，再艰巨的目标也会变得可控。",
            ),
            (
                "Communities become stronger when they are shaped by {en}.",
                "由{zh}塑造的群体会变得更加牢固。",
            ),
            (
                "We discover better answers by approaching uncertainty with {en}.",
                "以{zh}面对不确定性，我们便能找到更好的答案。",
            ),
            (
                "Success feels more worthwhile when it grows from {en}.",
                "源于{zh}的成功，会让人感到更有价值。",
            ),
            (
                "Even a difficult conversation can become constructive through {en}.",
                "即使是艰难的对话，也能通过{zh}变得富有建设性。",
            ),
        ),
    },
    "C1": {
        "themes": (
            ("intellectual humility", "求知上的谦逊"),
            ("deliberate resilience", "有意识的韧性"),
            ("ethical imagination", "道德想象力"),
            ("nuanced understanding", "细致入微的理解"),
            ("constructive skepticism", "建设性的质疑精神"),
            ("collective responsibility", "共同责任"),
            ("principled flexibility", "坚守原则的灵活性"),
            ("sustained introspection", "持续的自我审视"),
            ("empathetic leadership", "富有同理心的领导力"),
            ("informed conviction", "建立在充分认知上的信念"),
        ),
        "templates": (
            (
                "{cap} enables us to revise our assumptions without abandoning our values.",
                "{zh}使我们能够修正假设，同时不放弃自身价值观。",
            ),
            (
                "In an age of easy certainty, {en} remains an indispensable form of strength.",
                "在一个轻易下定论的时代，{zh}仍是一种不可或缺的力量。",
            ),
            (
                "Complex problems rarely yield to confidence alone; they also demand {en}.",
                "复杂问题很少仅凭自信就能解决，它们还需要{zh}。",
            ),
            (
                "By cultivating {en}, we learn to distinguish firm principles from rigid habits.",
                "通过培养{zh}，我们学会区分坚定的原则与僵化的习惯。",
            ),
            (
                "{cap} gives difficult truths the space to become useful rather than divisive.",
                "{zh}让艰难的真相有机会发挥作用，而非制造分裂。",
            ),
            (
                "The most enduring institutions pair clear purpose with {en}.",
                "最具生命力的制度，会把清晰的目标与{zh}结合起来。",
            ),
            (
                "Without {en}, expertise can quietly harden into unquestioned authority.",
                "缺少{zh}，专业知识可能悄然固化为不容质疑的权威。",
            ),
            (
                "{cap} allows disagreement to sharpen judgment instead of weakening trust.",
                "{zh}能让分歧磨砺判断力，而不是削弱信任。",
            ),
            (
                "Progress becomes sustainable when ambition is tempered by {en}.",
                "当雄心受到{zh}的调和时，进步才能持续。",
            ),
            (
                "Our response to uncertainty reveals whether we have truly developed {en}.",
                "我们对不确定性的回应，反映出自己是否真正培养了{zh}。",
            ),
        ),
    },
}


def capitalize_phrase(value: str) -> str:
    return value[:1].upper() + value[1:]


def generate(output: Path = OUTPUT) -> Counter[str]:
    entries: list[dict[str, object]] = []
    for difficulty, level in LEVELS.items():
        for theme_index, (english, chinese) in enumerate(level["themes"], start=1):
            for template_index, (template_en, template_zh) in enumerate(
                level["templates"], start=1
            ):
                entries.append(
                    {
                        "content_type": "sentence",
                        "text_en": template_en.format(
                            en=english,
                            cap=capitalize_phrase(english),
                        ),
                        "translation_zh": template_zh.format(zh=chinese),
                        "attribution": "DailyEnglish Original",
                        "source": "project-original",
                        "difficulty": difficulty,
                        "extra_data": {
                            "theme": english,
                            "theme_index": theme_index,
                            "template_index": template_index,
                        },
                    }
                )

    texts = [str(entry["text_en"]).casefold() for entry in entries]
    if len(entries) != 300 or len(texts) != len(set(texts)):
        raise RuntimeError("Sentence library must contain exactly 300 unique entries")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as output_file:
        for entry in entries:
            output_file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
            output_file.write("\n")
    return Counter(str(entry["difficulty"]) for entry in entries)


if __name__ == "__main__":
    counts = generate()
    print(f"Generated {sum(counts.values())} sentences: {dict(sorted(counts.items()))}")
