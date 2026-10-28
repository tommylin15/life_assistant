"""Add LINE OA per-account bindings and replay-safe capture drafts.

Revision ID: 20261028_0023
Revises: 20261019_0022
No existing user records are modified.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261028_0023"
down_revision = "20261019_0022"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "line_account_links",
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("audience", sa.String(16), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("line_user_id", "audience"),
        sa.CheckConstraint("audience IN ('production', 'staging')", name="ck_line_account_audience"),
    )
    op.create_index("ix_line_account_links_user_sub", "line_account_links", ["user_sub"])
    op.create_table(
        "line_capture_drafts",
        sa.Column("message_id", sa.String(128), primary_key=True),
        sa.Column("audience", sa.String(16), nullable=False),
        sa.Column("line_user_id", sa.String(64), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["line_user_id", "audience"],
            ["line_account_links.line_user_id", "line_account_links.audience"],
            name="fk_line_capture_link",
        ),
    )
    op.create_index("ix_line_capture_drafts_user_sub", "line_capture_drafts", ["user_sub"])


def downgrade():
    raise RuntimeError("LINE drafts contain user records; destructive downgrade requires explicit approval")
