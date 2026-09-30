import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DriveWorkspace(Base):
    __tablename__ = "drive_workspaces"
    __table_args__ = (
        UniqueConstraint(
            "owner_sub",
            "google_folder_id",
            name="uq_drive_workspaces_owner_folder",
        ),
        Index(
            "uq_drive_workspaces_default_per_owner",
            "owner_sub",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    google_folder_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    web_view_link: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DriveDocument(Base):
    __tablename__ = "drive_documents"
    __table_args__ = (
        UniqueConstraint(
            "owner_sub", "google_file_id", name="uq_drive_documents_owner_file"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    google_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    web_view_link: Mapped[str | None] = mapped_column(Text)
    provider_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_metadata_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DriveWorkspaceDocument(Base):
    __tablename__ = "drive_workspace_documents"

    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_workspaces.id"), primary_key=True
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_documents.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProjectDriveDocument(Base):
    __tablename__ = "project_drive_documents"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), primary_key=True
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_documents.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NoteDriveDocument(Base):
    __tablename__ = "note_drive_documents"

    note_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notes.id"), primary_key=True
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_documents.id"), primary_key=True
    )
    relation_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    relation_origin: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DriveAiSettings(Base):
    __tablename__ = "drive_ai_settings"

    owner_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    auto_tags: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    suggest_related_notes: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    allow_content_analysis: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    max_related_notes: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DriveDocumentEnrichmentRun(Base):
    __tablename__ = "drive_document_enrichment_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drive_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_documents.id"), nullable=False, index=True
    )
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    suggested_tags_json: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DriveNoteLinkSuggestion(Base):
    __tablename__ = "drive_note_link_suggestions"
    __table_args__ = (
        UniqueConstraint(
            "enrichment_run_id",
            "note_id",
            name="uq_drive_note_link_suggestions_run_note",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    enrichment_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_document_enrichment_runs.id"), nullable=False
    )
    drive_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("drive_documents.id"), nullable=False, index=True
    )
    note_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("notes.id"), nullable=False, index=True
    )
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
