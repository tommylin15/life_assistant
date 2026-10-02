"""Add provider-agnostic Drive AI enrichment persistence.

Revision ID: 20261002_0009
Revises: 20261001_0008
Create Date: 2026-10-02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261002_0009"
down_revision: str | None = "20261001_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drive_enrichment_settings",
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column(
            "auto_tags_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "note_suggestions_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "allow_document_content",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "max_related_note_suggestions",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_related_note_suggestions BETWEEN 1 AND 20",
            name="ck_drive_enrichment_settings_max_related_notes",
        ),
        sa.PrimaryKeyConstraint("user_sub"),
    )

    op.create_table(
        "drive_document_enrichment_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "suggested_tags_json",
            sa.Text(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'partial', 'failed', 'skipped')",
            name="ck_drive_enrichment_run_status",
        ),
        sa.ForeignKeyConstraint(
            ["drive_document_id"],
            ["drive_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_drive_enrichment_runs_document_created",
        "drive_document_enrichment_runs",
        ["drive_document_id", "created_at"],
    )
    op.create_index(
        "ix_drive_enrichment_runs_cache_lookup",
        "drive_document_enrichment_runs",
        ["drive_document_id", "content_fingerprint", "status"],
    )

    op.create_table(
        "drive_note_link_suggestions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("enrichment_run_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("note_id", sa.String(length=36), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "decision",
            sa.String(length=16),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('pending', 'accepted', 'rejected')",
            name="ck_drive_note_suggestion_decision",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_drive_note_suggestion_confidence",
        ),
        sa.ForeignKeyConstraint(
            ["enrichment_run_id"],
            ["drive_document_enrichment_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["drive_document_id"],
            ["drive_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["notes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "enrichment_run_id",
            "note_id",
            name="uq_drive_note_suggestions_run_note",
        ),
    )
    op.create_index(
        "ix_drive_note_suggestions_document",
        "drive_note_link_suggestions",
        ["drive_document_id"],
    )
    op.create_index(
        "ix_drive_note_suggestions_note",
        "drive_note_link_suggestions",
        ["note_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_drive_note_suggestions_note",
        table_name="drive_note_link_suggestions",
    )
    op.drop_index(
        "ix_drive_note_suggestions_document",
        table_name="drive_note_link_suggestions",
    )
    op.drop_table("drive_note_link_suggestions")
    op.drop_index(
        "ix_drive_enrichment_runs_cache_lookup",
        table_name="drive_document_enrichment_runs",
    )
    op.drop_index(
        "ix_drive_enrichment_runs_document_created",
        table_name="drive_document_enrichment_runs",
    )
    op.drop_table("drive_document_enrichment_runs")
    op.drop_table("drive_enrichment_settings")
