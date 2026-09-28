from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ExecutionLog(Base):
    __tablename__ = "execution_logs"
    __table_args__ = (
        Index(
            "uq_execution_logs_user_action_type_action_id",
            "user_sub",
            "action_type",
            "action_id",
            unique=True,
            postgresql_where=text("action_id IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
