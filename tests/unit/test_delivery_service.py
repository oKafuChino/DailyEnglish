import uuid
from datetime import datetime, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.enums import ContentType, DeliveryStatus
from app.domain.scheduling import local_date_for, next_daily_push_at
from app.domain.time import UTC
from app.services.delivery_service import DeliveryService
from app.workers.daily_push import DailyPushWorker, PreparedPush


def test_next_push_uses_user_timezone_and_rolls_to_tomorrow() -> None:
    before_push = datetime(2026, 7, 11, 23, 0, tzinfo=UTC)  # 07:00 in Shanghai
    after_push = datetime(2026, 7, 12, 1, 0, tzinfo=UTC)  # 09:00 in Shanghai

    assert next_daily_push_at(
        timezone_name="Asia/Shanghai",
        push_time=time(8, 0),
        after=before_push,
    ) == datetime(2026, 7, 12, 0, 0, tzinfo=UTC)
    assert next_daily_push_at(
        timezone_name="Asia/Shanghai",
        push_time=time(8, 0),
        after=after_push,
    ) == datetime(2026, 7, 13, 0, 0, tzinfo=UTC)


def test_local_delivery_date_uses_user_timezone() -> None:
    moment = datetime(2026, 7, 11, 17, 0, tzinfo=UTC)

    assert local_date_for(timezone_name="Asia/Shanghai", moment=moment).isoformat() == "2026-07-12"


@pytest.mark.asyncio
async def test_existing_daily_delivery_is_reused() -> None:
    service = DeliveryService(SimpleNamespace())
    delivery = SimpleNamespace(status=DeliveryStatus.FAILED)
    service.deliveries = SimpleNamespace(
        get_daily=AsyncMock(return_value=delivery),
        create_daily=AsyncMock(),
    )
    service.contents = SimpleNamespace(get_random=AsyncMock())

    result = await service.get_or_create_daily(
        user=SimpleNamespace(id=1, preferred_difficulty="B2"),
        content_type=ContentType.WORD,
        local_date=datetime(2026, 7, 12).date(),
        scheduled_for=datetime(2026, 7, 12, tzinfo=UTC),
    )

    assert result is delivery
    service.contents.get_random.assert_not_awaited()
    service.deliveries.create_daily.assert_not_awaited()


@pytest.mark.asyncio
async def test_delivery_state_transitions_record_attempt_and_error() -> None:
    session = SimpleNamespace(flush=AsyncMock())
    service = DeliveryService(session)
    service.deliveries = SimpleNamespace(session=session)
    delivery = SimpleNamespace(
        status=DeliveryStatus.PENDING,
        attempt_count=0,
        last_error=None,
    )

    await service.mark_sending(delivery)
    assert delivery.status == DeliveryStatus.SENDING
    assert delivery.attempt_count == 1

    service.mark_failed(delivery, RuntimeError("network unavailable"))
    assert delivery.status == DeliveryStatus.FAILED
    assert "network unavailable" in delivery.last_error


def make_word_delivery(**overrides):
    values = {
        "id": "delivery-id",
        "content_id": uuid.uuid4(),
        "content_type": ContentType.WORD,
        "status": DeliveryStatus.PENDING,
        "attempt_count": 0,
        "content": SimpleNamespace(
            text_en="thrive",
            phonetic="/θraɪv/",
            part_of_speech="verb",
            difficulty="B2",
            translation_zh="茁壮成长",
            example_en=None,
            example_zh=None,
        ),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_prepared_push() -> PreparedPush:
    delivery = make_word_delivery()
    return PreparedPush(
        delivery_id=uuid.uuid4(),
        user_id=1,
        chat_id=123,
        content_id=delivery.content_id,
        content_type=delivery.content_type,
        content=delivery.content,
    )


@pytest.mark.asyncio
async def test_worker_marks_successful_telegram_delivery() -> None:
    worker = DailyPushWorker(max_attempts=3)
    bot = SimpleNamespace(send_message=AsyncMock(return_value=SimpleNamespace(message_id=99)))

    result = await worker._send_prepared(bot, make_prepared_push())

    assert result.message_id == 99
    assert result.error is None
    assert result.forbidden is False


@pytest.mark.asyncio
async def test_worker_alerts_owner_when_failures_reach_threshold() -> None:
    worker = DailyPushWorker(max_attempts=3, alert_failure_threshold=1, owner_telegram_id=42)
    bot = SimpleNamespace(send_message=AsyncMock())

    await worker._send_alert_if_needed(bot, failed=1, total=1)

    bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_does_not_alert_below_failure_threshold() -> None:
    worker = DailyPushWorker(max_attempts=3, alert_failure_threshold=2, owner_telegram_id=42)
    bot = SimpleNamespace(send_message=AsyncMock())

    await worker._send_alert_if_needed(bot, failed=1, total=3)

    bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_records_retryable_send_failure() -> None:
    worker = DailyPushWorker(max_attempts=3)
    bot = SimpleNamespace(send_message=AsyncMock(side_effect=RuntimeError("network")))

    result = await worker._send_prepared(bot, make_prepared_push())

    assert result.message_id is None
    assert isinstance(result.error, RuntimeError)
    assert result.forbidden is False
