"""Add lossless legacy backfill targets and task history fields.

Revision ID: 20260927_0005
Revises: 20260926_0004
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260927_0005"
down_revision: Union[str, None] = "20260926_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # `tasks` predates the Alembic chain and may already exist from the
    # transitional create_all bootstrap. CREATE/ALTER IF NOT EXISTS keeps this
    # revision additive for both the current dev-test database and a clean
    # PostgreSQL database created from the migration chain.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id varchar(36) PRIMARY KEY,
            title varchar(500) NOT NULL,
            note text NULL,
            status varchar(20) NOT NULL DEFAULT 'pending',
            priority varchar(10) NOT NULL DEFAULT 'normal',
            due_at timestamptz NULL,
            reminder_at timestamptz NULL,
            project_id varchar(36) NULL,
            source_type varchar(64) NULL,
            source_ref text NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz NULL,
            deleted_at timestamptz NULL
        )
        """
    )
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_type varchar(64) NULL")
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS source_ref text NULL")
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at timestamptz NULL")
    op.execute("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS deleted_at timestamptz NULL")

    op.create_table(
        "checklist_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("is_done", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_checklist_items_task_id_sort_order", "checklist_items", ["task_id", "sort_order"])

    op.create_table(
        "tags",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )
    op.create_table(
        "entity_tags",
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("tag_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("entity_type", "entity_id", "tag_id"),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=64), server_default="notification", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "legacy_attachments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("source_local_path", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "calendar_event_refs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("google_event_id", sa.String(length=255), nullable=False),
        sa.Column("calendar_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_event_id", name="uq_calendar_event_refs_google_event_id"),
    )

    op.create_table(
        "gmail_refs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("gmail_message_id", sa.String(length=255), nullable=False),
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("sender", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("linked_entity_type", sa.String(length=64), nullable=True),
        sa.Column("linked_entity_id", sa.String(length=36), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gmail_message_id", name="uq_gmail_refs_gmail_message_id"),
    )

    op.create_table(
        "legacy_activity_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("result", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "legacy_key_value_state",
        sa.Column("source_table", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("source_table", "key"),
    )

    op.create_table(
        "legacy_migration_rows",
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("source_table", sa.String(length=64), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("row_sha256", sa.String(length=64), nullable=False),
        sa.Column("target_table", sa.String(length=64), nullable=False),
        sa.Column("target_key", sa.Text(), nullable=False),
        sa.Column("migrated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("source_fingerprint", "source_table", "source_key"),
    )


def downgrade() -> None:
    op.drop_table("legacy_migration_rows")
    op.drop_table("legacy_key_value_state")
    op.drop_table("legacy_activity_logs")
    op.drop_table("gmail_refs")
    op.drop_table("calendar_event_refs")
    op.drop_table("legacy_attachments")
    op.drop_table("reminders")
    op.drop_table("entity_tags")
    op.drop_table("tags")
    op.drop_index("ix_checklist_items_task_id_sort_order", table_name="checklist_items")
    op.drop_table("checklist_items")
    op.drop_column("tasks", "deleted_at")
    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "source_ref")
    op.drop_column("tasks", "source_type")
