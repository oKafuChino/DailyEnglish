import uuid
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    ContentStatus,
    ContentType,
    DeliveryKind,
    DeliveryStatus,
    UserStatus,
)

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

json_type = JSON().with_variant(JSONB(), "postgresql")


def enum_values(enum_class: type) -> list[str]:
    return [item.value for item in enum_class]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=UserStatus.PENDING,
        server_default=UserStatus.PENDING.value,
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(
        String(64), default="Asia/Shanghai", server_default="Asia/Shanghai", nullable=False
    )
    preferred_difficulty: Mapped[str] = mapped_column(
        String(16), default="mixed", server_default="mixed", nullable=False
    )
    daily_push_time: Mapped[time] = mapped_column(
        Time(timezone=False), default=time(8, 0), server_default="08:00:00", nullable=False
    )
    daily_push_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    next_push_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    redeemed_invites: Mapped[list["InviteCode"]] = relationship(back_populates="redeemed_by_user")
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    deliveries: Mapped[list["Delivery"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_users_push_due", "daily_push_enabled", "status", "next_push_at"),)


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_by_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    redeemed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    redeemed_by_user: Mapped[User | None] = relationship(back_populates="redeemed_invites")

    __table_args__ = (
        CheckConstraint(
            "redeemed_at IS NULL OR redeemed_by_user_id IS NOT NULL",
            name="redeemed_user_required",
        ),
    )


class ContentItem(TimestampMixin, Base):
    __tablename__ = "content_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type: Mapped[ContentType] = mapped_column(
        Enum(
            ContentType,
            name="content_type",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    translation_zh: Mapped[str] = mapped_column(Text, nullable=False)
    phonetic: Mapped[str | None] = mapped_column(String(128))
    part_of_speech: Mapped[str | None] = mapped_column(String(64))
    example_en: Mapped[str | None] = mapped_column(Text)
    example_zh: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(
            ContentStatus,
            name="content_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=ContentStatus.DRAFT,
        server_default=ContentStatus.DRAFT.value,
        nullable=False,
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        "metadata", json_type, default=dict, server_default="{}", nullable=False
    )

    favorites: Mapped[list["Favorite"]] = relationship(back_populates="content")
    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="content")

    __table_args__ = (Index("ix_content_items_selection", "content_type", "status", "created_at"),)


class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="favorites")
    content: Mapped[ContentItem] = relationship(back_populates="favorites")

    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_favorites_user_content"),)


class Delivery(TimestampMixin, Base):
    __tablename__ = "deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    content_type: Mapped[ContentType] = mapped_column(
        Enum(
            ContentType,
            name="delivery_content_type",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    kind: Mapped[DeliveryKind] = mapped_column(
        Enum(
            DeliveryKind,
            name="delivery_kind",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(
            DeliveryStatus,
            name="delivery_status",
            native_enum=False,
            length=16,
            values_callable=enum_values,
        ),
        default=DeliveryStatus.PENDING,
        server_default=DeliveryStatus.PENDING.value,
        nullable=False,
    )
    local_delivery_date: Mapped[date | None] = mapped_column(Date)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    attempt_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="deliveries")
    content: Mapped[ContentItem] = relationship(back_populates="deliveries")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "local_delivery_date",
            "content_type",
            "kind",
            name="uq_deliveries_daily_slot",
        ),
        CheckConstraint(
            "kind <> 'daily' OR local_delivery_date IS NOT NULL",
            name="daily_date_required",
        ),
        Index("ix_deliveries_pending", "status", "scheduled_for"),
    )


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(128))
    details: Mapped[dict[str, Any]] = mapped_column(
        json_type, default=dict, server_default="{}", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
