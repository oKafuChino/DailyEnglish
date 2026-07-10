"""Create the initial application schema.

Revision ID: 20260710_0001
Revises:
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260710_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_status = sa.Enum(
    "pending", "active", "blocked", name="user_status", native_enum=False, length=16
)
content_type = sa.Enum("word", "sentence", name="content_type", native_enum=False, length=16)
content_status = sa.Enum(
    "draft", "approved", "rejected", name="content_status", native_enum=False, length=16
)
delivery_content_type = sa.Enum(
    "word", "sentence", name="delivery_content_type", native_enum=False, length=16
)
delivery_kind = sa.Enum("daily", "manual", name="delivery_kind", native_enum=False, length=16)
delivery_status = sa.Enum(
    "pending",
    "sending",
    "sent",
    "failed",
    "skipped",
    name="delivery_status",
    native_enum=False,
    length=16,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("status", user_status, server_default="pending", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Shanghai", nullable=False),
        sa.Column("daily_push_time", sa.Time(), server_default="08:00:00", nullable=False),
        sa.Column("daily_push_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("next_push_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("chat_id", name=op.f("uq_users_chat_id")),
        sa.UniqueConstraint("telegram_user_id", name=op.f("uq_users_telegram_user_id")),
    )
    op.create_index(op.f("ix_users_next_push_at"), "users", ["next_push_at"])
    op.create_index("ix_users_push_due", "users", ["daily_push_enabled", "status", "next_push_at"])

    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", content_type, nullable=False),
        sa.Column("text_en", sa.Text(), nullable=False),
        sa.Column("translation_zh", sa.Text(), nullable=False),
        sa.Column("phonetic", sa.String(length=128), nullable=True),
        sa.Column("part_of_speech", sa.String(length=64), nullable=True),
        sa.Column("example_en", sa.Text(), nullable=True),
        sa.Column("example_zh", sa.Text(), nullable=True),
        sa.Column("attribution", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", content_status, server_default="draft", nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_items")),
        sa.UniqueConstraint("content_hash", name=op.f("uq_content_items_content_hash")),
    )
    op.create_index(
        "ix_content_items_selection",
        "content_items",
        ["content_type", "status", "created_at"],
    )

    op.create_table(
        "invite_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_digest", sa.String(length=64), nullable=False),
        sa.Column("created_by_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "redeemed_at IS NULL OR redeemed_by_user_id IS NOT NULL",
            name=op.f("ck_invite_codes_redeemed_user_required"),
        ),
        sa.ForeignKeyConstraint(
            ["redeemed_by_user_id"],
            ["users.id"],
            name=op.f("fk_invite_codes_redeemed_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invite_codes")),
        sa.UniqueConstraint("code_digest", name=op.f("uq_invite_codes_code_digest")),
    )
    op.create_index(
        op.f("ix_invite_codes_created_by_telegram_id"), "invite_codes", ["created_by_telegram_id"]
    )
    op.create_index(op.f("ix_invite_codes_expires_at"), "invite_codes", ["expires_at"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_audit_logs")),
    )
    op.create_index(op.f("ix_admin_audit_logs_action"), "admin_audit_logs", ["action"])
    op.create_index(
        op.f("ix_admin_audit_logs_admin_telegram_id"), "admin_audit_logs", ["admin_telegram_id"]
    )
    op.create_index(op.f("ix_admin_audit_logs_created_at"), "admin_audit_logs", ["created_at"])

    op.create_table(
        "favorites",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["content_items.id"],
            name=op.f("fk_favorites_content_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_favorites_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_favorites")),
        sa.UniqueConstraint("user_id", "content_id", name="uq_favorites_user_content"),
    )
    op.create_index(op.f("ix_favorites_content_id"), "favorites", ["content_id"])
    op.create_index(op.f("ix_favorites_user_id"), "favorites", ["user_id"])

    op.create_table(
        "deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", delivery_content_type, nullable=False),
        sa.Column("kind", delivery_kind, nullable=False),
        sa.Column("status", delivery_status, server_default="pending", nullable=False),
        sa.Column("local_delivery_date", sa.Date(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "kind <> 'daily' OR local_delivery_date IS NOT NULL",
            name=op.f("ck_deliveries_daily_date_required"),
        ),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["content_items.id"],
            name=op.f("fk_deliveries_content_id_content_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_deliveries_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deliveries")),
        sa.UniqueConstraint(
            "user_id",
            "local_delivery_date",
            "content_type",
            "kind",
            name="uq_deliveries_daily_slot",
        ),
    )
    op.create_index(op.f("ix_deliveries_content_id"), "deliveries", ["content_id"])
    op.create_index("ix_deliveries_pending", "deliveries", ["status", "scheduled_for"])
    op.create_index(op.f("ix_deliveries_scheduled_for"), "deliveries", ["scheduled_for"])
    op.create_index(op.f("ix_deliveries_user_id"), "deliveries", ["user_id"])


def downgrade() -> None:
    op.drop_table("deliveries")
    op.drop_table("favorites")
    op.drop_table("admin_audit_logs")
    op.drop_table("invite_codes")
    op.drop_table("content_items")
    op.drop_table("users")
