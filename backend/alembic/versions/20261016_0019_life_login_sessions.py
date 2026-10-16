"""Add revocable Life login sessions without altering existing OAuth grants."""
from alembic import op
import sqlalchemy as sa

revision = "20261016_0019"
down_revision = "20261012_0018"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "life_login_sessions",
        sa.Column("token_sha256", sa.String(length=64), primary_key=True),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=320), nullable=False),
        sa.Column("audience", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("audience IN ('production', 'staging')",
                           name="ck_life_login_sessions_audience"),
    )
    op.create_index("ix_life_login_sessions_user_sub",
                    "life_login_sessions", ["user_sub"])
    op.create_index("ix_life_login_sessions_expires_at",
                    "life_login_sessions", ["expires_at"])


def downgrade():
    raise RuntimeError("Downgrade would revoke all active Life sessions; prohibited")
