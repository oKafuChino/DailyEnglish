import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ContentItem, Delivery, User
from app.domain.enums import ContentType, DeliveryKind, DeliveryStatus, UserStatus


class DeliveryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_due_users(self, *, now: datetime, limit: int = 20) -> list[User]:
        result = await self.session.scalars(
            select(User)
            .where(
                User.status == UserStatus.ACTIVE,
                User.daily_push_enabled.is_(True),
                User.next_push_at.is_not(None),
                User.next_push_at <= now,
            )
            .order_by(User.next_push_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result)

    async def get_daily(
        self,
        *,
        user_id: int,
        local_date: date,
        content_type: ContentType,
    ) -> Delivery | None:
        return await self.session.scalar(
            select(Delivery)
            .where(
                Delivery.user_id == user_id,
                Delivery.local_delivery_date == local_date,
                Delivery.content_type == content_type,
                Delivery.kind == DeliveryKind.DAILY,
            )
            .options(selectinload(Delivery.content))
        )

    async def get_by_id_for_update(self, delivery_id: uuid.UUID) -> Delivery | None:
        return await self.session.scalar(
            select(Delivery)
            .where(Delivery.id == delivery_id)
            .options(selectinload(Delivery.content))
            .with_for_update()
        )

    async def list_daily_for_user(
        self,
        *,
        user_id: int,
        local_date: date,
    ) -> list[Delivery]:
        result = await self.session.scalars(
            select(Delivery).where(
                Delivery.user_id == user_id,
                Delivery.local_delivery_date == local_date,
                Delivery.kind == DeliveryKind.DAILY,
            )
        )
        return list(result)

    async def create_daily(
        self,
        *,
        user: User,
        content: ContentItem,
        local_date: date,
        scheduled_for: datetime,
    ) -> Delivery:
        delivery = Delivery(
            user_id=user.id,
            content=content,
            content_type=content.content_type,
            kind=DeliveryKind.DAILY,
            status=DeliveryStatus.PENDING,
            local_delivery_date=local_date,
            scheduled_for=scheduled_for,
        )
        self.session.add(delivery)
        await self.session.flush()
        return delivery
