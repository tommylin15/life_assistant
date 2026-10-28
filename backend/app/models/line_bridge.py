"""LINE OA bindings and captured text drafts; Life PostgreSQL remains the owner."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKeyConstraint, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class LineAccountLink(Base):
    __tablename__ = "line_account_links"
    line_user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audience: Mapped[str] = mapped_column(String(16), primary_key=True)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LineCaptureDraft(Base):
    __tablename__ = "line_capture_drafts"
    message_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    audience: Mapped[str] = mapped_column(String(16), nullable=False)
    line_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["line_user_id", "audience"],
            ["line_account_links.line_user_id", "line_account_links.audience"],
            name="fk_line_capture_link",
        ),
    )
