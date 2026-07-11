"""Add favorite word review state.

Revision ID: 20260711_0006
Revises: 20260711_0005
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0006"
down_revision: str | None = "20260711_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "favorites",
        sa.Column("reviewed_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "favorites",
        sa.Column(
            "review_success_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "favorites",
        sa.Column(
            "review_fail_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "favorites",
        sa.Column("review_last_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_favorites_review_selection",
        "favorites",
        ["user_id", "reviewed_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_favorites_review_selection", table_name="favorites")
    op.drop_column("favorites", "review_last_at")
    op.drop_column("favorites", "review_fail_count")
    op.drop_column("favorites", "review_success_count")
    op.drop_column("favorites", "reviewed_until")
