import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from app.bot.formatters import format_sentence, format_word
from app.bot.keyboards.content import favorite_keyboard
from app.db.models import ContentItem, User
from app.db.repositories.deliveries import DeliveryRepository
from app.db.repositories.users import UserRepository
from app.db.session import session_scope
from app.domain.enums import ContentType, DeliveryStatus
from app.domain.scheduling import local_date_for, next_daily_push_at
from app.domain.time import UTC
from app.services.delivery_service import DeliveryService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreparedPush:
    delivery_id: uuid.UUID
    user_id: int
    chat_id: int
    content_id: uuid.UUID
    content_type: ContentType
    content: ContentItem


@dataclass(frozen=True)
class PushResult:
    message_id: int | None = None
    error: Exception | None = None
    forbidden: bool = False


@dataclass(frozen=True)
class ClaimedUser:
    user_id: int
    timezone: str
    push_time: time
    local_date: date


class DailyPushWorker:
    def __init__(
        self,
        *,
        retry_minutes: int = 5,
        max_attempts: int = 3,
        alert_failure_threshold: int = 3,
        owner_telegram_id: int | None = None,
    ) -> None:
        self.retry_delay = timedelta(minutes=retry_minutes)
        self.claim_timeout = max(self.retry_delay, timedelta(minutes=10))
        self.max_attempts = max_attempts
        self.alert_failure_threshold = alert_failure_threshold
        self.owner_telegram_id = owner_telegram_id

    async def run_once(self, bot: Bot, *, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        async with session_scope() as session:
            initialized = await UserRepository(session).initialize_missing_push_schedules(now=now)
            if initialized:
                logger.info("Initialized %d missing push schedules", initialized)

        jobs, users = await self._claim_due_pushes(now=now)
        disabled_users: set[int] = set()
        alert_failures = 0
        for job in jobs:
            if job.user_id in disabled_users:
                result = PushResult(
                    error=RuntimeError("push disabled after Telegram forbidden response"),
                    forbidden=True,
                )
            else:
                result = await self._send_prepared(bot, job)
            await self._record_result(job, result)
            if result.error is not None and not result.forbidden:
                alert_failures += 1
            if result.forbidden:
                disabled_users.add(job.user_id)
        for claimed_user in users:
            await self._finalize_user(claimed_user, now=datetime.now(UTC))
        await self._send_alert_if_needed(bot, failed=alert_failures, total=len(jobs))
        return len(users)

    async def _claim_due_pushes(
        self,
        *,
        now: datetime,
    ) -> tuple[list[PreparedPush], list[ClaimedUser]]:
        jobs: list[PreparedPush] = []
        claimed_users: list[ClaimedUser] = []
        stale_before = now - self.claim_timeout

        async with session_scope() as session:
            users = await DeliveryRepository(session).list_due_users(now=now)
            for user in users:
                local_date = local_date_for(timezone_name=user.timezone, moment=now)
                claimed_users.append(
                    ClaimedUser(
                        user_id=user.id,
                        timezone=user.timezone,
                        push_time=user.daily_push_time,
                        local_date=local_date,
                    )
                )
                service = DeliveryService(session)
                for content_type in (ContentType.WORD, ContentType.SENTENCE):
                    assert user.next_push_at is not None
                    delivery = await service.get_or_create_daily(
                        user=user,
                        content_type=content_type,
                        local_date=local_date,
                        scheduled_for=user.next_push_at,
                    )
                    if delivery.status in (DeliveryStatus.SENT, DeliveryStatus.SKIPPED):
                        continue
                    if delivery.status == DeliveryStatus.SENDING:
                        updated_at = delivery.updated_at or delivery.created_at
                        if updated_at is not None and updated_at > stale_before:
                            continue
                        service.mark_failed(delivery, RuntimeError("stale sending claim recovered"))
                    if delivery.attempt_count >= self.max_attempts:
                        service.mark_skipped(delivery)
                        continue

                    await service.mark_sending(delivery)
                    jobs.append(
                        PreparedPush(
                            delivery_id=delivery.id,
                            user_id=user.id,
                            chat_id=user.chat_id,
                            content_id=delivery.content_id,
                            content_type=delivery.content_type,
                            content=delivery.content,
                        )
                    )

                # This claim prevents another worker from immediately selecting the user.
                user.next_push_at = now + self.claim_timeout
        return jobs, claimed_users

    async def _send_prepared(self, bot: Bot, job: PreparedPush) -> PushResult:
        formatter = format_word if job.content_type == ContentType.WORD else format_sentence
        try:
            message = await bot.send_message(
                chat_id=job.chat_id,
                text=formatter(job.content),
                parse_mode="HTML",
                reply_markup=favorite_keyboard(job.content_id),
            )
        except TelegramForbiddenError as exc:
            logger.warning("User blocked bot; disabling push for user_id=%s", job.user_id)
            return PushResult(error=exc, forbidden=True)
        except Exception as exc:
            logger.warning(
                "Telegram send failed for delivery_id=%s: %s",
                job.delivery_id,
                type(exc).__name__,
            )
            return PushResult(error=exc)
        return PushResult(message_id=message.message_id)

    async def _record_result(self, job: PreparedPush, result: PushResult) -> None:
        async with session_scope() as session:
            repository = DeliveryRepository(session)
            delivery = await repository.get_by_id_for_update(job.delivery_id)
            if delivery is None or delivery.status != DeliveryStatus.SENDING:
                return
            service = DeliveryService(session)
            if result.error is None and result.message_id is not None:
                service.mark_sent(
                    delivery,
                    message_id=result.message_id,
                    sent_at=datetime.now(UTC),
                )
            else:
                service.mark_failed(delivery, result.error or RuntimeError("unknown send failure"))

            if result.forbidden:
                user = await session.get(User, job.user_id, with_for_update=True)
                if user is not None:
                    user.daily_push_enabled = False
                    user.next_push_at = None

    async def _finalize_user(self, claimed: ClaimedUser, *, now: datetime) -> None:
        async with session_scope() as session:
            user = await session.get(User, claimed.user_id, with_for_update=True)
            if user is None or not user.daily_push_enabled:
                return
            deliveries = await DeliveryRepository(session).list_daily_for_user(
                user_id=user.id,
                local_date=claimed.local_date,
            )
            terminal = {DeliveryStatus.SENT, DeliveryStatus.SKIPPED}
            types = {
                delivery.content_type for delivery in deliveries if delivery.status in terminal
            }
            if types == {ContentType.WORD, ContentType.SENTENCE}:
                user.next_push_at = next_daily_push_at(
                    timezone_name=claimed.timezone,
                    push_time=claimed.push_time,
                    after=now,
                )
            else:
                user.next_push_at = now + self.retry_delay

    async def _send_alert_if_needed(self, bot: Bot, *, failed: int, total: int) -> None:
        if self.alert_failure_threshold <= 0 or self.owner_telegram_id is None:
            return
        if failed < self.alert_failure_threshold:
            return
        try:
            await bot.send_message(
                chat_id=self.owner_telegram_id,
                text=(
                    "⚠️ DailyEnglish 推送告警\n\n"
                    f"本轮推送失败 {failed}/{total} 条，已达到阈值 "
                    f"{self.alert_failure_threshold}。请检查 Worker 日志和 Telegram 网络状态。"
                ),
            )
        except Exception:
            logger.exception("Failed to send worker alert to owner")
