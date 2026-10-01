"""Add Drive project knowledge integration tables.

Revision ID: 20260930_0008
Revises: 20260930_0007
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260930_0008"
down_revision: Union[str, None] = "20260930_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drive_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_sub", sa.String(length=255), nullable=False),
        sa.Column("google_folder_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("web_view_link", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_sub",
            "google_folder_id",
            name="uq_drive_workspaces_owner_folder",
        ),
    )
    op.create_index("ix_drive_workspaces_owner_sub", "drive_workspaces", ["owner_sub"], unique=False)
    op.create_index(
        "uq_drive_workspaces_default_per_owner",
        "drive_workspaces",
        ["owner_sub"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.create_table(
        "drive_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_sub", sa.String(length=255), nullable=False),
        sa.Column("google_file_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("web_view_link", sa.Text(), nullable=True),
        sa.Column("provider_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_metadata_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_sub",
            "google_file_id",
            name="uq_drive_documents_owner_file",
        ),
    )
    op.create_index("ix_drive_documents_owner_sub", "drive_documents", ["owner_sub"], unique=False)

    op.create_table(
        "drive_workspace_documents",
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["drive_workspaces.id"]),
        sa.ForeignKeyConstraint(["drive_document_id"], ["drive_documents.id"]),
        sa.PrimaryKeyConstraint("workspace_id", "drive_document_id"),
    )

    op.create_table(
        "project_drive_documents",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["drive_document_id"], ["drive_documents.id"]),
        sa.PrimaryKeyConstraint("project_id", "drive_document_id"),
    )

    op.create_table(
        "note_drive_documents",
        sa.Column("note_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("relation_origin", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
        sa.ForeignKeyConstraint(["drive_document_id"], ["drive_documents.id"]),
        sa.PrimaryKeyConstraint("note_id", "drive_document_id", "relation_type"),
    )

    op.create_table(
        "drive_ai_settings",
        sa.Column("owner_sub", sa.String(length=255), nullable=False),
        sa.Column("auto_tags", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("suggest_related_notes", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("allow_content_analysis", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("max_related_notes", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("owner_sub"),
    )

    op.create_table(
        "drive_document_enrichment_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_sub", sa.String(length=255), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("suggested_tags_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["drive_document_id"], ["drive_documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drive_document_enrichment_runs_owner_sub", "drive_document_enrichment_runs", ["owner_sub"], unique=False)
    op.create_index("ix_drive_document_enrichment_runs_drive_document_id", "drive_document_enrichment_runs", ["drive_document_id"], unique=False)

    op.create_table(
        "drive_note_link_suggestions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_sub", sa.String(length=255), nullable=False),
        sa.Column("enrichment_run_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("note_id", sa.String(length=36), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["enrichment_run_id"], ["drive_document_enrichment_runs.id"]),
        sa.ForeignKeyConstraint(["drive_document_id"], ["drive_documents.id"]),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "enrichment_run_id",
            "note_id",
            name="uq_drive_note_link_suggestions_run_note",
        ),
    )
    op.create_index("ix_drive_note_link_suggestions_owner_sub", "drive_note_link_suggestions", ["owner_sub"], unique=False)
    op.create_index("ix_drive_note_link_suggestions_drive_document_id", "drive_note_link_suggestions", ["drive_document_id"], unique=False)
    op.create_index("ix_drive_note_link_suggestions_note_id", "drive_note_link_suggestions", ["note_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_drive_note_link_suggestions_note_id", table_name="drive_note_link_suggestions")
    op.drop_index("ix_drive_note_link_suggestions_drive_document_id", table_name="drive_note_link_suggestions")
    op.drop_index("ix_drive_note_link_suggestions_owner_sub", table_name="drive_note_link_suggestions")
    op.drop_table("drive_note_link_suggestions")
    op.drop_index("ix_drive_document_enrichment_runs_drive_document_id", table_name="drive_document_enrichment_runs")
    op.drop_index("ix_drive_document_enrichment_runs_owner_sub", table_name="drive_document_enrichment_runs")
    op.drop_table("drive_document_enrichment_runs")
    op.drop_table("drive_ai_settings")
    op.drop_table("note_drive_documents")
    op.drop_table("project_drive_documents")
    op.drop_table("drive_workspace_documents")
    op.drop_index("ix_drive_documents_owner_sub", table_name="drive_documents")
    op.drop_table("drive_documents")
    op.drop_index("uq_drive_workspaces_default_per_owner", table_name="drive_workspaces")
    op.drop_index("ix_drive_workspaces_owner_sub", table_name="drive_workspaces")
    op.drop_table("drive_workspaces")
