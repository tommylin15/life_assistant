import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, desc, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    recurrence_rule: Mapped[str] = mapped_column(Text, nullable=False)
    reminder_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    __table_args__ = (
        Index(
            "ix_habit_completions_habit_id_completed_at",
            "habit_id",
            desc("completed_at"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    habit_id: Mapped[str] = mapped_column(String(36), ForeignKey("habits.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
