"""Fail-closed public catalog query. Not an availability checker or auto-booking."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.free_events import (
    FreeEvent, FreeEventRegistrationOpportunity, FreeEventSession, FreeEventSource,
)
from app.models.free_event_discovery_schemas import FreeEventOpportunityCard


def verified_catalog_query(*, now: datetime, limit: int, offset: int):
    today = now.astimezone(ZoneInfo("Asia/Taipei")).date()
    r = FreeEventRegistrationOpportunity
    s = FreeEventSession
    e = FreeEvent
    source = FreeEventSource
    return (
        select(e, s, r)
        .join(s, s.event_id == e.id)
        .join(r, r.session_id == s.id)
        .join(source, source.id == e.source_id)
        .where(
            e.verification_status == "verified",
            e.last_verified_at.is_not(None),
            e.official_url.is_not(None),
            source.fetch_enabled.is_(True),
            source.access_review == "reviewed_with_evidence",
            source.license_evidence_url.is_not(None),
            s.is_cancelled.is_(False),
            r.official_verified.is_(True),
            r.last_verified_at.is_not(None),
            r.registration_url.is_not(None),
            r.fee_kind.in_(["free", "conditional_free"]),
            r.registration_status.notin_(["cancelled", "closed", "event_ended", "full"]),
            or_(
                and_(s.ends_at.is_not(None), s.ends_at >= now),
                and_(s.starts_at.is_not(None), s.starts_at >= now),
                and_(s.ends_on_exclusive.is_not(None), s.ends_on_exclusive > today),
                and_(s.starts_on.is_not(None), s.starts_on >= today),
            ),
        )
        .order_by(s.starts_on.asc().nulls_last(),
                  s.starts_at.asc().nulls_last(), e.id, s.id, r.id)
        .limit(limit).offset(offset)
    )


def as_verified_card(event, session, registration, *, now: datetime) -> FreeEventOpportunityCard:
    """Even published 'open' states require verified explicit time boundaries."""
    opening = registration.registration_opens_at
    closing = registration.registration_closes_at
    window_open = (
        registration.registration_status == "open"
        and opening is not None and closing is not None
        and opening.tzinfo is not None and closing.tzinfo is not None
        and opening <= now < closing
    )
    verified_at = registration.last_verified_at
    if (verified_at is None or not event.official_url
            or not registration.registration_url):
        raise ValueError("free-event card requires official evidence")
    return FreeEventOpportunityCard(
        event_id=event.id,
        session_id=session.id,
        opportunity_id=registration.id,
        title=event.title,
        summary=event.summary,
        category=event.category,
        city=session.city,
        venue=session.venue,
        starts_at=session.starts_at,
        ends_at=session.ends_at,
        starts_on=session.starts_on,
        ends_on_exclusive=session.ends_on_exclusive,
        timezone_name=session.timezone_name,
        fee_kind=registration.fee_kind,
        fee_amount=registration.fee_amount,
        fee_currency=registration.fee_currency,
        eligibility_note=registration.eligibility_note,
        official_url=event.official_url,
        registration_url=registration.registration_url,
        registration_opens_at=opening,
        registration_closes_at=closing,
        registration_status=registration.registration_status,
        window_confirmed_open=bool(window_open),
        verified_at=verified_at,
    )


async def list_verified_public_events(
    db: AsyncSession, *, limit: int = 20, offset: int = 0,
    now: datetime | None = None,
) -> list[FreeEventOpportunityCard]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware now required")
    if not (1 <= limit <= 50) or not (0 <= offset <= 5000):
        raise ValueError("invalid bounded pagination")
    result = await db.execute(verified_catalog_query(now=now, limit=limit, offset=offset))
    return [as_verified_card(event, session, registration, now=now)
            for event, session, registration in result.all()]
