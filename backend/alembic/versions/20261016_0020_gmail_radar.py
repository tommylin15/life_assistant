"""Add manual-only Gmail radar result and scan summary tables.

Revision ID: 20261016_0020
Revises: 20261016_0019
"""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0020"
down_revision = "20261016_0019"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "gmail_radar_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("gmail_message_id", sa.String(255), nullable=False),
        sa.Column("gmail_thread_id", sa.String(255), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.String(320), nullable=False, server_default=""),
        sa.Column("sender", sa.String(320), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_sub", "gmail_message_id", name="uq_gmail_radar_user_message"),
        sa.CheckConstraint("status IN ('pending','completed','ignored')", name="ck_gmail_radar_status"),
    )
    op.create_index("ix_gmail_radar_user_status", "gmail_radar_items", ["user_sub", "status"])
    op.create_table(
        "gmail_radar_scan_states",
        sa.Column("user_sub", sa.String(255), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("last_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_finished_at", sa.DateTime(timezone=True)),
        sa.Column("checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("status IN ('succeeded','partial','failed')", name="ck_gmail_radar_scan_status"),
    )


def downgrade():
    # Retain the user's derived Gmail radar items; destructive downgrade prohibited.
    raise RuntimeError("Destructive Gmail radar downgrade requires explicit approval")
