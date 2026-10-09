"""Add durable, per-source batch leases; no sources are scheduled or activated.

Revision ID: 20261009_0012
Revises: 20261009_0011
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261009_0012"
down_revision: str | None = "20261009_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "free_event_ingestion_leases",
        sa.Column("source_id", sa.String(80),
                  sa.ForeignKey("free_event_sources.id"), primary_key=True),
        sa.Column("lease_token", sa.String(64), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("last_error_kind", sa.String(40)),
        sa.CheckConstraint("consecutive_failures >= 0",
                           name="ck_free_event_lease_nonnegative_failures"),
    )


def downgrade() -> None:
    # Never executed by the release path; controlled dev/test only.
    op.drop_table("free_event_ingestion_leases")
