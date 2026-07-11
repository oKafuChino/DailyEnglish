"""Add user preferred content difficulty.

Revision ID: 20260711_0002
Revises: 20260710_0001
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0002"
down_revision: str | None = "20260710_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "preferred_difficulty",
            sa.String(length=16),
            server_default="mixed",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_difficulty")
