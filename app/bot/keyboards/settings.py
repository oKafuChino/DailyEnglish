from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class SettingsCallback(CallbackData, prefix="user_settings"):
    action: str
    value: str | None = None


DIFFICULTY_LABELS = {
    "mixed": "混合",
    "B1": "B1",
    "B2": "B2",
    "C1": "C1",
}


def difficulty_button_text(value: str, current: str) -> str:
    prefix = "✅ " if value == current else ""
    return f"{prefix}{DIFFICULTY_LABELS[value]}"


def settings_keyboard(
    *,
    push_enabled: bool,
    preferred_difficulty: str = "mixed",
) -> InlineKeyboardMarkup:
    toggle_label = "🔕 关闭推送" if push_enabled else "🔔 开启推送"
    current = preferred_difficulty if preferred_difficulty in DIFFICULTY_LABELS else "mixed"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_label,
                    callback_data=SettingsCallback(action="toggle").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🕐 修改时间",
                    callback_data=SettingsCallback(action="time").pack(),
                ),
                InlineKeyboardButton(
                    text="🌍 修改时区",
                    callback_data=SettingsCallback(action="timezone").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎚️ 难度：{DIFFICULTY_LABELS[current]}",
                    callback_data=SettingsCallback(action="difficulty", value="mixed").pack(),
                ),
                InlineKeyboardButton(
                    text=difficulty_button_text("B1", current),
                    callback_data=SettingsCallback(action="difficulty", value="B1").pack(),
                ),
                InlineKeyboardButton(
                    text=difficulty_button_text("B2", current),
                    callback_data=SettingsCallback(action="difficulty", value="B2").pack(),
                ),
                InlineKeyboardButton(
                    text=difficulty_button_text("C1", current),
                    callback_data=SettingsCallback(action="difficulty", value="C1").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✖️ 关闭面板",
                    callback_data=SettingsCallback(action="close").pack(),
                )
            ],
        ]
    )
