"""PostgreSQL-only transactional M1 ingestion, not exposed as an API or a job.

Requires an explicitly approved FreeEventSource record and migration 0011.
No raw HTML, user actions, network calls, AI calls, or automatic publication.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import uuid

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.free_events import (
    FreeEvent, FreeEventEvidence, FreeEventOrganizer,
    FreeEventRegistrationOpportunity, FreeEventSession, FreeEventSource,
)
from app.services.free_events_normalization import (
    EventCandidate, canonical_event_key, meaningful_fingerprint,
)


class FreeEventSourceNotApproved(PermissionError):
    """The requested source cannot mutate the public event catalog."""


def _uuid() -> str:
    return str(uuid.uuid4())


def _organizer_key(candidate: EventCandidate) -> str:
    if candidate.organizer_url and candidate.official_verified:
        basis = "verified-organizer-url:" + candidate.organizer_url
    else:
        basis = "source-scoped-organizer:" + candidate.source_id + ":" + (
            candidate.organizer_name or ""
        ).strip().casefold()
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _event_upsert(candidate: EventCandidate, fingerprint: str):
    """Generate an atomic ON CONFLICT statement that invalidates changed verification."""
    incoming = pg_insert(FreeEvent).values(
        id=_uuid(),
        canonical_key=canonical_event_key(candidate),
        source_id=candidate.source_id,
        organizer_id=None,
        title=candidate.title,
        summary=candidate.summary,
        category=candidate.category,
        source_url=candidate.source_url,
        official_url=candidate.official_url,
        content_fingerprint=fingerprint,
        verification_status="unverified",
    )
    statement = incoming.on_conflict_do_update(
        index_elements=[FreeEvent.canonical_key],
        set_={
            "title": incoming.excluded.title,
            "summary": incoming.excluded.summary,
            "category": incoming.excluded.category,
            "source_url": incoming.excluded.source_url,
            "official_url": incoming.excluded.official_url,
            "content_fingerprint": incoming.excluded.content_fingerprint,
            "verification_status": case(
                (FreeEvent.content_fingerprint == incoming.excluded.content_fingerprint,
                 FreeEvent.verification_status),
                (FreeEvent.verification_status.in_(["verified", "stale"]), "stale"),
                else_="unverified",
            ),
            "updated_at": datetime.now(timezone.utc),
        },
    )
    return statement.returning(FreeEvent.id)


async def ingest_approved_candidate(
    db: AsyncSession,
    candidate: EventCandidate,
    *,
    observed_at: datetime,
) -> dict[str, object]:
    """Idempotent bounded ingestion of an approved public source into 0011 tables.

    Caller owns a fresh AsyncSession and must have obtained an authorized,
    bounded record. This function does not verify rights merely from a URL.
    """
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be offset-aware")
    if observed_at > datetime.now(timezone.utc):
        raise ValueError("future observation cannot be persisted")
    if len(candidate.sessions) > 100 or sum(
        len(s.opportunities) for s in candidate.sessions
    ) > 500:
        raise ValueError("bounded ingestion limit exceeded")
    fingerprint = meaningful_fingerprint(candidate)

    async with db.begin():
        source_row = await db.execute(
            select(FreeEventSource)
            .where(FreeEventSource.id == candidate.source_id)
            .with_for_update()
        )
        source = source_row.scalar_one_or_none()
        if (source is None or not source.fetch_enabled
                or source.access_review != "reviewed_with_evidence"
                or not source.license_evidence_url):
            raise FreeEventSourceNotApproved("event source approval required")

        organizer_id = None
        if candidate.organizer_name:
            key = _organizer_key(candidate)
            org_insert = pg_insert(FreeEventOrganizer).values(
                id=_uuid(),
                canonical_key=key,
                display_name=candidate.organizer_name,
                official_url=(
                    candidate.organizer_url if candidate.official_verified else None
                ),
            )
            org_insert = org_insert.on_conflict_do_update(
                index_elements=[FreeEventOrganizer.canonical_key],
                set_={"display_name": org_insert.excluded.display_name},
            ).returning(FreeEventOrganizer.id)
            organizer_id = (await db.execute(org_insert)).scalar_one()

        event_id = (await db.execute(_event_upsert(candidate, fingerprint))).scalar_one()
        # Preserve the originally verified organizer identity unless a reviewer
        # explicitly revisits it; no automatic mass reassociation is attempted.
        session_count = opportunity_count = 0
        for session in candidate.sessions:
            session_insert = pg_insert(FreeEventSession).values(
                id=_uuid(),
                event_id=event_id,
                session_key=session.session_key,
                starts_at=session.starts_at,
                ends_at=session.ends_at,
                starts_on=session.starts_on,
                ends_on_exclusive=session.ends_on_exclusive,
                timezone_name=session.timezone_name,
                city=session.city,
                venue=session.venue,
                is_cancelled=session.is_cancelled,
            )
            session_insert = session_insert.on_conflict_do_update(
                index_elements=[FreeEventSession.event_id, FreeEventSession.session_key],
                set_={
                    "starts_at": session_insert.excluded.starts_at,
                    "ends_at": session_insert.excluded.ends_at,
                    "starts_on": session_insert.excluded.starts_on,
                    "ends_on_exclusive": session_insert.excluded.ends_on_exclusive,
                    "timezone_name": session_insert.excluded.timezone_name,
                    "city": session_insert.excluded.city,
                    "venue": session_insert.excluded.venue,
                    "is_cancelled": session_insert.excluded.is_cancelled,
                },
            ).returning(FreeEventSession.id)
            session_id = (await db.execute(session_insert)).scalar_one()
            session_count += 1
            for opportunity in session.opportunities:
                opp_insert = pg_insert(FreeEventRegistrationOpportunity).values(
                    id=_uuid(),
                    session_id=session_id,
                    opportunity_key=opportunity.opportunity_key,
                    registration_url=opportunity.registration_url,
                    registration_opens_at=opportunity.opens_at,
                    registration_closes_at=opportunity.closes_at,
                    fee_kind=opportunity.fee_kind,
                    fee_amount=opportunity.fee_amount,
                    fee_currency=opportunity.fee_currency,
                    eligibility_note=opportunity.eligibility_note,
                    # Never persist auto-publication claims from scraped JSON.
                    registration_status=opportunity.registration_status,
                    official_verified=False,
                )
                opp_insert = opp_insert.on_conflict_do_update(
                    index_elements=[
                        FreeEventRegistrationOpportunity.session_id,
                        FreeEventRegistrationOpportunity.opportunity_key,
                    ],
                    set_={
                        "registration_url": opp_insert.excluded.registration_url,
                        "registration_opens_at": opp_insert.excluded.registration_opens_at,
                        "registration_closes_at": opp_insert.excluded.registration_closes_at,
                        "fee_kind": opp_insert.excluded.fee_kind,
                        "fee_amount": opp_insert.excluded.fee_amount,
                        "fee_currency": opp_insert.excluded.fee_currency,
                        "eligibility_note": opp_insert.excluded.eligibility_note,
                        "registration_status": opp_insert.excluded.registration_status,
                        "official_verified": False,
                        "last_verified_at": None,
                    },
                )
                await db.execute(opp_insert)
                opportunity_count += 1

        evidence = pg_insert(FreeEventEvidence).values(
            id=_uuid(),
            event_id=event_id,
            source_id=candidate.source_id,
            field_name="source_candidate",
            source_url=candidate.source_url,
            content_fingerprint=fingerprint,
            evidence_excerpt=None,
            observed_at=observed_at,
        )
        await db.execute(evidence.on_conflict_do_nothing(
            index_elements=[
                FreeEventEvidence.event_id, FreeEventEvidence.source_id,
                FreeEventEvidence.field_name, FreeEventEvidence.content_fingerprint,
            ]
        ))
    return {
        "event_id": event_id,
        "fingerprint": fingerprint,
        "session_count": session_count,
        "registration_opportunity_count": opportunity_count,
        "publication_status": "unverified",
        "ai_calls": 0,
    }
