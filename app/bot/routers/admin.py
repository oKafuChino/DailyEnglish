import uuid
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.bot.filters.admin import AdminFilter
from app.bot.filters.private_chat import PrivateChatFilter
from app.config import get_settings
from app.db.repositories.invites import InviteRepository
from app.db.session import session_scope
from app.domain.time import UTC
from app.exceptions import InvalidInviteCodeError, InviteCodeRedeemedError
from app.services.invite_service import InviteService

router = Router(name="admin")
router.message.filter(PrivateChatFilter(), AdminFilter())


def _invite_status(
    redeemed_at: datetime | None,
    revoked_at: datetime | None,
    expires_at: datetime,
) -> str:
    if redeemed_at is not None:
        return "已使用"
    if revoked_at is not None:
        return "已撤销"
    if expires_at <= datetime.now(UTC):
        return "已过期"
    return "可使用"


@router.message(Command("invite"), flags={"rate_limit": "admin"})
async def create_invite(message: Message, command: CommandObject) -> None:
    try:
        valid_hours = int(command.args) if command.args else 168
        if not 1 <= valid_hours <= 720:
            raise ValueError
    except ValueError:
        await message.answer("用法：/invite [有效小时数]，范围为 1-720，默认 168 小时。")
        return

    assert message.from_user is not None
    settings = get_settings()
    async with session_scope() as session:
        result = await InviteService(
            session, pepper=settings.invite_code_pepper.get_secret_value()
        ).create_invite(
            admin_telegram_id=message.from_user.id,
            valid_for=timedelta(hours=valid_hours),
        )

    await message.answer(
        "一次性邀请码已生成：\n\n"
        f"{result.plain_code}\n\n"
        f"有效期：{valid_hours} 小时\n"
        f"ID：{result.invite.id}\n\n"
        "邀请码仅显示这一次，使用后立即失效。"
    )


@router.message(Command("invites"), flags={"rate_limit": "admin"})
async def list_invites(message: Message) -> None:
    async with session_scope() as session:
        invites = await InviteRepository(session).list_recent(limit=10)

    if not invites:
        await message.answer("还没有生成过邀请码。")
        return
    lines = ["最近 10 个邀请码："]
    for invite in invites:
        status = _invite_status(invite.redeemed_at, invite.revoked_at, invite.expires_at)
        lines.append(f"\n{invite.id}\n状态：{status}｜过期：{invite.expires_at:%Y-%m-%d %H:%M UTC}")
    await message.answer("\n".join(lines))


@router.message(Command("revoke"), flags={"rate_limit": "admin"})
async def revoke_invite(message: Message, command: CommandObject) -> None:
    try:
        invite_id = uuid.UUID(command.args or "")
    except ValueError:
        await message.answer("用法：/revoke <邀请码ID>，ID 可通过 /invites 查看。")
        return

    assert message.from_user is not None
    settings = get_settings()
    try:
        async with session_scope() as session:
            await InviteService(
                session, pepper=settings.invite_code_pepper.get_secret_value()
            ).revoke(invite_id=invite_id, admin_telegram_id=message.from_user.id)
    except InvalidInviteCodeError:
        await message.answer("未找到该邀请码。")
        return
    except InviteCodeRedeemedError:
        await message.answer("该邀请码已经被使用，不能撤销。")
        return
    await message.answer("邀请码已撤销。")
