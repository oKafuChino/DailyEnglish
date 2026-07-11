from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class SettingsCallback(CallbackData, prefix="user_settings"):
    action: str


def settings_keyboard(*, push_enabled: bool) -> InlineKeyboardMarkup:
    toggle_label = "🔕 关闭推送" if push_enabled else "🔔 开启推送"
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
                    text="✖️ 关闭面板",
                    callback_data=SettingsCallback(action="close").pack(),
                )
            ],
        ]
    )
