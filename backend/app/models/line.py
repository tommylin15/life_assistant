"""LINE identities are secondary, revocable links to existing Life accounts."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class LineBinding(Base):
    __tablename__ = "line_bindings"
    __table_args__ = (UniqueConstraint("namespace", "line_user_id"),
                      UniqueConstraint("namespace", "user_sub"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(80))
    line_user_id: Mapped[str] = mapped_column(String(64))
    user_sub: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str] = mapped_column(String(320))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LineLinkTicket(Base):
    __tablename__ = "line_link_tickets"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(80))
    user_sub: Mapped[str] = mapped_column(String(255), index=True)
    line_user_id: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)


class LineSession(Base):
    __tablename__ = "line_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    binding_id: Mapped[str] = mapped_column(String(36), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class LineEvent(Base):
    __tablename__ = "line_events"
    # Hash(namespace + webhookEventId); payload and reply tokens never enter logs.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(80))
    binding_id: Mapped[str | None] = mapped_column(String(36), index=True)
    user_sub: Mapped[str | None] = mapped_column(String(255), index=True)
    text: Mapped[str] = mapped_column(Text, default="")
    reply: Mapped[list] = mapped_column(JSON, default=list)
    reply_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
