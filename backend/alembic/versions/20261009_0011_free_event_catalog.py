"""Add public free-event catalog. Revision 20261009_0011, parent 20261007_0010.

No existing table is modified; no source adapter or account action is enabled.
"""
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "20261009_0011"
down_revision: str | None = "20261007_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "free_event_sources",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("tier", sa.String(24), nullable=False),
        sa.Column("reference_url", sa.Text(), nullable=False),
        sa.Column("license_evidence_url", sa.Text()),
        sa.Column("access_review", sa.String(64), nullable=False),
        sa.Column("fetch_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expected_interval_hours", sa.Integer(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_kind", sa.String(80)),
        sa.CheckConstraint("tier IN ('official_dataset', 'official_api', 'official_catalog', 'aggregator')", name="ck_free_event_source_tier"),
        sa.CheckConstraint("expected_interval_hours BETWEEN 1 AND 168", name="ck_free_event_source_interval"),
    )
    op.create_table(
        "free_event_organizers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_key", sa.String(64), unique=True, nullable=False),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("official_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "free_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("canonical_key", sa.String(64), unique=True, nullable=False),
        sa.Column("source_id", sa.String(80), sa.ForeignKey("free_event_sources.id"), nullable=False),
        sa.Column("organizer_id", sa.String(36), sa.ForeignKey("free_event_organizers.id")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.String(600)),
        sa.Column("category", sa.String(80)),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("official_url", sa.Text()),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("verification_status", sa.String(16), nullable=False, server_default=sa.text("'unverified'")),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("verification_status IN ('unverified', 'verified', 'stale', 'invalid')",
                           name="ck_free_event_verification_status"),
    )
    op.create_index("ix_free_events_status_checked", "free_events", ["verification_status", "last_verified_at"])
    op.create_index("ix_free_events_source", "free_events", ["source_id"])

    op.create_table(
        "free_event_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("free_events.id"), nullable=False),
        sa.Column("session_key", sa.String(128), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("starts_on", sa.Date()),
        sa.Column("ends_on_exclusive", sa.Date()),
        sa.Column("timezone_name", sa.String(80)),
        sa.Column("city", sa.String(100)),
        sa.Column("venue", sa.String(300)),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("event_id", "session_key", name="uq_free_event_session_key"),
        sa.CheckConstraint("starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
                           name="ck_free_event_session_time_order"),
        sa.CheckConstraint("starts_on IS NULL OR ends_on_exclusive IS NULL OR ends_on_exclusive > starts_on",
                           name="ck_free_event_session_date_order"),
        sa.CheckConstraint("(starts_on IS NULL AND ends_on_exclusive IS NULL) OR "
                           "(starts_at IS NULL AND ends_at IS NULL)",
                           name="ck_free_event_session_date_time_exclusive"),
    )
    op.create_index("ix_free_event_sessions_starts_at", "free_event_sessions", ["starts_at"])
    op.create_index("ix_free_event_sessions_starts_on", "free_event_sessions", ["starts_on"])

    op.create_table(
        "free_event_registration_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("free_event_sessions.id"), nullable=False),
        sa.Column("opportunity_key", sa.String(128), nullable=False),
        sa.Column("registration_url", sa.Text()),
        sa.Column("registration_opens_at", sa.DateTime(timezone=True)),
        sa.Column("registration_closes_at", sa.DateTime(timezone=True)),
        sa.Column("fee_kind", sa.String(20), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("fee_amount", sa.Numeric(12, 2)),
        sa.Column("fee_currency", sa.String(3)),
        sa.Column("eligibility_note", sa.String(400)),
        sa.Column("registration_status", sa.String(24), nullable=False, server_default=sa.text("'unannounced'")),
        sa.Column("official_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("session_id", "opportunity_key", name="uq_free_event_registration_key"),
        sa.CheckConstraint("fee_kind IN ('free', 'conditional_free', 'paid', 'unknown')",
                           name="ck_free_event_registration_fee_kind"),
        sa.CheckConstraint("registration_status IN ('unannounced', 'upcoming', 'open', 'full', "
                           "'waitlist_available', 'closed', 'cancelled', 'event_ended')",
                           name="ck_free_event_registration_status"),
        sa.CheckConstraint("registration_opens_at IS NULL OR registration_closes_at IS NULL OR "
                           "registration_closes_at > registration_opens_at",
                           name="ck_free_event_registration_window"),
        sa.CheckConstraint("fee_amount IS NULL OR fee_amount >= 0",
                           name="ck_free_event_registration_nonnegative_fee"),
    )
    op.create_index("ix_free_event_registration_opens", "free_event_registration_opportunities",
                    ["registration_opens_at"])

    op.create_table(
        "free_event_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), sa.ForeignKey("free_events.id"), nullable=False),
        sa.Column("source_id", sa.String(80), sa.ForeignKey("free_event_sources.id"), nullable=False),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("evidence_excerpt", sa.String(320)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", "source_id", "field_name", "content_fingerprint",
                            name="uq_free_event_evidence_field_fingerprint"),
    )
    op.create_index("ix_free_event_evidence_observed", "free_event_evidence", ["observed_at"])


def downgrade() -> None:
    # Explicit controlled dev/test downgrade only; never automated on production.
    op.drop_index("ix_free_event_evidence_observed", table_name="free_event_evidence")
    op.drop_table("free_event_evidence")
    op.drop_index("ix_free_event_registration_opens", table_name="free_event_registration_opportunities")
    op.drop_table("free_event_registration_opportunities")
    op.drop_index("ix_free_event_sessions_starts_on", table_name="free_event_sessions")
    op.drop_index("ix_free_event_sessions_starts_at", table_name="free_event_sessions")
    op.drop_table("free_event_sessions")
    op.drop_index("ix_free_events_source", table_name="free_events")
    op.drop_index("ix_free_events_status_checked", table_name="free_events")
    op.drop_table("free_events")
    op.drop_table("free_event_organizers")
    op.drop_table("free_event_sources")
