from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.keyboards.review import ReviewChoiceCallback, review_choice_keyboard
from app.domain.time import UTC
from app.services.review_service import (
    REVIEW_BATCH_SIZE,
    REVIEW_COOLDOWN,
    ReviewService,
    compact_translation,
    is_spelling_correct,
    review_state_item_passed,
)


def make_content(*, content_id: str, word: str, translation: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=content_id,
        text_en=word,
        translation_zh=translation,
    )


def make_favorite(
    *,
    favorite_id: int,
    content_id: str,
    word: str,
    translation: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=favorite_id,
        content_id=content_id,
        content=make_content(
            content_id=content_id,
            word=word,
            translation=translation,
        ),
    )


def make_service() -> ReviewService:
    service = ReviewService(SimpleNamespace())
    service.favorites = SimpleNamespace(
        list_review_candidates_for_user=AsyncMock(),
        list_review_distractors=AsyncMock(),
        reset_word_review_cooldowns_for_user=AsyncMock(),
        mark_review_result=AsyncMock(),
    )
    return service


def test_compact_translation_keeps_readable_chinese_option() -> None:
    assert compact_translation("n. 喜欢的事物, 幸运儿；a. 特别受喜爱的") == "喜欢的事物"
    assert compact_translation("  重要的、有意义的解释  ") == "重要的"


def test_spelling_answer_is_case_insensitive_and_space_normalized() -> None:
    assert is_spelling_correct("  Ice  Cream ", "ice cream")
    assert is_spelling_correct("ABLE", "able")
    assert not is_spelling_correct("abIe", "able")


def test_review_choice_keyboard_carries_session_and_question_identity() -> None:
    keyboard = review_choice_keyboard(
        ["能干的", "勇敢的"],
        session_id="abc123",
        question_index=4,
    )

    callback_data = keyboard.inline_keyboard[1][0].callback_data

    assert callback_data == ReviewChoiceCallback(session_id="abc123", question=4, answer=1).pack()


def test_review_state_item_requires_both_checks_to_pass() -> None:
    assert review_state_item_passed({"choice_passed": True, "spelling_passed": True})
    assert not review_state_item_passed({"choice_passed": True, "spelling_passed": False})
    assert not review_state_item_passed({"choice_passed": False, "spelling_passed": True})


@pytest.mark.asyncio
async def test_build_session_uses_candidates_and_generates_four_options() -> None:
    service = make_service()
    candidates = [
        make_favorite(
            favorite_id=1,
            content_id="word-1",
            word="able",
            translation="a. 能干的, 能够的",
        ),
        make_favorite(
            favorite_id=2,
            content_id="word-2",
            word="brave",
            translation="a. 勇敢的",
        ),
    ]
    service.favorites.list_review_candidates_for_user.return_value = candidates
    service.favorites.list_review_distractors.return_value = [
        make_content(content_id="word-3", word="calm", translation="a. 冷静的"),
        make_content(content_id="word-4", word="direct", translation="a. 直接的"),
        make_content(content_id="word-5", word="eager", translation="a. 渴望的"),
    ]

    questions = await service.build_session(user_id=7, now=datetime(2026, 7, 11, tzinfo=UTC))

    assert len(questions) == 2
    assert questions[0].word in {"able", "brave"}
    assert len(questions[0].options) == 4
    assert questions[0].options[questions[0].correct_option]
    service.favorites.list_review_distractors.assert_awaited_once()
    service.favorites.reset_word_review_cooldowns_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_session_resets_cooldown_when_review_pool_is_empty() -> None:
    service = make_service()
    candidate = make_favorite(
        favorite_id=1,
        content_id="word-1",
        word="able",
        translation="a. 能干的",
    )
    service.favorites.list_review_candidates_for_user.side_effect = [[], [candidate]]
    service.favorites.list_review_distractors.return_value = [
        make_content(content_id="word-2", word="brave", translation="a. 勇敢的"),
        make_content(content_id="word-3", word="calm", translation="a. 冷静的"),
        make_content(content_id="word-4", word="direct", translation="a. 直接的"),
    ]
    now = datetime(2026, 7, 11, tzinfo=UTC)

    questions = await service.build_session(user_id=7, now=now)

    assert len(questions) == 1
    service.favorites.reset_word_review_cooldowns_for_user.assert_awaited_once_with(
        user_id=7,
        now=now,
    )


@pytest.mark.asyncio
async def test_build_session_limits_to_ten_words_after_shuffle() -> None:
    service = make_service()
    service.favorites.list_review_candidates_for_user.return_value = [
        make_favorite(
            favorite_id=index,
            content_id=f"word-{index}",
            word=f"word{index}",
            translation=f"n. 释义{index}",
        )
        for index in range(20)
    ]
    service.favorites.list_review_distractors.return_value = [
        make_content(content_id="d1", word="d1", translation="n. 选项一"),
        make_content(content_id="d2", word="d2", translation="n. 选项二"),
        make_content(content_id="d3", word="d3", translation="n. 选项三"),
    ]

    questions = await service.build_session(user_id=7)

    assert len(questions) == REVIEW_BATCH_SIZE


@pytest.mark.asyncio
async def test_record_result_sets_three_day_cooldown_only_when_passed() -> None:
    service = make_service()
    service.favorites.mark_review_result.return_value = True
    now = datetime(2026, 7, 11, 8, 0, tzinfo=UTC)

    assert await service.record_result(user_id=7, favorite_id=1, passed=True, now=now)
    service.favorites.mark_review_result.assert_awaited_with(
        favorite_id=1,
        user_id=7,
        passed=True,
        reviewed_until=now + REVIEW_COOLDOWN,
        now=now,
    )

    assert await service.record_result(
        user_id=7,
        favorite_id=1,
        passed=False,
        now=now + timedelta(minutes=1),
    )
    service.favorites.mark_review_result.assert_awaited_with(
        favorite_id=1,
        user_id=7,
        passed=False,
        reviewed_until=None,
        now=now + timedelta(minutes=1),
    )
