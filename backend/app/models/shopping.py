import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, false, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    list_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shopping_lists.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
