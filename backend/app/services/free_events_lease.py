"""Durable M1 source-batch claims and bounded failure backoff.

This module does not fetch external URLs or create scheduled jobs.
Each call uses a NEW AsyncSession and one atomic PostgreSQL transaction.
All writers lock FreeEventSource before FreeEventIngestionLease to prevent
lock-order inversions; the source access gate remains mandatory.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.free_events import FreeEventIngestionLease, FreeEventSource
from app.services.free_events_ingest import FreeEventSourceNotApproved

SAFE_FAILURE_KINDS = frozenset({
    "network_timeout", "http_429", "http_5xx", "parse_error",
    "schema_drift", "source_revoked", "validation_error", "unknown",
})


def _clock(now: datetime) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("lease clock must be timezone-aware")


def _approved(source: FreeEventSource | None) -> bool:
    return bool(source is not None
                and source.fetch_enabled
                and source.access_review == "reviewed_with_evidence"
                and source.license_evidence_url)


async def claim_source_batch(
    db: AsyncSession,
    *,
    source_id: str,
    now: datetime,
    lease_minutes: int = 10,
) -> str | None:
    """Claim source; return opaque private token, or None if not due/held/backoff.

    Source must be explicitly allowed in PostgreSQL, not merely in JSON registry.
    last_checked_at records an ATTEMPT, never a valid M0 observation day.
    """
    _clock(now)
    if not (1 <= lease_minutes <= 60):
        raise ValueError("bounded 1-60 minute lease required")
    if not source_id or len(source_id) > 80:
        raise ValueError("invalid source ID")
    async with db.begin():
        source = (await db.execute(
            select(FreeEventSource)
            .where(FreeEventSource.id == source_id)
            .with_for_update()
        )).scalar_one_or_none()
        if not _approved(source):
            raise FreeEventSourceNotApproved("source review required")
        interval = timedelta(hours=source.expected_interval_hours)
        if source.last_success_at is not None and source.last_success_at + interval > now:
            return None
        current = await db.get(
            FreeEventIngestionLease, source_id, with_for_update=True
        )
        if current is not None:
            if current.lease_until > now:
                return None
            if current.next_retry_at is not None and current.next_retry_at > now:
                return None
        token = uuid.uuid4().hex
        if current is None:
            db.add(FreeEventIngestionLease(
                source_id=source_id,
                lease_token=token,
                lease_until=now + timedelta(minutes=lease_minutes),
                attempt_at=now,
                consecutive_failures=0,
            ))
        else:
            current.lease_token = token
            current.lease_until = now + timedelta(minutes=lease_minutes)
            current.attempt_at = now
            current.completed_at = None
            current.next_retry_at = None
        source.last_checked_at = now
        await db.flush()
        return token


async def finish_source_batch(
    db: AsyncSession,
    *,
    source_id: str,
    token: str,
    now: datetime,
    success: bool,
    failure_kind: str | None = None,
) -> bool:
    """Release owned, unexpired lease. False for expired/foreign token.

    Never mark a revoked source successful, even if the fetch finished.
    Error categories are allowlisted and contain no raw credentials or URLs.
    """
    _clock(now)
    if not token or len(token) != 32:
        raise ValueError("invalid lease token")
    if failure_kind is not None and failure_kind not in SAFE_FAILURE_KINDS:
        raise ValueError("unsafe failure category")
    if not success and failure_kind is None:
        failure_kind = "unknown"
    async with db.begin():
        source = (await db.execute(
            select(FreeEventSource)
            .where(FreeEventSource.id == source_id)
            .with_for_update()
        )).scalar_one_or_none()
        lease = await db.get(FreeEventIngestionLease, source_id, with_for_update=True)
        if lease is None or lease.lease_token != token or lease.lease_until <= now:
            return False
        if success and not _approved(source):
            success = False
            failure_kind = "source_revoked"
        lease.completed_at = now
        lease.lease_until = now
        if success:
            lease.consecutive_failures = 0
            lease.next_retry_at = None
            lease.last_error_kind = None
            source.last_success_at = now
            source.last_error_kind = None
        else:
            lease.consecutive_failures += 1
            backoff_minutes = min(
                360, 5 * 2 ** min(lease.consecutive_failures - 1, 8)
            )
            lease.next_retry_at = now + timedelta(minutes=backoff_minutes)
            lease.last_error_kind = failure_kind
            if source is not None:
                source.last_error_kind = failure_kind
        await db.flush()
        return True
