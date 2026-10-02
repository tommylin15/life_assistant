import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
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


class DriveEnrichmentSettings(Base):
    __tablename__ = "drive_enrichment_settings"
    __table_args__ = (
        CheckConstraint(
            "max_related_note_suggestions BETWEEN 1 AND 20",
            name="ck_drive_enrichment_settings_max_related_notes",
        ),
    )

    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    auto_tags_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    note_suggestions_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )
    allow_document_content: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )
    max_related_note_suggestions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default=text("5"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DriveDocumentEnrichmentRun(Base):
    __tablename__ = "drive_document_enrichment_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('succeeded', 'partial', 'failed', 'skipped')",
            name="ck_drive_enrichment_run_status",
        ),
        Index(
            "ix_drive_enrichment_runs_document_created",
            "drive_document_id",
            "created_at",
        ),
        Index(
            "ix_drive_enrichment_runs_cache_lookup",
            "drive_document_id",
            "content_fingerprint",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    suggested_tags_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        server_default=text("'[]'"),
    )
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class DriveNoteLinkSuggestion(Base):
    __tablename__ = "drive_note_link_suggestions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('pending', 'accepted', 'rejected')",
            name="ck_drive_note_suggestion_decision",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_drive_note_suggestion_confidence",
        ),
        UniqueConstraint(
            "enrichment_run_id",
            "note_id",
            name="uq_drive_note_suggestions_run_note",
        ),
        Index("ix_drive_note_suggestions_document", "drive_document_id"),
        Index("ix_drive_note_suggestions_note", "note_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    enrichment_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_document_enrichment_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drive_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    note_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
