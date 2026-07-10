import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.formatters import format_sentence, format_word
from app.bot.keyboards.content import favorite_keyboard
from app.db.models import Delivery, User
from app.db.repositories.deliveries import DeliveryRepository
from app.db.repositories.users import UserRepository
from app.db.session import session_scope
from app.domain.enums import ContentType, DeliveryStatus
from app.domain.scheduling import local_date_for, next_daily_push_at
from app.domain.time import UTC
from app.services.delivery_service import DeliveryService

logger = logging.getLogger(__name__)


class DailyPushWorker:
    def __init__(self, *, retry_minutes: int = 5, max_attempts: int = 3) -> None:
        self.retry_delay = timedelta(minutes=retry_minutes)
        self.max_attempts = max_attempts

    async def run_once(self, bot: Bot, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        async with session_scope() as session:
            initialized = await UserRepository(session).initialize_missing_push_schedules(now=now)
            if initialized:
                logger.info("Initialized %d missing push schedules", initialized)

        async with session_scope() as session:
            users = await DeliveryRepository(session).list_due_users(now=now)
            for user in users:
                try:
                    await self._push_user(bot, user=user, now=now, session=session)
                except Exception:
                    logger.exception("Daily push failed for user_id=%s", user.id)
                    user.next_push_at = now + self.retry_delay
            return len(users)

    async def _push_user(
        self,
        bot: Bot,
        *,
        user: User,
        now: datetime,
        session: AsyncSession,
    ) -> None:
        local_date = local_date_for(timezone_name=user.timezone, moment=now)
        service = DeliveryService(session)
        completed = True

        for content_type in (ContentType.WORD, ContentType.SENTENCE):
            assert user.next_push_at is not None
            delivery = await service.get_or_create_daily(
                user=user,
                content_type=content_type,
                local_date=local_date,
                scheduled_for=user.next_push_at,
            )
            delivered, forbidden = await self._send_delivery(
                bot,
                user=user,
                delivery=delivery,
                service=service,
            )
            completed = completed and delivered
            if forbidden:
                user.daily_push_enabled = False
                user.next_push_at = None
                return

        if completed:
            user.next_push_at = next_daily_push_at(
                timezone_name=user.timezone,
                push_time=user.daily_push_time,
                after=now,
            )
        else:
            user.next_push_at = now + self.retry_delay

    async def _send_delivery(
        self,
        bot: Bot,
        *,
        user: User,
        delivery: Delivery,
        service: DeliveryService,
    ) -> tuple[bool, bool]:
        if delivery.status in (DeliveryStatus.SENT, DeliveryStatus.SKIPPED):
            return True, False
        if delivery.attempt_count >= self.max_attempts:
            service.mark_skipped(delivery)
            return True, False

        await service.mark_sending(delivery)
        formatter = format_word if delivery.content_type == ContentType.WORD else format_sentence
        try:
            message = await bot.send_message(
                chat_id=user.chat_id,
                text=formatter(delivery.content),
                parse_mode="HTML",
                reply_markup=favorite_keyboard(delivery.content_id),
            )
        except TelegramForbiddenError as exc:
            service.mark_failed(delivery, exc)
            logger.warning("User blocked bot; disabling push for user_id=%s", user.id)
            return False, True
        except Exception as exc:
            service.mark_failed(delivery, exc)
            logger.warning(
                "Telegram send failed for delivery_id=%s attempt=%d: %s",
                delivery.id,
                delivery.attempt_count,
                type(exc).__name__,
            )
            return False, False

        service.mark_sent(
            delivery,
            message_id=message.message_id,
            sent_at=datetime.now(UTC),
        )
        return True, False
