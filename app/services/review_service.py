import random
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ContentItem, Favorite
from app.db.repositories.favorites import FavoriteRepository
from app.domain.time import UTC

REVIEW_BATCH_SIZE = 10
REVIEW_OPTION_COUNT = 4
REVIEW_COOLDOWN = timedelta(days=3)

_WHITESPACE_PATTERN = re.compile(r"\s+")
_TRANSLATION_SPLIT_PATTERN = re.compile(r"[;；，,。、.]")
_PART_OF_SPEECH_PREFIX = re.compile(
    r"^(?:a|adj|ad|adv|art|aux|conj|int|interj|n|num|prep|pron|v|vi|vt)\.\s*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReviewQuestion:
    favorite_id: int
    word: str
    translation: str
    options: list[str]
    correct_option: int

    def to_state(self) -> dict[str, Any]:
        return asdict(self) | {
            "choice_passed": None,
            "spelling_passed": None,
        }


def normalize_spelling_answer(value: str) -> str:
    return _WHITESPACE_PATTERN.sub(" ", value.strip().casefold())


def is_spelling_correct(answer: str, word: str) -> bool:
    return normalize_spelling_answer(answer) == normalize_spelling_answer(word)


def compact_translation(value: str, *, max_length: int = 36) -> str:
    normalized = _WHITESPACE_PATTERN.sub(" ", value.strip())
    normalized = _PART_OF_SPEECH_PREFIX.sub("", normalized).strip()
    first_part = _TRANSLATION_SPLIT_PATTERN.split(normalized, maxsplit=1)[0].strip()
    compact = first_part or normalized
    if len(compact) <= max_length:
        return compact
    return f"{compact[: max_length - 1]}…"


class ReviewService:
    def __init__(self, session: AsyncSession, *, rng: random.Random | None = None) -> None:
        self.favorites = FavoriteRepository(session)
        self.rng = rng or random.SystemRandom()

    async def build_session(
        self,
        *,
        user_id: int,
        now: datetime | None = None,
        limit: int = REVIEW_BATCH_SIZE,
    ) -> list[ReviewQuestion]:
        review_now = now or datetime.now(UTC)
        candidates = await self.favorites.list_review_candidates_for_user(
            user_id=user_id,
            limit=limit,
            now=review_now,
        )
        if not candidates:
            await self.favorites.reset_word_review_cooldowns_for_user(
                user_id=user_id,
                now=review_now,
            )
            candidates = await self.favorites.list_review_candidates_for_user(
                user_id=user_id,
                limit=limit,
                now=review_now,
            )

        self.rng.shuffle(candidates)
        candidates = candidates[:limit]
        shared_distractors: list[ContentItem] = []
        if candidates:
            shared_distractors = await self.favorites.list_review_distractors(
                exclude_content_id=candidates[0].content_id,
                limit=max(REVIEW_OPTION_COUNT * len(candidates) * 4, REVIEW_OPTION_COUNT),
            )
        questions: list[ReviewQuestion] = []
        for favorite in candidates:
            question = await self._build_question(
                favorite,
                candidates,
                shared_distractors,
            )
            if question is not None:
                questions.append(question)
        return questions

    async def record_result(
        self,
        *,
        user_id: int,
        favorite_id: int,
        passed: bool,
        now: datetime | None = None,
    ) -> bool:
        review_now = now or datetime.now(UTC)
        reviewed_until = review_now + REVIEW_COOLDOWN if passed else None
        return await self.favorites.mark_review_result(
            favorite_id=favorite_id,
            user_id=user_id,
            passed=passed,
            reviewed_until=reviewed_until,
            now=review_now,
        )

    async def _build_question(
        self,
        favorite: Favorite,
        session_favorites: list[Favorite],
        shared_distractors: list[ContentItem],
    ) -> ReviewQuestion | None:
        correct_option = compact_translation(favorite.content.translation_zh)
        options = [correct_option]
        seen_options = {correct_option}

        for other in session_favorites:
            if other.id == favorite.id:
                continue
            self._append_option(options, seen_options, other.content.translation_zh)
            if len(options) >= REVIEW_OPTION_COUNT:
                break

        if len(options) < REVIEW_OPTION_COUNT:
            for distractor in shared_distractors:
                if distractor.id == favorite.content_id:
                    continue
                self._append_option(options, seen_options, distractor.translation_zh)
                if len(options) >= REVIEW_OPTION_COUNT:
                    break

        if len(options) < REVIEW_OPTION_COUNT:
            fallback_distractors = await self.favorites.list_review_distractors(
                exclude_content_id=favorite.content_id,
                limit=(REVIEW_OPTION_COUNT - len(options)) * 4,
            )
            for distractor in fallback_distractors:
                self._append_option(options, seen_options, distractor.translation_zh)
                if len(options) >= REVIEW_OPTION_COUNT:
                    break

        if len(options) < REVIEW_OPTION_COUNT:
            return None

        self.rng.shuffle(options)
        return ReviewQuestion(
            favorite_id=favorite.id,
            word=favorite.content.text_en,
            translation=favorite.content.translation_zh,
            options=options,
            correct_option=options.index(correct_option),
        )

    @staticmethod
    def _append_option(
        options: list[str],
        seen_options: set[str],
        translation: str,
    ) -> None:
        option = compact_translation(translation)
        if option in seen_options:
            return
        options.append(option)
        seen_options.add(option)


def review_questions_to_state(questions: list[ReviewQuestion]) -> list[dict[str, Any]]:
    return [question.to_state() for question in questions]


def review_state_item_passed(item: dict[str, Any]) -> bool:
    return bool(item.get("choice_passed")) and bool(item.get("spelling_passed"))


def format_review_correct_answer(item: dict[str, Any]) -> str:
    return f"{item['word']} — {item['translation']}"


def content_to_choice_label(content: ContentItem) -> str:
    return compact_translation(content.translation_zh)
