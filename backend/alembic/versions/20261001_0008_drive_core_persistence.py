"""Add core Drive workspace and relationship persistence.

Revision ID: 20261001_0008
Revises: 20260930_0007
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20261001_0008"
down_revision: Union[str, None] = "20260930_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drive_workspaces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("google_folder_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
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
        sa.UniqueConstraint(
            "user_sub",
            "google_folder_id",
            name="uq_drive_workspaces_user_folder",
        ),
    )
    op.create_index(
        "ix_drive_workspaces_user_sub",
        "drive_workspaces",
        ["user_sub"],
    )

    op.create_table(
        "drive_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("google_file_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("web_view_link", sa.Text(), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "user_sub",
            "google_file_id",
            name="uq_drive_documents_user_file",
        ),
    )
    op.create_index(
        "ix_drive_documents_user_sub",
        "drive_documents",
        ["user_sub"],
    )

    op.create_table(
        "drive_workspace_documents",
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["drive_workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["drive_document_id"],
            ["drive_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("workspace_id", "drive_document_id"),
    )

    op.create_table(
        "project_drive_documents",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["drive_document_id"],
            ["drive_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "drive_document_id"),
    )

    op.create_table(
        "note_drive_documents",
        sa.Column("note_id", sa.String(length=36), nullable=False),
        sa.Column("drive_document_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("link_source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relation_type IN ('source_import', 'related')",
            name="ck_note_drive_documents_relation_type",
        ),
        sa.CheckConstraint(
            "link_source IN ('manual', 'ai_accepted', 'import')",
            name="ck_note_drive_documents_link_source",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["notes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["drive_document_id"],
            ["drive_documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("note_id", "drive_document_id"),
    )


def downgrade() -> None:
    op.drop_table("note_drive_documents")
    op.drop_table("project_drive_documents")
    op.drop_table("drive_workspace_documents")
    op.drop_index("ix_drive_documents_user_sub", table_name="drive_documents")
    op.drop_table("drive_documents")
    op.drop_index("ix_drive_workspaces_user_sub", table_name="drive_workspaces")
    op.drop_table("drive_workspaces")
