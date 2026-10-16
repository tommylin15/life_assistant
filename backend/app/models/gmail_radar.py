"""Per-user, explicitly requested Gmail radar results (no message body storage)."""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class GmailRadarItem(Base):
    __tablename__ = "gmail_radar_items"
    __table_args__ = (
        UniqueConstraint("user_sub", "gmail_message_id", name="uq_gmail_radar_user_message"),
        Index("ix_gmail_radar_user_status", "user_sub", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    sender: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    linked_target: Mapped[str | None] = mapped_column(String(16), nullable=True)
    linked_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GmailRadarScanState(Base):
    __tablename__ = "gmail_radar_scan_states"
    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scan_kind: Mapped[str] = mapped_column(String(20), nullable=False, default="quick")
    three_day_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    three_day_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    three_day_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class GmailRadarSeen(Base):
    """Owner-scoped message-ID-only dedup cache; no bodies or metadata."""
    __tablename__ = "gmail_radar_seen"
    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    gmail_message_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
