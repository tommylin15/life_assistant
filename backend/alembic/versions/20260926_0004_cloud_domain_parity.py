"""Add cloud parity tables for notes, habits, shopping, and templates.

Revision ID: 20260926_0004
Revises: 20260925_0003
Create Date: 2026-09-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260926_0004"
down_revision: Union[str, None] = "20260925_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "note_links",
        sa.Column("source_note_id", sa.String(length=36), nullable=False),
        sa.Column("target_note_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["source_note_id"], ["notes.id"]),
        sa.ForeignKeyConstraint(["target_note_id"], ["notes.id"]),
        sa.PrimaryKeyConstraint("source_note_id", "target_note_id"),
    )
    op.create_table(
        "habits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("recurrence_rule", sa.Text(), nullable=False),
        sa.Column("reminder_time", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "habit_completions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("habit_id", sa.String(length=36), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_habit_completions_habit_id_completed_at",
        "habit_completions",
        ["habit_id", sa.text("completed_at DESC")],
    )
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "shopping_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("list_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("is_done", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["list_id"], ["shopping_lists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("template_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("templates")
    op.drop_table("shopping_items")
    op.drop_table("shopping_lists")
    op.drop_index("ix_habit_completions_habit_id_completed_at", table_name="habit_completions")
    op.drop_table("habit_completions")
    op.drop_table("habits")
    op.drop_table("note_links")
    op.drop_table("notes")
