"""Persist last-known-good external AI provider model.

Revision ID: 20261007_0010
Revises: 20261002_0009
Create Date: 2026-10-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261007_0010"
down_revision: str | None = "20261002_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_preferences",
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("preferred_model", sa.String(length=255), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("provider"),
    )


def downgrade() -> None:
    op.drop_table("ai_provider_preferences")
