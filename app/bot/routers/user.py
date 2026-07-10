import math

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message

from app.bot.filters.private_chat import PrivateChatFilter
from app.bot.formatters import format_sentence, format_word
from app.bot.keyboards.content import (
    FavoriteCallback,
    daily_favorite_keyboard,
    favorite_keyboard,
)
from app.bot.middlewares.registration import RegistrationMiddleware
from app.db.models import ContentItem, User
from app.db.session import session_scope
from app.domain.enums import ContentType
from app.exceptions import FavoriteContentNotFoundError
from app.services.content_service import ContentService, ContentUnavailableError
from app.services.favorite_service import FavoriteService

router = Router(name="user")
router.message.filter(PrivateChatFilter())
router.callback_query.filter(PrivateChatFilter())
router.message.middleware(RegistrationMiddleware())
router.callback_query.middleware(RegistrationMiddleware())


async def _get_content(kind: str) -> ContentItem:
    async with session_scope() as session:
        service = ContentService(session)
        if kind == "word":
            return await service.get_word()
        return await service.get_sentence()


@router.message(Command("word"), flags={"rate_limit": "content"})
async def word(message: Message) -> None:
    try:
        content = await _get_content("word")
    except ContentUnavailableError:
        await message.answer("暂时没有可用的单词，请稍后再试。")
        return
    await message.answer(
        format_word(content),
        parse_mode="HTML",
        reply_markup=favorite_keyboard(content.id),
    )


@router.message(Command("sentence"), flags={"rate_limit": "content"})
async def sentence(message: Message) -> None:
    try:
        content = await _get_content("sentence")
    except ContentUnavailableError:
        await message.answer("暂时没有可用的句子，请稍后再试。")
        return
    await message.answer(
        format_sentence(content),
        parse_mode="HTML",
        reply_markup=favorite_keyboard(content.id),
    )


@router.message(Command("daily"), flags={"rate_limit": "content"})
async def daily(message: Message) -> None:
    try:
        async with session_scope() as session:
            service = ContentService(session)
            word_content = await service.get_word()
            sentence_content = await service.get_sentence()
    except ContentUnavailableError:
        await message.answer("今日内容暂时不可用，请稍后再试。")
        return

    text = f"{format_word(word_content)}\n\n──────────\n\n{format_sentence(sentence_content)}"
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=daily_favorite_keyboard(word_content.id, sentence_content.id),
    )


@router.callback_query(
    FavoriteCallback.filter(),
    flags={"rate_limit": "callback"},
)
async def toggle_favorite(
    callback: CallbackQuery,
    callback_data: FavoriteCallback,
    current_user: User,
) -> None:
    try:
        async with session_scope() as session:
            service = FavoriteService(session)
            if callback_data.action == "add":
                changed = await service.add(
                    user_id=current_user.id,
                    content_id=callback_data.content_id,
                )
                response = "已收藏" if changed else "已经收藏过了"
            elif callback_data.action == "remove":
                changed = await service.remove(
                    user_id=current_user.id,
                    content_id=callback_data.content_id,
                )
                response = "已取消收藏" if changed else "收藏已不存在"
            else:
                await callback.answer("未知操作", show_alert=True)
                return
    except FavoriteContentNotFoundError:
        await callback.answer("该内容已不存在", show_alert=True)
        return

    await callback.answer(response)
    if callback.message and callback.message.reply_markup:
        buttons = callback.message.reply_markup.inline_keyboard
        if len(buttons) == 1 and len(buttons[0]) == 1:
            await callback.message.edit_reply_markup(
                reply_markup=favorite_keyboard(
                    callback_data.content_id,
                    saved=callback_data.action == "add",
                )
            )


@router.message(Command("saved"), flags={"rate_limit": "content"})
async def saved(message: Message, command: CommandObject, current_user: User) -> None:
    try:
        page = int(command.args) if command.args else 1
        if page < 1:
            raise ValueError
    except ValueError:
        await message.answer("用法：/saved [页码]")
        return

    async with session_scope() as session:
        items, total = await FavoriteService(session).list_page(
            user_id=current_user.id,
            page=page,
        )
    if not items:
        await message.answer("这一页没有收藏内容。" if total else "你还没有收藏任何内容。")
        return

    pages = math.ceil(total / 5)
    await message.answer(f"⭐ 我的收藏｜第 {page}/{pages} 页")
    for favorite in items:
        formatter = (
            format_word if favorite.content.content_type == ContentType.WORD else format_sentence
        )
        await message.answer(
            formatter(favorite.content),
            parse_mode="HTML",
            reply_markup=favorite_keyboard(favorite.content_id, saved=True),
        )
