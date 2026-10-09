"""Add durable normalized candidate queue, additive and independent of old data.

Revision ID: 20261009_0014
Revises: 20261009_0013
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa
from app.services.free_events_schema_reconcile import create_checked_table, create_checked_index

revision: str = "20261009_0014"
down_revision: str | None = "20261009_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    create_checked_table(
        "free_event_candidate_queue",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(80),
                  sa.ForeignKey("free_event_sources.id"), nullable=False),
        sa.Column("external_event_key", sa.String(255), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("candidate_payload", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False,
                  server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.String(64)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_kind", sa.String(40)),
        sa.UniqueConstraint("source_id", "external_event_key",
                            name="uq_free_event_candidate_source_key"),
        sa.CheckConstraint(
            "state IN ('pending', 'processing', 'done', 'retry', 'failed')",
            name="ck_free_event_candidate_state",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 5",
            name="ck_free_event_candidate_attempts",
        ),
    )
    create_checked_index(
        "ix_free_event_candidate_claim", "free_event_candidate_queue",
        ["source_id", "state", "next_retry_at"],
    )


def downgrade() -> None:
    # Not part of production release: would delete queue evidence.
    op.drop_index("ix_free_event_candidate_claim",
                  table_name="free_event_candidate_queue")
    op.drop_table("free_event_candidate_queue")
