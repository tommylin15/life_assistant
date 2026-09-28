"""Add action-id idempotency metadata to execution logs.

Revision ID: 20260928_0006
Revises: 20260927_0005
Create Date: 2026-09-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260928_0006"
down_revision: Union[str, None] = "20260927_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "execution_logs",
        sa.Column("request_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "uq_execution_logs_user_action_type_action_id",
        "execution_logs",
        ["user_sub", "action_type", "action_id"],
        unique=True,
        postgresql_where=sa.text("action_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_execution_logs_user_action_type_action_id",
        table_name="execution_logs",
    )
    op.drop_column("execution_logs", "request_hash")
