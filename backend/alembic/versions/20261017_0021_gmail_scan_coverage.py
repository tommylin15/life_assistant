"""Add explicit Gmail three-day coverage and per-user seen ID cache.

Revision ID: 20261017_0021
Revises: 20261016_0020
"""
from alembic import op
import sqlalchemy as sa

revision = "20261017_0021"
down_revision = "20261016_0020"
branch_labels = depends_on = None


def upgrade():
    op.add_column("gmail_radar_scan_states",
        sa.Column("scan_kind", sa.String(20), nullable=False, server_default="quick"))
    op.add_column("gmail_radar_scan_states",
        sa.Column("three_day_count", sa.Integer(), nullable=True))
    op.add_column("gmail_radar_scan_states",
        sa.Column("three_day_remaining", sa.Integer(), nullable=True))
    op.add_column("gmail_radar_scan_states",
        sa.Column("three_day_complete", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "gmail_radar_seen",
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_sub", "gmail_message_id",
                                name="pk_gmail_radar_seen"),
    )
    op.create_index("ix_gmail_radar_seen_checked_at",
                    "gmail_radar_seen", ["checked_at"])


def downgrade():
    raise RuntimeError("Destructive Gmail scan coverage downgrade requires explicit approval")
