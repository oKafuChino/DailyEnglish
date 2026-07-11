import asyncio
import uuid
from datetime import datetime, timedelta
from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message
from sqlalchemy import func, select

from app.bot.filters.admin import AdminFilter
from app.bot.filters.private_chat import PrivateChatFilter
from app.config import get_settings
from app.db.models import ContentItem, Delivery, Favorite, InviteCode, User
from app.db.repositories.invites import InviteRepository
from app.db.session import session_scope
from app.domain.enums import ContentType, DeliveryStatus, UserStatus
from app.domain.time import UTC
from app.exceptions import InvalidInviteCodeError, InviteCodeRedeemedError
from app.services.admin_update_service import AdminUpdateService, truncate_output
from app.services.invite_service import InviteService

router = Router(name="admin")
router.message.filter(PrivateChatFilter(), AdminFilter())
_update_lock = asyncio.Lock()


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


@router.message(Command("stats"), flags={"rate_limit": "admin"})
async def stats(message: Message) -> None:
    async with session_scope() as session:
        active_users = int(
            await session.scalar(
                select(func.count(User.id)).where(User.status == UserStatus.ACTIVE)
            )
            or 0
        )
        pending_users = int(
            await session.scalar(
                select(func.count(User.id)).where(User.status == UserStatus.PENDING)
            )
            or 0
        )
        push_enabled = int(
            await session.scalar(
                select(func.count(User.id)).where(
                    User.status == UserStatus.ACTIVE,
                    User.daily_push_enabled.is_(True),
                )
            )
            or 0
        )
        words = int(
            await session.scalar(
                select(func.count(ContentItem.id)).where(
                    ContentItem.content_type == ContentType.WORD
                )
            )
            or 0
        )
        sentences = int(
            await session.scalar(
                select(func.count(ContentItem.id)).where(
                    ContentItem.content_type == ContentType.SENTENCE
                )
            )
            or 0
        )
        favorites = int(await session.scalar(select(func.count(Favorite.id))) or 0)
        sent_deliveries = int(
            await session.scalar(
                select(func.count(Delivery.id)).where(Delivery.status == DeliveryStatus.SENT)
            )
            or 0
        )
        failed_deliveries = int(
            await session.scalar(
                select(func.count(Delivery.id)).where(Delivery.status == DeliveryStatus.FAILED)
            )
            or 0
        )
        available_invites = int(
            await session.scalar(
                select(func.count(InviteCode.id)).where(
                    InviteCode.redeemed_at.is_(None),
                    InviteCode.revoked_at.is_(None),
                    InviteCode.expires_at > datetime.now(UTC),
                )
            )
            or 0
        )

    await message.answer(
        "📊 DailyEnglish 统计\n\n"
        f"用户：活跃 {active_users}｜待注册 {pending_users}｜开启推送 {push_enabled}\n"
        f"内容：单词 {words}｜句子 {sentences}｜收藏 {favorites}\n"
        f"投递：成功 {sent_deliveries}｜失败待重试 {failed_deliveries}\n"
        f"邀请码：可使用 {available_invites}"
    )


@router.message(Command("update"), flags={"rate_limit": "admin"})
async def update_bot(message: Message) -> None:
    settings = get_settings()
    if not settings.admin_update_command.strip():
        await message.answer(
            "远程更新尚未启用。\n\n"
            "请先在 .env 中配置 ADMIN_UPDATE_COMMAND，例如：\n"
            "ADMIN_UPDATE_COMMAND=/opt/dailyenglish/remote-update.sh"
        )
        return
    if _update_lock.locked():
        await message.answer("已有一个更新任务正在执行，请稍后再试。")
        return

    await message.answer("已收到更新指令，开始执行远程更新……")
    async with _update_lock:
        try:
            result = await AdminUpdateService(
                command=settings.admin_update_command,
                timeout_seconds=settings.admin_update_timeout_seconds,
            ).run()
        except ValueError as exc:
            await message.answer(f"远程更新配置无效：{escape(str(exc))}")
            return

    output = escape(truncate_output(result.output) or "无输出")
    if result.timed_out:
        await message.answer(
            f"更新命令超时，已尝试终止。\n退出码：{result.return_code}\n\n<pre>{output}</pre>",
            parse_mode="HTML",
        )
        return
    if result.succeeded:
        await message.answer(
            f"更新命令执行完成。\n\n<pre>{output}</pre>",
            parse_mode="HTML",
        )
        return
    await message.answer(
        f"更新命令执行失败。\n退出码：{result.return_code}\n\n<pre>{output}</pre>",
        parse_mode="HTML",
    )


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
