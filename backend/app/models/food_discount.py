"""Independent Taipei/New Taipei 41-district food discount pool (V0.5.2 / V1.3.2)."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FoodDiscount(Base):
    __tablename__ = "food_discounts"
    __table_args__ = (
        Index("ix_food_discounts_visibility", "visibility_status", "claim_status"),
        Index("ix_food_discounts_city_district", "city", "district"),
        Index("ix_food_discounts_category", "category"),
    )

    candidate_key: Mapped[str] = mapped_column(String(200), primary_key=True)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    city: Mapped[str | None] = mapped_column(String(50))
    district: Mapped[str | None] = mapped_column(String(100))
    merchant: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    offer_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    offer_type: Mapped[str | None] = mapped_column(String(100))
    nominal_discount: Mapped[str | None] = mapped_column(String(120))
    fixed_discount_ntd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    original_price_ntd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    offer_price_ntd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    period_text: Mapped[str | None] = mapped_column(String(400))
    address: Mapped[str | None] = mapped_column(String(600))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1200))
    claim_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="COLLECTED_SOURCE_CLAIM"
    )
    visibility_status: Mapped[str] = mapped_column(
        String(64), nullable=False, default="VISIBLE_SOURCE_ONLY"
    )
    first_seen_on: Mapped[date | None] = mapped_column(Date)
    claim_deadline_on: Mapped[date | None] = mapped_column(Date)
    redemption_ends_on: Mapped[date | None] = mapped_column(Date)
    offer_ends_on: Mapped[date | None] = mapped_column(Date)
    last_positive_on: Mapped[date | None] = mapped_column(Date)
    next_refresh_on: Mapped[date | None] = mapped_column(Date)
    date_basis: Mapped[str | None] = mapped_column(String(64))
    disclosure: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        default="公開來源宣稱，未逐項核實，不保證到店可使用",
    )
    details: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
