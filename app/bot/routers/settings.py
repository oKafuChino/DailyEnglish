import re
from datetime import time
from html import escape
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.private_chat import PrivateChatFilter
from app.bot.keyboards.settings import SettingsCallback, settings_keyboard
from app.bot.middlewares.registration import RegistrationMiddleware
from app.bot.states.settings import UserSettings
from app.db.models import User
from app.db.session import session_scope
from app.services.user_service import UserService

router = Router(name="settings")
router.message.filter(PrivateChatFilter())
router.callback_query.filter(PrivateChatFilter())
router.message.middleware(RegistrationMiddleware())
router.callback_query.middleware(RegistrationMiddleware())

PUSH_TIME_PATTERN = re.compile(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")


def parse_push_time(value: str) -> time:
    normalized = value.strip()
    if PUSH_TIME_PATTERN.fullmatch(normalized) is None:
        raise ValueError("Push time must use HH:MM")
    return time.fromisoformat(normalized)


def format_settings(user: User) -> str:
    enabled = "已开启" if user.daily_push_enabled else "已关闭"
    lines = [
        "⚙️ <b>推送设置</b>",
        "",
        f"状态：{enabled}",
        f"时间：{user.daily_push_time:%H:%M}",
        f"时区：{escape(user.timezone)}",
    ]
    if user.next_push_at is not None and user.daily_push_enabled:
        local_next = user.next_push_at.astimezone(ZoneInfo(user.timezone))
        lines.append(f"下次推送：{local_next:%Y-%m-%d %H:%M}")
    return "\n".join(lines)


async def _send_settings(message: Message, user: User) -> None:
    await message.answer(
        format_settings(user),
        parse_mode="HTML",
        reply_markup=settings_keyboard(push_enabled=user.daily_push_enabled),
    )


@router.message(Command("setting", "settings"))
async def show_settings(message: Message, state: FSMContext, current_user: User) -> None:
    await state.clear()
    await _send_settings(message, current_user)


@router.callback_query(
    SettingsCallback.filter(),
    flags={"rate_limit": "callback"},
)
async def settings_action(
    callback: CallbackQuery,
    callback_data: SettingsCallback,
    state: FSMContext,
    current_user: User,
) -> None:
    if callback_data.action == "close":
        await state.clear()
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
        await callback.answer()
        return
    if callback_data.action == "time":
        await state.set_state(UserSettings.waiting_for_push_time)
        if callback.message:
            await callback.message.answer("请输入新的推送时间，例如 08:30。发送 /cancel 取消。")
        await callback.answer()
        return
    if callback_data.action == "timezone":
        await state.set_state(UserSettings.waiting_for_timezone)
        if callback.message:
            await callback.message.answer(
                "请输入 IANA 时区，例如 Asia/Shanghai 或 Europe/London。发送 /cancel 取消。"
            )
        await callback.answer()
        return
    if callback_data.action != "toggle":
        await callback.answer("未知设置操作", show_alert=True)
        return

    async with session_scope() as session:
        user = await UserService(session).toggle_daily_push(user_id=current_user.id)
    if callback.message:
        await callback.message.edit_text(
            format_settings(user),
            parse_mode="HTML",
            reply_markup=settings_keyboard(push_enabled=user.daily_push_enabled),
        )
    await callback.answer("推送已开启" if user.daily_push_enabled else "推送已关闭")


@router.message(Command("cancel"))
async def cancel_settings(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("当前没有待取消的设置操作。")
        return
    await state.clear()
    await message.answer("已取消设置。")


@router.message(UserSettings.waiting_for_push_time, F.text.regexp(r"^[^/]"))
async def receive_push_time(message: Message, state: FSMContext, current_user: User) -> None:
    try:
        push_time = parse_push_time(message.text or "")
    except ValueError:
        await message.answer("时间格式无效，请使用 24 小时制 HH:MM，例如 08:30。")
        return
    async with session_scope() as session:
        user = await UserService(session).set_push_time(
            user_id=current_user.id,
            push_time=push_time,
        )
    await state.clear()
    await _send_settings(message, user)


@router.message(UserSettings.waiting_for_timezone, F.text.regexp(r"^[^/]"))
async def receive_timezone(message: Message, state: FSMContext, current_user: User) -> None:
    timezone_name = (message.text or "").strip()
    try:
        async with session_scope() as session:
            user = await UserService(session).set_timezone(
                user_id=current_user.id,
                timezone_name=timezone_name,
            )
    except ValueError:
        await message.answer("时区无效，请输入 IANA 时区，例如 Asia/Shanghai。")
        return
    await state.clear()
    await _send_settings(message, user)
