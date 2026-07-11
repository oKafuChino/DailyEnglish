import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

TARGET_COUNTS = {"B1": 15000, "B2": 20000, "C1": 15000}
WORD_PATTERN = re.compile(r"[a-z]+(?:-[a-z]+)?")
CHINESE_PATTERN = re.compile(r"[\u3400-\u9fff]")
LEMMA_PATTERN = re.compile(r"(?:^|/)0:([^/]+)")
SPECIAL_LABEL_PATTERN = re.compile(r"\[[^]]+\]")
ABBREVIATION_PATTERN = re.compile(r"(?:^|[;；,，\s])abbr\.", re.IGNORECASE)
PROPER_NOUN_MARKER_PATTERN = re.compile(r"人名|地名|男子名|女子名|姓氏")
REPEATED_LETTER_PATTERN = re.compile(r"([a-z])\1{2,}")

# Exam-tagged source data can still contain entries unsuitable for a general audience.
BLOCKED_WORDS = {
    "bastard",
    "bitch",
    "abc",
    "cunt",
    "fuck",
    "motherfucker",
    "nigger",
    "pornography",
    "rape",
    "rapist",
    "slut",
    "whore",
    "zzz",
}

POS_LABELS = (
    (re.compile(r"\b(?:vt|vi|v)\."), "verb"),
    (re.compile(r"\bn\."), "noun"),
    (re.compile(r"\b(?:a|adj)\."), "adjective"),
    (re.compile(r"\b(?:ad|adv)\."), "adverb"),
    (re.compile(r"\bprep\."), "preposition"),
    (re.compile(r"\bconj\."), "conjunction"),
    (re.compile(r"\bpron\."), "pronoun"),
    (re.compile(r"\bnum\."), "numeral"),
    (re.compile(r"\bint\."), "interjection"),
)


def classify(tags: set[str], best_rank: int) -> str | None:
    # ECDICT exam tags overlap heavily, so frequency bands keep common words out of
    # advanced levels. These are project-specific approximations, not CEFR labels.
    if {"cet4", "gk", "ky"} & tags and not {"toefl", "gre"} & tags and 200 <= best_rank <= 20_000:
        return "B1"
    if (
        {"cet6", "ielts", "toefl"} & tags
        and "cet4" not in tags
        and "gre" not in tags
        and 800 <= best_rank <= 50_000
    ):
        return "B2"
    if {"toefl", "gre"} & tags and "cet4" not in tags and 2_500 <= best_rank <= 80_000:
        return "C1"
    return None


def difficulty_for_rank(index: int) -> str:
    if index < TARGET_COUNTS["B1"]:
        return "B1"
    if index < TARGET_COUNTS["B1"] + TARGET_COUNTS["B2"]:
        return "B2"
    return "C1"


def parse_rank(value: str) -> int:
    try:
        rank = int(value)
    except (TypeError, ValueError):
        return 1_000_000
    return rank if rank > 0 else 1_000_000


def clean_translation(value: str) -> str | None:
    segments = re.split(r"\\[rn]|[\r\n]+", value)
    cleaned: list[str] = []
    for segment in segments:
        segment = SPECIAL_LABEL_PATTERN.sub("", segment).strip(" ,;；")
        if segment and CHINESE_PATTERN.search(segment):
            cleaned.append(segment)
        if len(cleaned) == 2:
            break
    if not cleaned:
        return None
    result = "；".join(cleaned)
    return result[:500]


def infer_part_of_speech(value: str) -> str | None:
    labels = [label for pattern, label in POS_LABELS if pattern.search(value.lower())]
    return " / ".join(dict.fromkeys(labels)) or None


def normalize_phonetic(value: str) -> str | None:
    value = value.strip().strip("/")
    if not value or len(value) > 120:
        return None
    return f"/{value}/"


def source_score(row: dict[str, str], difficulty: str) -> tuple[int, int, int, str]:
    best_rank = min(parse_rank(row.get("bnc", "")), parse_rank(row.get("frq", "")))
    target_rank = {"B1": 2_500, "B2": 7_000, "C1": 12_000}[difficulty]
    oxford_penalty = 0 if row.get("oxford") == "1" else 1
    collins = -int(row["collins"]) if row.get("collins", "").isdigit() else 0
    return abs(best_rank - target_rank), oxford_penalty, collins, row["word"]


def build_entry(row: dict[str, str], difficulty: str) -> dict[str, object] | None:
    word = row["word"].strip().lower()
    if not WORD_PATTERN.fullmatch(word) or not 3 <= len(word) <= 32 or word in BLOCKED_WORDS:
        return None
    if REPEATED_LETTER_PATTERN.fullmatch(word):
        return None
    translation_raw = row.get("translation", "")
    if ABBREVIATION_PATTERN.search(translation_raw):
        return None
    if PROPER_NOUN_MARKER_PATTERN.search(translation_raw):
        return None
    lemma_match = LEMMA_PATTERN.search(row.get("exchange", ""))
    if lemma_match and lemma_match.group(1).lower() != word:
        return None
    translation = clean_translation(translation_raw)
    if translation is None:
        return None
    tags = sorted(set(row.get("tag", "").split()))
    return {
        "content_type": "word",
        "text_en": word,
        "translation_zh": translation,
        "phonetic": normalize_phonetic(row.get("phonetic", "")),
        "part_of_speech": infer_part_of_speech(row.get("translation", "")),
        "example_en": None,
        "example_zh": None,
        "attribution": "ECDICT",
        "source": "ECDICT (MIT); approximate project level mapping",
        "difficulty": difficulty,
        "extra_data": {
            "source_tags": tags,
            "source_bnc_rank": parse_rank(row.get("bnc", "")),
            "source_frequency_rank": parse_rank(row.get("frq", "")),
        },
    }


def generate(source: Path, output: Path) -> Counter[str]:
    csv.field_size_limit(10_000_000)
    candidates: list[tuple[tuple[int, int, int, int, str], dict[str, str]]] = []
    with source.open(encoding="utf-8", newline="") as source_file:
        for row in csv.DictReader(source_file):
            best_rank = min(parse_rank(row.get("bnc", "")), parse_rank(row.get("frq", "")))
            if build_entry(row, "B1") is None:
                continue
            oxford_penalty = 0 if row.get("oxford") == "1" else 1
            collins = -int(row["collins"]) if row.get("collins", "").isdigit() else 0
            candidates.append(
                (
                    (
                        best_rank,
                        oxford_penalty,
                        collins,
                        -len(set(row.get("tag", "").split())),
                        row["word"],
                    ),
                    row,
                )
            )

    selected: list[dict[str, object]] = []
    target_total = sum(TARGET_COUNTS.values())
    ordered = sorted(candidates, key=lambda item: item[0])
    if len(ordered) < target_total:
        raise RuntimeError(f"Not enough candidates: required {target_total}, found {len(ordered)}")
    for index, (_, row) in enumerate(ordered[:target_total]):
        difficulty = difficulty_for_rank(index)
        entry = build_entry(row, difficulty)
        if entry is None:
            raise RuntimeError(f"Candidate unexpectedly rejected: {row['word']}")
        selected.append(entry)

    words = [str(entry["text_en"]) for entry in selected]
    if len(words) != len(set(words)):
        raise RuntimeError("Generated word library contains duplicates")
    selected.sort(key=lambda item: (str(item["difficulty"]), str(item["text_en"])))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as output_file:
        for entry in selected:
            output_file.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")))
            output_file.write("\n")
    return Counter(str(entry["difficulty"]) for entry in selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the DailyEnglish ECDICT word library")
    parser.add_argument("source", type=Path, help="Path to ECDICT ecdict.csv")
    parser.add_argument("output", type=Path, help="Output JSONL path")
    args = parser.parse_args()
    counts = generate(args.source, args.output)
    print(f"Generated {sum(counts.values())} words: {dict(sorted(counts.items()))}")


if __name__ == "__main__":
    main()
