"""Add nullable tenant ownership; preserve legacy rows without guessing Owner sub."""
from alembic import op
import sqlalchemy as sa

revision = "20261012_0018"
down_revision = "20261012_0017"
branch_labels = depends_on = None


def upgrade():
    for table in ("notes", "projects", "habits", "shopping_lists"):
        op.add_column(table, sa.Column("user_sub", sa.String(255), nullable=True))
        op.create_index(f"ix_{table}_user_sub", table, ["user_sub"])


def downgrade():
    raise RuntimeError("Ownership downgrade would discard tenant identity; prohibited")
