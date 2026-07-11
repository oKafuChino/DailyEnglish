"""Support multiple preferred push difficulties.

Revision ID: 20260711_0003
Revises: 20260711_0002
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260711_0003"
down_revision: str | None = "20260711_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE users SET preferred_difficulty = 'B1,B2,C1' WHERE preferred_difficulty = 'mixed'"
    )
    op.alter_column(
        "users",
        "preferred_difficulty",
        existing_type=sa.String(length=16),
        server_default="B1,B2,C1",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET preferred_difficulty = 'mixed' WHERE preferred_difficulty = 'B1,B2,C1'"
    )
    op.alter_column(
        "users",
        "preferred_difficulty",
        existing_type=sa.String(length=16),
        server_default="mixed",
        existing_nullable=False,
    )
