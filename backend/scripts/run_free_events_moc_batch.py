"""Bounded ingestion of the Ministry of Culture published *dataset* JSON.

Does not scrape HTML, use credentialed APIs, follow redirects, or verify free
registration. Writes real source observations and unverified event candidates.
All network source URLs are fixed in code; input page URLs are never fetched.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import uuid

import httpx
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.free_events import FreeEventSource, FreeEventSourceObservation
from app.services.free_events_candidate_queue import enqueue_candidate, claim_candidate, complete_candidate
from app.services.free_events_normalization import EventCandidate
from app.services.free_events_ingest import ingest_approved_candidate
from app.services.free_events_lease import claim_source_batch, finish_source_batch
from app.services.free_events_moc_adapter import normalize_moc_record

DATASET_ENDPOINT = (
    "https://cloud.culture.tw/frontsite/trans/SearchShowAction.do"
    "?method=doFindTypeJ&category=all"
)
DATASET_PROVENANCE = "https://data.gov.tw/dataset/6478"
SOURCE_ID = "moc_events_all"
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RECORDS = 12000
MAX_ADMISSION = 400
EXPECTED_REVISION = "20261009_0014"


class SourceBatchError(RuntimeError):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


def parse_moc_response(data: bytes) -> list[dict]:
    if len(data) > MAX_RESPONSE_BYTES:
        raise SourceBatchError("validation_error")
    try:
        rows = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        raise SourceBatchError("parse_error") from None
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
        raise SourceBatchError("schema_drift")
    if not all(isinstance(row, dict) for row in rows):
        raise SourceBatchError("schema_drift")
    return rows


async def fetch_moc_dataset() -> bytes:
    """Fixed host, no redirects/credentials/env proxies; finite stream cap."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(30, connect=8), verify=True,
        ) as client:
            async with client.stream(
                "GET", DATASET_ENDPOINT,
                headers={"Accept": "application/json",
                         "User-Agent": "life_assistant-free-event-observer/1.0"},
            ) as response:
                if response.status_code == 429:
                    raise SourceBatchError("http_429")
                if response.status_code >= 500:
                    raise SourceBatchError("http_5xx")
                if response.status_code != 200:
                    raise SourceBatchError("validation_error")
                # Stream chunks and fail before exhausting runner resources.
                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > MAX_RESPONSE_BYTES:
                        raise SourceBatchError("validation_error")
                return bytes(chunks)
    except (httpx.TimeoutException, httpx.TransportError):
        raise SourceBatchError("network_timeout") from None


def choose_bounded_sample(rows: list[dict], observed_at: datetime) -> list[dict]:
    """Rotate coverage when dataset exceeds the bounded batch size."""
    if len(rows) <= MAX_ADMISSION:
        return rows
    pages = math.ceil(len(rows) / MAX_ADMISSION)
    page = observed_at.astimezone(timezone.utc).date().toordinal() % pages
    index = page * MAX_ADMISSION
    return rows[index:index + MAX_ADMISSION]


async def _ensure_first_party_source(db):
    """Seed only a *missing* approved official source; never undo admin revoke."""
    stmt = pg_insert(FreeEventSource).values(
        id=SOURCE_ID,
        tier="official_dataset",
        reference_url=DATASET_PROVENANCE,
        license_evidence_url=DATASET_PROVENANCE,
        access_review="reviewed_with_evidence",
        fetch_enabled=True,
        expected_interval_hours=12,
    ).on_conflict_do_nothing(index_elements=[FreeEventSource.id])
    async with db.begin():
        await db.execute(stmt)


async def run_batch() -> dict:
    # Fail before connecting to any network when migration has not been applied.
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    lease_token = None
    acquired = False
    try:
        async with engine.connect() as conn:
            revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != EXPECTED_REVISION:
                raise SourceBatchError("schema_drift")
        async with factory() as db:
            await _ensure_first_party_source(db)
        observed_at = datetime.now(timezone.utc)
        async with factory() as db:
            lease_token = await claim_source_batch(
                db, source_id=SOURCE_ID, now=observed_at, lease_minutes=60,
            )
        if lease_token is None:
            return {"status": "NOT_DUE_OR_LEASED", "source_id": SOURCE_ID,
                    "observation_written": False, "published": 0}
        acquired = True
        try:
            raw = await fetch_moc_dataset()
            rows = parse_moc_response(raw)
            sample = choose_bounded_sample(rows, observed_at)
            if not rows:
                raise SourceBatchError("schema_drift")
            accepted = rejected = unknown_fee = unknown_open = 0
            queued = unchanged = 0
            for row in sample:
                try:
                    candidate = normalize_moc_record(row)
                    if not candidate.sessions:
                        raise ValueError("no structured show sessions")
                except (ValueError, TypeError):
                    rejected += 1
                    continue
                async with factory() as db:
                    action = await enqueue_candidate(db, candidate, observed_at=observed_at)
                accepted += 1
                queued += int(action == "queued")
                unchanged += int(action == "unchanged")
                unknown_fee += sum(
                    opportunity.fee_kind == "unknown"
                    for session in candidate.sessions
                    for opportunity in session.opportunities
                )
                unknown_open += sum(
                    opportunity.opens_at is None
                    for session in candidate.sessions
                    for opportunity in session.opportunities
                )
            if accepted == 0:
                raise SourceBatchError("schema_drift")
            processed = failed = 0
            for _ in range(MAX_ADMISSION):
                async with factory() as db:
                    claim = await claim_candidate(
                        db, source_id=SOURCE_ID, now=datetime.now(timezone.utc),
                        lease_minutes=60,
                    )
                if claim is None:
                    break
                succeeded = False
                try:
                    candidate = EventCandidate.model_validate(claim.payload)
                    async with factory() as db:
                        await ingest_approved_candidate(
                            db, candidate, observed_at=claim.observed_at,
                        )
                    succeeded = True
                except Exception:
                    succeeded = False
                async with factory() as db:
                    acked = await complete_candidate(
                        db, claim, now=datetime.now(timezone.utc),
                        success=succeeded,
                        failure_kind=None if succeeded else "unknown",
                    )
                if not acked:
                    raise SourceBatchError("source_revoked")
                processed += int(succeeded)
                failed += int(not succeeded)
            # The sampled rows are not the complete underlying source.
            async with factory() as db:
                async with db.begin():
                    db.add(FreeEventSourceObservation(
                        id=str(uuid.uuid4()),
                        source_id=SOURCE_ID,
                        observed_at=observed_at,
                        endpoint_key="moc_all_categories_json",
                        response_fingerprint=hashlib.sha256(raw).hexdigest(),
                        record_count=len(rows),
                        accepted_count=accepted,
                        rejected_count=rejected,
                        fee_unknown_count=unknown_fee,
                        registration_start_unknown_count=unknown_open,
                        complete_source=(len(sample) == len(rows) and rejected == 0),
                    ))
            if failed:
                raise SourceBatchError("validation_error")
            async with factory() as db:
                ack = await finish_source_batch(
                    db, source_id=SOURCE_ID, token=lease_token,
                    now=datetime.now(timezone.utc), success=True,
                )
            if not ack:
                raise SourceBatchError("validation_error")
            return {
                "status": "OBSERVED_UNVERIFIED", "source_id": SOURCE_ID,
                "observed_at": observed_at.isoformat(),
                "source_records": len(rows),
                "candidate_records_accepted": accepted,
                "candidate_records_queued": queued,
                "candidate_records_unchanged": unchanged,
                "candidate_records_ingested": processed,
                "candidate_records_failed": failed,
                "candidate_records_rejected": rejected,
                "fee_unknown": unknown_fee,
                "registration_start_unknown": unknown_open,
                "complete_source": len(sample) == len(rows) and rejected == 0,
                "observation_written": True, "published": 0,
            }
        except Exception as error:
            failure = error.category if isinstance(error, SourceBatchError) else "unknown"
            async with factory() as db:
                await finish_source_batch(
                    db, source_id=SOURCE_ID, token=lease_token,
                    now=datetime.now(timezone.utc), success=False,
                    failure_kind=failure,
                )
            raise SourceBatchError(failure) from None
    finally:
        await engine.dispose()


def main() -> None:
    result = asyncio.run(run_batch())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
