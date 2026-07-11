from html import escape
from secrets import token_urlsafe
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.filters.private_chat import PrivateChatFilter
from app.bot.keyboards.review import ReviewChoiceCallback, review_choice_keyboard
from app.bot.middlewares.registration import RegistrationMiddleware
from app.bot.states.review import Review
from app.db.models import User
from app.db.session import session_scope
from app.services.review_service import (
    REVIEW_BATCH_SIZE,
    ReviewService,
    format_review_correct_answer,
    is_spelling_correct,
    review_questions_to_state,
    review_state_item_passed,
)

router = Router(name="review")
router.message.filter(PrivateChatFilter())
router.callback_query.filter(PrivateChatFilter())
router.message.middleware(RegistrationMiddleware())
router.callback_query.middleware(RegistrationMiddleware())


def _question_text(item: dict[str, Any], index: int, total: int) -> str:
    return (
        f"🧠 <b>收藏单词复习 {index + 1}/{total}</b>\n\n"
        f"请选择 <b>{escape(item['word'])}</b> 的正确中文释义："
    )


def _spelling_prompt(item: dict[str, Any]) -> str:
    return f"✍️ <b>拼写挑战</b>\n\n请根据中文释义拼写英文单词：\n{escape(item['translation'])}"


def _summary_text(items: list[dict[str, Any]]) -> str:
    passed = sum(1 for item in items if review_state_item_passed(item))
    failed = len(items) - passed
    return (
        "✅ 本轮复习完成！\n\n"
        f"共复习：{len(items)} 个收藏单词\n"
        f"完全通过：{passed} 个\n"
        f"需要巩固：{failed} 个\n\n"
        "完全通过的单词会暂时离开复习池；答错的单词下次仍会被抽到。"
    )


async def _send_choice_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    items = data.get("items") or []
    index = int(data.get("index") or 0)
    session_id = str(data.get("session_id") or "")
    if index >= len(items):
        await message.answer(_summary_text(items))
        await state.clear()
        return

    item = items[index]
    await state.set_state(Review.waiting_for_choice)
    await message.answer(
        _question_text(item, index, len(items)),
        parse_mode="HTML",
        reply_markup=review_choice_keyboard(
            item["options"],
            session_id=session_id,
            question_index=index,
        ),
    )


async def _finish_current_item(
    message: Message,
    state: FSMContext,
    current_user: User,
    *,
    spelling_passed: bool,
) -> None:
    data = await state.get_data()
    items = data.get("items") or []
    index = int(data.get("index") or 0)
    if index >= len(items):
        await state.clear()
        await message.answer("当前复习会话已结束，请发送 /review 开始新一轮复习。")
        return

    item = items[index]
    item["spelling_passed"] = spelling_passed
    passed = review_state_item_passed(item)
    async with session_scope() as session:
        await ReviewService(session).record_result(
            user_id=current_user.id,
            favorite_id=int(item["favorite_id"]),
            passed=passed,
        )

    if spelling_passed:
        await message.answer("✅ 拼写正确！")
    else:
        await message.answer(f"❌ 拼写不正确。正确答案：{escape(item['word'])}", parse_mode="HTML")

    if passed:
        await message.answer("🎉 这个单词两关都通过了，未来 3 天内会暂时离开复习池。")
    else:
        await message.answer("📌 这个单词还需要巩固，下次复习仍可能抽到。")

    next_index = index + 1
    await state.update_data(items=items, index=next_index)
    if next_index >= len(items):
        await message.answer(_summary_text(items))
        await state.clear()
        return
    await _send_choice_question(message, state)


@router.message(Command("review"), flags={"rate_limit": "content"})
async def start_review(message: Message, state: FSMContext, current_user: User) -> None:
    await state.clear()
    async with session_scope() as session:
        questions = await ReviewService(session).build_session(user_id=current_user.id)

    if not questions:
        await message.answer(
            "你还没有可复习的收藏单词。\n\n"
            "可以先用 /word 获取单词并点击收藏，之后再发送 /review 开始复习。"
        )
        return

    await state.update_data(
        items=review_questions_to_state(questions),
        index=0,
        session_id=token_urlsafe(6),
    )
    await message.answer(
        f"🧠 本轮将从你的收藏夹中抽取 {len(questions)} 个单词复习。"
        f"{'每轮最多 10 个。' if len(questions) == REVIEW_BATCH_SIZE else ''}"
    )
    await _send_choice_question(message, state)


@router.callback_query(
    ReviewChoiceCallback.filter(),
    Review.waiting_for_choice,
    flags={"rate_limit": "callback"},
)
async def receive_choice(
    callback: CallbackQuery,
    callback_data: ReviewChoiceCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    items = data.get("items") or []
    index = int(data.get("index") or 0)
    if index >= len(items):
        await state.clear()
        await callback.answer("复习会话已结束，请重新发送 /review。", show_alert=True)
        return

    item = items[index]
    if (
        callback_data.session_id != str(data.get("session_id") or "")
        or callback_data.question != index
    ):
        await callback.answer("这道复习题已经过期，请回答当前最新题目。", show_alert=True)
        return

    choice_passed = callback_data.answer == int(item["correct_option"])
    item["choice_passed"] = choice_passed
    await state.update_data(items=items)
    await callback.answer("回答正确" if choice_passed else "回答错误")

    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        if choice_passed:
            await callback.message.answer("✅ 选择正确！")
        else:
            await callback.message.answer(
                f"❌ 选择不正确。正确答案：{escape(format_review_correct_answer(item))}",
                parse_mode="HTML",
            )
        await state.set_state(Review.waiting_for_spelling)
        await callback.message.answer(_spelling_prompt(item), parse_mode="HTML")


@router.callback_query(ReviewChoiceCallback.filter(), flags={"rate_limit": "callback"})
async def reject_stale_choice(callback: CallbackQuery) -> None:
    await callback.answer("这道复习题已经结束，请继续当前题目或重新发送 /review。", show_alert=True)


@router.callback_query(F.data.startswith("review_choice:"), flags={"rate_limit": "callback"})
async def reject_legacy_or_invalid_choice(callback: CallbackQuery) -> None:
    await callback.answer("这道复习题已经过期，请重新发送 /review。", show_alert=True)


@router.message(Review.waiting_for_choice, F.text.regexp(r"^[^/]"))
async def reject_text_during_choice(message: Message) -> None:
    await message.answer("请点击上面的四个中文选项之一；如需退出复习，请发送 /cancel。")


@router.message(Review.waiting_for_choice, ~F.text)
async def reject_non_text_during_choice(message: Message) -> None:
    await message.answer("请点击上面的四个中文选项之一；如需退出复习，请发送 /cancel。")


@router.message(Review.waiting_for_spelling, F.text.regexp(r"^[^/]"))
async def receive_spelling(message: Message, state: FSMContext, current_user: User) -> None:
    data = await state.get_data()
    items = data.get("items") or []
    index = int(data.get("index") or 0)
    if index >= len(items):
        await state.clear()
        await message.answer("当前复习会话已结束，请发送 /review 开始新一轮复习。")
        return

    item = items[index]
    spelling_passed = is_spelling_correct(message.text or "", item["word"])
    await _finish_current_item(
        message,
        state,
        current_user,
        spelling_passed=spelling_passed,
    )


@router.message(Review.waiting_for_spelling, ~F.text)
async def reject_non_text_during_spelling(message: Message) -> None:
    await message.answer("请直接输入英文单词；如需退出复习，请发送 /cancel。")


@router.message(Command("cancel"), Review.waiting_for_choice)
@router.message(Command("cancel"), Review.waiting_for_spelling)
async def cancel_review(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("已退出本轮单词复习。")
