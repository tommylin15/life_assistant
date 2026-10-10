"""ChatGPT-selected activity pool and individually owned UI/admin policies."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, JSON, Numeric, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CuratedActivity(Base):
    __tablename__ = "curated_activities"
    __table_args__ = (
        Index("ix_curated_activity_date", "starts_on"),
        Index("ix_curated_activity_city", "city"),
    )
    identity_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    occurrence_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(1200))
    city: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(100))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    fee_kind: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    benefit_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    on_site_spending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    importance: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_required: Mapped[bool | None] = mapped_column(Boolean)
    registration_status: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    limited_offer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FeatureRollout(Base):
    __tablename__ = "feature_rollouts"
    feature_key: Mapped[str] = mapped_column(String(60), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    audience: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserUIPreference(Base):
    __tablename__ = "user_ui_preferences"
    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    nav_mode: Mapped[str] = mapped_column(String(12), nullable=False, default="auto")
    pinned: Mapped[list] = mapped_column(JSON, nullable=False)
    more_order: Mapped[list] = mapped_column(JSON, nullable=False)
    home_cards: Mapped[list] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LifeAIPolicy(Base):
    __tablename__ = "life_ai_policy"
    policy_key: Mapped[str] = mapped_column(String(32), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_providers: Mapped[list] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
