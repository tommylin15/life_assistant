"""Add LINE account links, sessions and durable drafts without altering Life data."""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0024"
down_revision = "20261028_0023"
branch_labels = depends_on = None


def upgrade():
    op.create_table("line_bindings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("namespace", sa.String(80), nullable=False),
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(320), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("namespace", "line_user_id"),
        sa.UniqueConstraint("namespace", "user_sub"))
    op.create_table("line_link_tickets",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("namespace", sa.String(80), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False, index=True),
        sa.Column("line_user_id", sa.String(64)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("consumed", sa.Boolean(), nullable=False))
    op.create_table("line_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("binding_id", sa.String(36), nullable=False, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True))
    op.create_table("line_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("namespace", sa.String(80), nullable=False),
        sa.Column("binding_id", sa.String(36), index=True),
        sa.Column("user_sub", sa.String(255), index=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("reply", sa.JSON(), nullable=False),
        sa.Column("reply_sent", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True))


def downgrade():
    raise RuntimeError("Disable LINE via configuration; retain user links/drafts on rollback")
