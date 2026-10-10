"""Stable activity handoff and account-owned actions; preserves legacy rows."""
from alembic import op
import sqlalchemy as sa

revision = "20261010_0016"
down_revision = "20261010_0015"
branch_labels = depends_on = None


def upgrade():
    op.add_column("curated_activities", sa.Column("handoff_event_key", sa.String(200)))
    op.add_column("curated_activities", sa.Column("content_hash", sa.String(64)))
    op.add_column("curated_activities", sa.Column("parent_event_key", sa.String(200)))
    op.add_column("curated_activities", sa.Column("handoff_details", sa.JSON()))
    op.create_unique_constraint("uq_curated_handoff_event_key", "curated_activities", ["handoff_event_key"])
    op.create_index("ix_curated_activities_parent_event_key", "curated_activities", ["parent_event_key"])
    op.add_column("tasks", sa.Column("user_sub", sa.String(255)))
    op.create_table(
        "curated_personal_actions",
        sa.Column("user_sub", sa.String(255), primary_key=True),
        sa.Column("activity_id", sa.String(64), primary_key=True),
        sa.Column("kind", sa.String(32), primary_key=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("entity_id", sa.String(100)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('save','follow','task','calendar_info','calendar_registration','calendar_confirmed','reminder')", name="ck_curated_action_kind"),
    )


def downgrade():
    raise RuntimeError("No destructive downgrade for activity handoff")
