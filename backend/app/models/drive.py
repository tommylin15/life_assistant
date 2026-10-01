import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DriveWorkspace(Base):
    __tablename__ = "drive_workspaces"
    __table_args__ = (
        UniqueConstraint(
            "user_sub",
            "google_folder_id",
            name="uq_drive_workspaces_user_folder",
        ),
        Index("ix_drive_workspaces_user_sub", "user_sub"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    google_folder_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DriveDocument(Base):
    __tablename__ = "drive_documents"
    __table_args__ = (
        UniqueConstraint(
            "user_sub",
            "google_file_id",
            name="uq_drive_documents_user_file",
        ),
        Index("ix_drive_documents_user_sub", "user_sub"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    google_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    web_view_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DriveWorkspaceDocument(Base):
    __tablename__ = "drive_workspace_documents"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ProjectDriveDocument(Base):
    __tablename__ = "project_drive_documents"

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class NoteDriveDocument(Base):
    __tablename__ = "note_drive_documents"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('source_import', 'related')",
            name="ck_note_drive_documents_relation_type",
        ),
        CheckConstraint(
            "link_source IN ('manual', 'ai_accepted', 'import')",
            name="ck_note_drive_documents_link_source",
        ),
    )

    note_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    link_source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
