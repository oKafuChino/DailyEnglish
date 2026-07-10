import uuid

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class FavoriteCallback(CallbackData, prefix="favorite"):
    action: str
    content_id: uuid.UUID


def favorite_keyboard(content_id: uuid.UUID, *, saved: bool = False) -> InlineKeyboardMarkup:
    action = "remove" if saved else "add"
    label = "🗑 取消收藏" if saved else "⭐ 收藏"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=FavoriteCallback(
                        action=action,
                        content_id=content_id,
                    ).pack(),
                )
            ]
        ]
    )


def daily_favorite_keyboard(
    word_id: uuid.UUID,
    sentence_id: uuid.UUID,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ 收藏单词",
                    callback_data=FavoriteCallback(action="add", content_id=word_id).pack(),
                ),
                InlineKeyboardButton(
                    text="⭐ 收藏句子",
                    callback_data=FavoriteCallback(action="add", content_id=sentence_id).pack(),
                ),
            ]
        ]
    )
