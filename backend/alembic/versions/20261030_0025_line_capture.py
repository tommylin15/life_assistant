"""Add scoped LINE-only pending conversation states; preserve existing Life rows."""
from alembic import op
import sqlalchemy as sa

revision = "20261030_0025"
down_revision = "20261028_0024"
branch_labels = depends_on = None


def upgrade():
    op.create_table("line_capture_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("namespace", sa.String(80), nullable=False),
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("source_event_id", sa.String(64), nullable=False, unique=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("target", sa.String(16)),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("awaiting", sa.String(32)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_line_capture_actor_active", "line_capture_sessions",
                    ["namespace", "line_user_id", "expires_at"])


def downgrade():
    raise RuntimeError("Disable LINE smart capture by rollout; retain unconfirmed state for recovery")
