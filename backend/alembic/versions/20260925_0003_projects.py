"""Add projects table.

Revision ID: 20260925_0003
Revises: 20260925_0002
Create Date: 2026-09-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0003"
down_revision: Union[str, None] = "20260925_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_name", "projects", ["name"])


def downgrade() -> None:
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")
