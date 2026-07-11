from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.filters.private_chat import PrivateChatFilter
from app.bot.states.registration import Registration
from app.config import get_settings
from app.db.repositories.users import UserRepository
from app.db.session import session_scope
from app.domain.enums import UserStatus
from app.exceptions import (
    AlreadyRegisteredError,
    InvalidInviteCodeError,
    InviteCodeExpiredError,
    InviteCodeRedeemedError,
    InviteCodeRevokedError,
    UserBlockedError,
)
from app.services.invite_service import InviteService
from app.services.user_service import UserService

router = Router(name="public")
router.message.filter(PrivateChatFilter())


def build_help_text(*, is_registered: bool, is_admin: bool) -> str:
    lines = [
        "📚 DailyEnglish Bot 指令帮助",
        "",
        "/start - 启动机器人",
        "/help - 查看指令帮助",
    ]
    if is_registered or is_admin:
        lines.extend(
            [
                "/word - 获取一个英语单词",
                "/sentence - 获取一句英语好句",
                "/daily - 获取今日单词和句子",
                "/saved [页码] - 查看收藏内容",
                "/setting - 设置推送时间、时区和开关",
                "/cancel - 取消正在进行的设置操作",
            ]
        )
    else:
        lines.extend(
            [
                "/register <邀请码> - 使用一次性邀请码注册",
                "",
                "完成注册后即可使用学习、收藏和推送设置功能。",
            ]
        )
    if is_admin:
        lines.extend(
            [
                "",
                "👑 管理员指令",
                "/invite [小时] - 生成一次性邀请码",
                "/invites - 查看最近 10 个邀请码",
                "/revoke <邀请码ID> - 撤销未使用的邀请码",
            ]
        )
    return "\n".join(lines)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    if message.from_user is None:
        return
    is_admin = message.from_user.id == get_settings().owner_telegram_id
    is_registered = is_admin
    if not is_admin:
        async with session_scope() as session:
            user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
        is_registered = user is not None and user.status == UserStatus.ACTIVE
    await message.answer(build_help_text(is_registered=is_registered, is_admin=is_admin))


async def _redeem_for_message(message: Message, code: str) -> str:
    if message.from_user is None:
        return "无法读取 Telegram 用户信息。"
    settings = get_settings()
    try:
        async with session_scope() as session:
            user = await UserService(session).ensure_user(
                telegram_user_id=message.from_user.id,
                chat_id=message.chat.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            await InviteService(
                session, pepper=settings.invite_code_pepper.get_secret_value()
            ).redeem(code=code, user=user)
    except InvalidInviteCodeError:
        return "邀请码无效，请检查后重试。"
    except InviteCodeExpiredError:
        return "邀请码已过期，请联系管理员获取新的邀请码。"
    except InviteCodeRevokedError:
        return "邀请码已被管理员撤销。"
    except AlreadyRegisteredError:
        return "你已经完成注册，无需重复使用邀请码。"
    except InviteCodeRedeemedError:
        return "邀请码已经被使用。"
    except UserBlockedError:
        return "你的账号已被停用，请联系管理员。"
    return "注册成功！现在可以使用 DailyEnglish Bot 了。"


@router.message(CommandStart(), flags={"rate_limit": "registration"})
async def start(message: Message, state: FSMContext, command: CommandObject) -> None:
    if message.from_user is None:
        return
    settings = get_settings()
    if message.from_user.id == settings.owner_telegram_id:
        await state.clear()
        await message.answer(
            "欢迎回来，管理员。\n\n"
            "/invite [小时] - 生成邀请码\n"
            "/invites - 查看最近邀请码\n"
            "/revoke <ID> - 撤销邀请码"
        )
        return

    async with session_scope() as session:
        user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if user is not None and user.status == UserStatus.ACTIVE:
        await state.clear()
        await message.answer("欢迎回来，你已经完成注册。发送 /help 查看可用指令。")
        return
    if command.args:
        response = await _redeem_for_message(message, command.args)
        if response.startswith("注册成功"):
            await state.clear()
        await message.answer(response)
        return

    await state.set_state(Registration.waiting_for_invite)
    await message.answer("欢迎使用 DailyEnglish Bot。请直接发送管理员提供的一次性邀请码。")


@router.message(Command("register"), flags={"rate_limit": "registration"})
async def register(message: Message, state: FSMContext, command: CommandObject) -> None:
    if not command.args:
        await state.set_state(Registration.waiting_for_invite)
        await message.answer("请发送邀请码，格式类似 ABCD-EFGH-JK23。")
        return
    response = await _redeem_for_message(message, command.args)
    if response.startswith("注册成功"):
        await state.clear()
    await message.answer(response)


@router.message(
    Registration.waiting_for_invite,
    F.text,
    flags={"rate_limit": "registration"},
)
async def receive_invite(message: Message, state: FSMContext) -> None:
    response = await _redeem_for_message(message, message.text or "")
    if response.startswith("注册成功"):
        await state.clear()
    await message.answer(response)


@router.message(Command("invite", "invites", "revoke"))
async def reject_admin_command(message: Message) -> None:
    await message.answer("该命令仅限管理员使用。")
