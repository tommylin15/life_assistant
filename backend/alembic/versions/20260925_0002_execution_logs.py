"""Add execution audit log.

Revision ID: 20260925_0002
Revises: 20260925_0001
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0002"
down_revision: Union[str, None] = "20260925_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=True),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=64), nullable=True),
        sa.Column("error_category", sa.String(length=128), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_logs_request_id", "execution_logs", ["request_id"])
    op.create_index("ix_execution_logs_action_id", "execution_logs", ["action_id"])
    op.create_index("ix_execution_logs_user_sub", "execution_logs", ["user_sub"])
    op.create_index("ix_execution_logs_action_type", "execution_logs", ["action_type"])
    op.create_index("ix_execution_logs_status", "execution_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_execution_logs_status", table_name="execution_logs")
    op.drop_index("ix_execution_logs_action_type", table_name="execution_logs")
    op.drop_index("ix_execution_logs_user_sub", table_name="execution_logs")
    op.drop_index("ix_execution_logs_action_id", table_name="execution_logs")
    op.drop_index("ix_execution_logs_request_id", table_name="execution_logs")
    op.drop_table("execution_logs")
