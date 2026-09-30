"""Add PostgreSQL full-text search index for notes.

Revision ID: 20260930_0007
Revises: 20260928_0006
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260930_0007"
down_revision: Union[str, None] = "20260928_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "ix_notes_full_text_search"


def upgrade() -> None:
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS {INDEX_NAME}
        ON notes
        USING GIN (
            to_tsvector(
                'simple'::regconfig,
                coalesce(title, '') || ' ' || coalesce(body, '')
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notes_full_text_search")
