"""Durable, bounded, deterministic candidate queue; no network or AI."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import uuid

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.free_events import FreeEventCandidateQueue, FreeEventSource
from app.services.free_events_ingest import FreeEventSourceNotApproved
from app.services.free_events_normalization import EventCandidate

MAX_NORMALIZED_BYTES = 128 * 1024
MAX_ATTEMPTS = 5
SAFE_FAILURE_KINDS = {"schema_drift", "validation_error", "source_revoked", "unknown"}


@dataclass(frozen=True, slots=True)
class CandidateClaim:
    id: str
    token: str
    fingerprint: str
    payload: dict
    observed_at: datetime


def _clock(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware timestamp required")
    if value > datetime.now(timezone.utc) + timedelta(seconds=5):
        raise ValueError("future timestamp rejected")


async def _approved_source(db: AsyncSession, source_id: str) -> None:
    source = (await db.execute(
        select(FreeEventSource).where(FreeEventSource.id == source_id).with_for_update()
    )).scalar_one_or_none()
    if not (source and source.fetch_enabled
            and source.access_review == "reviewed_with_evidence"
            and source.license_evidence_url):
        raise FreeEventSourceNotApproved("approved source required")


async def enqueue_candidate(
    db: AsyncSession, candidate: EventCandidate, *, observed_at: datetime,
) -> str:
    """Persist only validated JSON; changed fingerprints invalidate stale leases."""
    _clock(observed_at)
    if candidate.official_verified or any(
        o.official_verified for s in candidate.sessions for o in s.opportunities
    ):
        raise ValueError("source candidate cannot self-verify")
    payload = candidate.model_dump(mode="json")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")
    if len(serialized) > MAX_NORMALIZED_BYTES:
        raise ValueError("candidate payload exceeds size cap")
    fingerprint = hashlib.sha256(serialized).hexdigest()
    async with db.begin():
        await _approved_source(db, candidate.source_id)
        insert = pg_insert(FreeEventCandidateQueue).values(
            id=str(uuid.uuid4()), source_id=candidate.source_id,
            external_event_key=candidate.external_event_key,
            content_fingerprint=fingerprint, candidate_payload=payload,
            state="pending", attempt_count=0,
            first_seen_at=observed_at, observed_at=observed_at,
            updated_at=observed_at,
        )
        stmt = insert.on_conflict_do_update(
            index_elements=[
                FreeEventCandidateQueue.source_id,
                FreeEventCandidateQueue.external_event_key,
            ],
            set_={
                "content_fingerprint": insert.excluded.content_fingerprint,
                "candidate_payload": insert.excluded.candidate_payload,
                "state": "pending", "attempt_count": 0,
                "observed_at": insert.excluded.observed_at,
                "updated_at": insert.excluded.updated_at,
                "next_retry_at": None, "lease_token": None, "lease_until": None,
                "processed_at": None, "last_error_kind": None,
            },
            where=(FreeEventCandidateQueue.content_fingerprint !=
                   insert.excluded.content_fingerprint),
        ).returning(FreeEventCandidateQueue.id)
        changed = (await db.execute(stmt)).scalar_one_or_none()
    return "queued" if changed else "unchanged"


async def claim_candidate(
    db: AsyncSession, *, source_id: str, now: datetime, lease_minutes: int = 30,
) -> CandidateClaim | None:
    _clock(now)
    if not 1 <= lease_minutes <= 60:
        raise ValueError("lease must be 1-60 minutes")
    async with db.begin():
        await _approved_source(db, source_id)
        # A worker may crash on its final attempt; expire that lease into a
        # terminal failed row rather than leaving processing stuck forever.
        await db.execute(
            update(FreeEventCandidateQueue)
            .where(FreeEventCandidateQueue.source_id == source_id,
                   FreeEventCandidateQueue.state == "processing",
                   FreeEventCandidateQueue.attempt_count >= MAX_ATTEMPTS,
                   FreeEventCandidateQueue.lease_until <= now)
            .values(state="failed", lease_token=None, lease_until=None,
                    next_retry_at=None, last_error_kind="unknown", updated_at=now)
        )
        row = (await db.execute(
            select(FreeEventCandidateQueue)
            .where(
                FreeEventCandidateQueue.source_id == source_id,
                FreeEventCandidateQueue.attempt_count < MAX_ATTEMPTS,
                or_(
                    FreeEventCandidateQueue.state == "pending",
                    and_(FreeEventCandidateQueue.state == "retry",
                         or_(FreeEventCandidateQueue.next_retry_at.is_(None),
                             FreeEventCandidateQueue.next_retry_at <= now)),
                    and_(FreeEventCandidateQueue.state == "processing",
                         FreeEventCandidateQueue.lease_until <= now),
                ),
            )
            .order_by(FreeEventCandidateQueue.first_seen_at,
                      FreeEventCandidateQueue.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )).scalar_one_or_none()
        if row is None:
            return None
        row.state = "processing"
        row.attempt_count += 1
        row.lease_token = uuid.uuid4().hex
        row.lease_until = now + timedelta(minutes=lease_minutes)
        row.next_retry_at = None
        row.updated_at = now
        await db.flush()
        return CandidateClaim(
            id=row.id, token=row.lease_token,
            fingerprint=row.content_fingerprint,
            payload=dict(row.candidate_payload), observed_at=row.observed_at,
        )


async def complete_candidate(
    db: AsyncSession, claim: CandidateClaim, *, now: datetime,
    success: bool, failure_kind: str | None = None,
) -> bool:
    """Fence old tokens; store only error category, never private source text."""
    _clock(now)
    if not success and failure_kind not in SAFE_FAILURE_KINDS:
        raise ValueError("allowlisted failure category required")
    async with db.begin():
        # Lock source before candidate, matching enqueue/claim/ingestion lock order.
        if success:
            source_id = str(claim.payload.get("source_id", ""))
            await _approved_source(db, source_id)
        row = await db.get(FreeEventCandidateQueue, claim.id, with_for_update=True)
        if (row is None or row.state != "processing"
                or row.lease_token != claim.token
                or row.content_fingerprint != claim.fingerprint
                or row.lease_until is None or row.lease_until <= now):
            return False
        if success:
            if row.source_id != source_id:
                return False
            row.state = "done"
            row.processed_at = now
            row.last_error_kind = None
            row.next_retry_at = None
        else:
            row.state = "failed" if row.attempt_count >= MAX_ATTEMPTS else "retry"
            row.last_error_kind = failure_kind
            row.next_retry_at = (
                None if row.state == "failed"
                else now + timedelta(minutes=min(360, 5 * (2 ** (row.attempt_count - 1))))
            )
        row.lease_token = None
        row.lease_until = None
        row.updated_at = now
        return True
