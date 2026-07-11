from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Delivery, User
from app.db.repositories.deliveries import DeliveryRepository
from app.domain.enums import ContentType, DeliveryStatus
from app.services.content_service import ContentService


class DeliveryService:
    def __init__(self, session: AsyncSession) -> None:
        self.deliveries = DeliveryRepository(session)
        self.contents = ContentService(session)

    async def get_or_create_daily(
        self,
        *,
        user: User,
        content_type: ContentType,
        local_date: date,
        scheduled_for: datetime,
    ) -> Delivery:
        delivery = await self.deliveries.get_daily(
            user_id=user.id,
            local_date=local_date,
            content_type=content_type,
        )
        if delivery is not None:
            return delivery
        content = await self.contents.get_random(
            content_type,
            difficulty=user.preferred_difficulty,
        )
        return await self.deliveries.create_daily(
            user=user,
            content=content,
            local_date=local_date,
            scheduled_for=scheduled_for,
        )

    async def mark_sending(self, delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.SENDING
        delivery.attempt_count += 1
        delivery.last_error = None
        await self.deliveries.session.flush()

    @staticmethod
    def mark_sent(delivery: Delivery, *, message_id: int, sent_at: datetime) -> None:
        delivery.status = DeliveryStatus.SENT
        delivery.telegram_message_id = message_id
        delivery.sent_at = sent_at
        delivery.last_error = None

    @staticmethod
    def mark_failed(delivery: Delivery, error: Exception) -> None:
        delivery.status = DeliveryStatus.FAILED
        delivery.last_error = f"{type(error).__name__}: {error}"[:2000]

    @staticmethod
    def mark_skipped(delivery: Delivery) -> None:
        delivery.status = DeliveryStatus.SKIPPED
