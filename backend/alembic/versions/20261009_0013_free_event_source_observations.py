"""Append-only, minimal source observation history (real fetches only).

Revision ID: 20261009_0013
Revises: 20261009_0012
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261009_0013"
down_revision: str | None = "20261009_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "free_event_source_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(80),
                  sa.ForeignKey("free_event_sources.id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("endpoint_key", sa.String(64), nullable=False),
        sa.Column("response_fingerprint", sa.String(64), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("fee_unknown_count", sa.Integer(), nullable=False),
        sa.Column("registration_start_unknown_count", sa.Integer(), nullable=False),
        sa.Column("complete_source", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "record_count >= 0 AND accepted_count >= 0 AND rejected_count >= 0",
            name="ck_free_event_obs_nonnegative",
        ),
        sa.CheckConstraint(
            "accepted_count + rejected_count <= record_count",
            name="ck_free_event_obs_bounded_counts",
        ),
    )
    op.create_index(
        "ix_free_event_observations_source_time",
        "free_event_source_observations", ["source_id", "observed_at"],
    )


def downgrade() -> None:
    # Never invoked automatically; would destroy real observational evidence.
    op.drop_index("ix_free_event_observations_source_time",
                  table_name="free_event_source_observations")
    op.drop_table("free_event_source_observations")
