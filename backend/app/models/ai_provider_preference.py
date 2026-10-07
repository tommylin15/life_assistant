from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AIProviderPreference(Base):
    """Operational last-known-good model preference for external AI providers."""

    __tablename__ = "ai_provider_preferences"

    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    preferred_model: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
