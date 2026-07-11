"""Add content difficulty selection index.

Revision ID: 20260711_0005
Revises: 20260711_0004
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260711_0005"
down_revision: str | None = "20260711_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_content_items_difficulty_selection",
        "content_items",
        ["content_type", "status", "difficulty", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_items_difficulty_selection", table_name="content_items")
