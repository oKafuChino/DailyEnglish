from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ReviewChoiceCallback(CallbackData, prefix="review_choice"):
    session_id: str
    question: int
    answer: int


def review_choice_keyboard(
    options: list[str],
    *,
    session_id: str,
    question_index: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{index + 1}. {option}",
                    callback_data=ReviewChoiceCallback(
                        session_id=session_id,
                        question=question_index,
                        answer=index,
                    ).pack(),
                )
            ]
            for index, option in enumerate(options)
        ]
    )
