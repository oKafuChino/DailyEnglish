import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
USER_AGENT = "DailyEnglishBot/0.1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")


def extract_example(payload: Any) -> str | None:
    if not isinstance(payload, list) or not payload:
        return None
    for entry in payload:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                example = definition.get("example")
                if isinstance(example, str):
                    normalized = " ".join(example.strip().strip("\"'").split())
                    if 10 <= len(normalized) <= 240:
                        return normalized
    return None


def fetch_example(word: str, *, retries: int, timeout: float) -> str | None:
    url = API_URL.format(word=quote(word))
    for attempt in range(retries + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return extract_example(payload)
        except HTTPError as exc:
            if exc.code == 404:
                return None
        except (TimeoutError, URLError, json.JSONDecodeError):
            pass
        if attempt < retries:
            time.sleep(1.5 * (attempt + 1))
    return None


def fill_examples(
    rows: list[dict[str, Any]],
    *,
    workers: int,
    retries: int,
    timeout: float,
) -> int:
    pending = [
        (index, row["text_en"])
        for index, row in enumerate(rows)
        if row.get("content_type") == "word" and not row.get("example_en")
    ]
    if not pending:
        return 0

    filled = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_example, word, retries=retries, timeout=timeout): index
            for index, word in pending
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            index = futures[future]
            example = future.result()
            if example:
                rows[index]["example_en"] = example
                filled += 1
            if completed % 100 == 0:
                print(f"Processed {completed}/{len(pending)}; filled {filled}")
    return filled


def offline_example(word: str, part_of_speech: str | None, difficulty: str | None) -> str:
    pos = (part_of_speech or "").lower()
    level = difficulty or "B1"
    if "adverb" in pos:
        return f"She explained the idea {word} so everyone could follow the discussion."
    if "adjective" in pos:
        return f"The situation felt {word} after the team reviewed all the details."
    if "verb" in pos:
        return f"They tried to {word} before the problem became more difficult."
    if "preposition" in pos:
        return f"The note was placed {word} the old book on the desk."
    if "conjunction" in pos:
        return f"We waited for a better answer, {word} the first plan was not enough."
    if "noun" in pos:
        return f"We discussed {word} during the lesson and wrote down a useful example."
    return f"The teacher used {word} in a {level} sentence to make the meaning clear."


def fill_offline_examples(rows: list[dict[str, Any]]) -> int:
    filled = 0
    for row in rows:
        if row.get("content_type") != "word" or row.get("example_en"):
            continue
        row["example_en"] = offline_example(
            str(row["text_en"]),
            row.get("part_of_speech"),
            row.get("difficulty"),
        )
        extra_data = row.setdefault("extra_data", {})
        if isinstance(extra_data, dict):
            extra_data["example_source"] = "DailyEnglish offline template"
        filled += 1
    return filled


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill missing word examples")
    parser.add_argument("--input", type=Path, default=Path("app/data/words.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("app/data/words.jsonl"))
    parser.add_argument(
        "--mode",
        choices=("offline", "api"),
        default="offline",
        help="offline is deterministic and does not require network access",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    if args.mode == "api":
        filled = fill_examples(
            rows,
            workers=args.workers,
            retries=args.retries,
            timeout=args.timeout,
        )
    else:
        filled = fill_offline_examples(rows)
    write_jsonl(args.output, rows)
    total_with_examples = sum(1 for row in rows if row.get("example_en"))
    print(
        f"Filled {filled} new examples; {total_with_examples}/{len(rows)} words now have example_en"
    )


if __name__ == "__main__":
    main()
