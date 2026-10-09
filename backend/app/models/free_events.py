"""Minimal public free-event catalog; no user actions, scraping or API keys."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint, false, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _id() -> str:
    return str(uuid.uuid4())


class FreeEventSource(Base):
    __tablename__ = "free_event_sources"
    __table_args__ = (
        CheckConstraint(
            "tier IN ('official_dataset', 'official_api', 'official_catalog', 'aggregator')",
            name="ck_free_event_source_tier",
        ),
        CheckConstraint(
            "NOT fetch_enabled OR (access_review = 'reviewed_with_evidence' "
            "AND license_evidence_url IS NOT NULL)",
            name="ck_free_event_source_fetch_approval",
        ),
        CheckConstraint("expected_interval_hours BETWEEN 1 AND 168",
                        name="ck_free_event_source_interval"),
    )
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tier: Mapped[str] = mapped_column(String(24), nullable=False)
    reference_url: Mapped[str] = mapped_column(Text, nullable=False)
    license_evidence_url: Mapped[str | None] = mapped_column(Text)
    access_review: Mapped[str] = mapped_column(String(64), nullable=False)
    fetch_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)
    expected_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_kind: Mapped[str | None] = mapped_column(String(80))


class FreeEventOrganizer(Base):
    __tablename__ = "free_event_organizers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    canonical_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    official_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FreeEvent(Base):
    __tablename__ = "free_events"
    __table_args__ = (
        Index("ix_free_events_status_checked", "verification_status", "last_verified_at"),
        Index("ix_free_events_source", "source_id"),
        CheckConstraint(
            "verification_status IN ('unverified', 'verified', 'stale', 'invalid')",
            name="ck_free_event_verification_status",
        ),
        CheckConstraint(
            "verification_status <> 'verified' OR "
            "(official_url IS NOT NULL AND last_verified_at IS NOT NULL)",
            name="ck_free_event_verified_provenance",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    canonical_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(80), ForeignKey("free_event_sources.id"), nullable=False)
    organizer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("free_event_organizers.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(600))
    category: Mapped[str | None] = mapped_column(String(80))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    official_url: Mapped[str | None] = mapped_column(Text)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'unverified'"))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class FreeEventSession(Base):
    __tablename__ = "free_event_sessions"
    __table_args__ = (
        UniqueConstraint("event_id", "session_key", name="uq_free_event_session_key"),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
            name="ck_free_event_session_time_order",
        ),
        CheckConstraint(
            "starts_on IS NULL OR ends_on_exclusive IS NULL OR ends_on_exclusive > starts_on",
            name="ck_free_event_session_date_order",
        ),
        CheckConstraint(
            "(starts_on IS NULL AND ends_on_exclusive IS NULL) OR "
            "(starts_at IS NULL AND ends_at IS NULL)",
            name="ck_free_event_session_date_time_exclusive",
        ),
        Index("ix_free_event_sessions_starts_at", "starts_at"),
        Index("ix_free_event_sessions_starts_on", "starts_on"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("free_events.id"), nullable=False)
    session_key: Mapped[str] = mapped_column(String(128), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    starts_on: Mapped[date | None] = mapped_column(Date())
    ends_on_exclusive: Mapped[date | None] = mapped_column(Date())
    timezone_name: Mapped[str | None] = mapped_column(String(80))
    city: Mapped[str | None] = mapped_column(String(100))
    venue: Mapped[str | None] = mapped_column(String(300))
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)


class FreeEventRegistrationOpportunity(Base):
    __tablename__ = "free_event_registration_opportunities"
    __table_args__ = (
        UniqueConstraint("session_id", "opportunity_key", name="uq_free_event_registration_key"),
        CheckConstraint(
            "fee_kind IN ('free', 'conditional_free', 'paid', 'unknown')",
            name="ck_free_event_registration_fee_kind",
        ),
        CheckConstraint(
            "registration_status IN ('unannounced', 'upcoming', 'open', 'full', "
            "'waitlist_available', 'closed', 'cancelled', 'event_ended')",
            name="ck_free_event_registration_status",
        ),
        CheckConstraint(
            "registration_opens_at IS NULL OR registration_closes_at IS NULL "
            "OR registration_closes_at > registration_opens_at",
            name="ck_free_event_registration_window",
        ),
        CheckConstraint(
            "fee_amount IS NULL OR fee_amount >= 0",
            name="ck_free_event_registration_nonnegative_fee",
        ),
        CheckConstraint(
            "fee_kind <> 'free' OR fee_amount IS NULL OR fee_amount = 0",
            name="ck_free_event_registration_free_fee",
        ),
        CheckConstraint(
            "NOT official_verified OR fee_kind NOT IN ('free', 'conditional_free') "
            "OR registration_url IS NOT NULL",
            name="ck_free_event_registration_official_evidence",
        ),
        Index("ix_free_event_registration_opens", "registration_opens_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("free_event_sessions.id"), nullable=False)
    opportunity_key: Mapped[str] = mapped_column(String(128), nullable=False)
    registration_url: Mapped[str | None] = mapped_column(Text)
    registration_opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    registration_closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fee_kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'unknown'"))
    fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    fee_currency: Mapped[str | None] = mapped_column(String(3))
    eligibility_note: Mapped[str | None] = mapped_column(String(400))
    registration_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'unannounced'"))
    official_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FreeEventEvidence(Base):
    __tablename__ = "free_event_evidence"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "source_id", "field_name", "content_fingerprint",
            name="uq_free_event_evidence_field_fingerprint",
        ),
        Index("ix_free_event_evidence_observed", "observed_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("free_events.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(80), ForeignKey("free_event_sources.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_excerpt: Mapped[str | None] = mapped_column(String(320))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FreeEventIngestionLease(Base):
    """One durable source claim; never stores credentials or raw source payloads."""
    __tablename__ = "free_event_ingestion_leases"
    __table_args__ = (
        CheckConstraint("consecutive_failures >= 0",
                        name="ck_free_event_lease_nonnegative_failures"),
    )
    source_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("free_event_sources.id"), primary_key=True,
    )
    lease_token: Mapped[str] = mapped_column(String(64), nullable=False)
    lease_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), default=0,
    )
    last_error_kind: Mapped[str | None] = mapped_column(String(40))
