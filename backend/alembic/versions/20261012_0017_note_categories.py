"""Add a nullable category to notes without modifying existing note content."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0017"
down_revision = "20261010_0016"
branch_labels = depends_on = None


def upgrade():
    op.add_column("notes", sa.Column("category", sa.String(80), nullable=True))
    op.create_index("ix_notes_category", "notes", ["category"])


def downgrade():
    raise RuntimeError("No destructive downgrade for note categories")
