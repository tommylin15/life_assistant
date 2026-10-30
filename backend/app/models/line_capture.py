"""Scoped, short-lived LINE conversation state, never authoritative Life data."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, JSON, String, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class LineCapture(Base):
    __tablename__ = "line_capture_sessions"
    __table_args__ = (Index("ix_line_capture_actor_active", "namespace", "line_user_id", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    line_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str | None] = mapped_column(String(16))
    fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    awaiting: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
