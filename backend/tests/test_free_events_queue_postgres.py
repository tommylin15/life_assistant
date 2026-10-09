"""Real PostgreSQL queue, retry, fencing and MoC catalog integration tests.

CI connects only to the ephemeral local database. No live host or credentials.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import os
import uuid
import unittest

from sqlalchemy import func, select, text, update
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models.free_events import (
    FreeEvent, FreeEventCandidateQueue, FreeEventSource,
)
from app.services.free_events_candidate_queue import (
    claim_candidate, complete_candidate, enqueue_candidate,
)
from app.services.free_events_ingest import (
    FreeEventSourceNotApproved, ingest_approved_candidate,
)
from app.services.free_events_normalization import EventCandidate


def _dsn():
    url = os.getenv("FREE_EVENTS_INTEGRATION_DATABASE_URL", "")
    if not url:
        return None
    parts = make_url(url)
    if not (parts.drivername == "postgresql+asyncpg"
            and parts.host in ("localhost", "127.0.0.1")
            and parts.port == 5432 and parts.database == "free_events_ci"
            and parts.username == "postgres"):
        raise RuntimeError("refusing non-ephemeral PostgreSQL")
    return url


@unittest.skipUnless(os.getenv("FREE_EVENTS_INTEGRATION_DATABASE_URL"),
                     "PostgreSQL CI sidecar required")
class CandidateQueuePostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(_dsn(), pool_pre_ping=True)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc) - timedelta(seconds=2)
        self.source_id = "q_" + uuid.uuid4().hex[:24]
        async with self.sessions() as db:
            async with db.begin():
                db.add(FreeEventSource(
                    id=self.source_id, tier="official_dataset",
                    reference_url="https://data.gov.tw/dataset/6478",
                    license_evidence_url="https://data.gov.tw/dataset/6478",
                    access_review="reviewed_with_evidence", fetch_enabled=True,
                    expected_interval_hours=12,
                ))

    async def asyncTearDown(self):
        await self.engine.dispose()

    def candidate(self, title="Structured event"):
        return EventCandidate.model_validate({
            "source_id": self.source_id,
            "external_event_key": "id1",
            "title": title,
            "source_url": "https://data.gov.tw/dataset/6478",
            "official_url": "https://organizer.example.tw/event/1",
            "official_verified": False,
            "sessions": [{
                "session_key": "first",
                "starts_at": (self.now + timedelta(days=1)).isoformat(),
                "ends_at": (self.now + timedelta(days=1, hours=2)).isoformat(),
                "opportunities": [{
                    "opportunity_key": "general",
                    "registration_url": "https://organizer.example.tw/register/1",
                    "fee_kind": "unknown",
                    "registration_status": "unannounced",
                }],
            }],
        })

    async def enqueue(self, candidate=None):
        async with self.sessions() as db:
            return await enqueue_candidate(
                db, candidate or self.candidate(), observed_at=self.now,
            )

    async def claim(self, at=None):
        async with self.sessions() as db:
            return await claim_candidate(
                db, source_id=self.source_id, now=at or self.now,
            )

    async def finish(self, claim, success=True, at=None, failure_kind=None):
        async with self.sessions() as db:
            return await complete_candidate(
                db, claim, now=at or self.now, success=success,
                failure_kind=failure_kind,
            )

    async def test_queue_dedup_normalize_and_catalog_zero_ai(self):
        results = await asyncio.gather(*(self.enqueue() for _ in range(4)))
        self.assertEqual(results.count("queued"), 1)
        self.assertEqual(results.count("unchanged"), 3)
        claim = await self.claim()
        self.assertIsNotNone(claim)
        async with self.sessions() as db:
            result = await ingest_approved_candidate(
                db, EventCandidate.model_validate(claim.payload),
                observed_at=claim.observed_at,
            )
        self.assertEqual(result["ai_calls"], 0)
        self.assertEqual(result["publication_status"], "unverified")
        self.assertTrue(await self.finish(claim))
        self.assertEqual(await self.enqueue(), "unchanged")
        self.assertIsNone(await self.claim())
        async with self.sessions() as db:
            count = await db.scalar(select(func.count()).select_from(
                FreeEvent).where(FreeEvent.source_id == self.source_id))
            queued = (await db.execute(select(FreeEventCandidateQueue).where(
                FreeEventCandidateQueue.source_id == self.source_id))).scalar_one()
        self.assertEqual(count, 1)
        self.assertEqual(queued.state, "done")
        self.assertEqual(queued.attempt_count, 1)
        self.assertIsNone(queued.lease_token)

    async def test_changed_candidate_reopens_and_fences_old_version(self):
        self.assertEqual(await self.enqueue(), "queued")
        old_claim = await self.claim()
        self.assertEqual(await self.enqueue(self.candidate("Updated event")), "queued")
        self.assertFalse(await self.finish(old_claim))
        next_claim = await self.claim()
        self.assertIsNotNone(next_claim)
        self.assertEqual(next_claim.payload["title"], "Updated event")
        self.assertNotEqual(old_claim.fingerprint, next_claim.fingerprint)
        self.assertTrue(await self.finish(next_claim))
        self.assertIsNone(await self.claim())

    async def test_retry_and_expired_claim_are_fenced(self):
        await self.enqueue()
        first = await self.claim()
        self.assertTrue(await self.finish(
            first, success=False, failure_kind="validation_error",
        ))
        self.assertIsNone(await self.claim())
        async with self.sessions() as db:
            async with db.begin():
                await db.execute(update(FreeEventCandidateQueue).where(
                    FreeEventCandidateQueue.source_id == self.source_id
                ).values(next_retry_at=self.now - timedelta(seconds=1)))
        second = await self.claim()
        self.assertNotEqual(first.token, second.token)
        self.assertFalse(await self.finish(first))
        self.assertTrue(await self.finish(second))
        self.assertIsNone(await self.claim())

    async def test_crash_after_ingest_replay_does_not_duplicate_catalog(self):
        await self.enqueue()
        old = await self.claim()
        async with self.sessions() as db:
            await ingest_approved_candidate(
                db, EventCandidate.model_validate(old.payload),
                observed_at=old.observed_at,
            )
        async with self.sessions() as db:
            async with db.begin():
                await db.execute(update(FreeEventCandidateQueue).where(
                    FreeEventCandidateQueue.source_id == self.source_id
                ).values(lease_until=self.now - timedelta(seconds=1)))
        newer = await self.claim()
        self.assertIsNotNone(newer)
        self.assertFalse(await self.finish(old))
        async with self.sessions() as db:
            await ingest_approved_candidate(
                db, EventCandidate.model_validate(newer.payload),
                observed_at=newer.observed_at,
            )
        self.assertTrue(await self.finish(newer))
        async with self.sessions() as db:
            count = await db.scalar(select(func.count()).select_from(
                FreeEvent).where(FreeEvent.source_id == self.source_id))
        self.assertEqual(count, 1)

    async def test_source_revocation_blocks_enqueue_claim_and_ack(self):
        await self.enqueue()
        claim = await self.claim()
        async with self.sessions() as db:
            async with db.begin():
                await db.execute(update(FreeEventSource).where(
                    FreeEventSource.id == self.source_id
                ).values(fetch_enabled=False, access_review="pending"))
        with self.assertRaises(FreeEventSourceNotApproved):
            await self.enqueue()
        with self.assertRaises(FreeEventSourceNotApproved):
            await self.claim()
        with self.assertRaises(FreeEventSourceNotApproved):
            await self.finish(claim)

    async def test_source_cannot_sneak_verified_claim_into_queue(self):
        candidate = self.candidate()
        fake = candidate.model_copy(update={"official_verified": True})
        with self.assertRaises(ValueError):
            await self.enqueue(fake)

    async def test_real_queue_schema_and_version(self):
        async with self.engine.connect() as conn:
            self.assertEqual(
                await conn.scalar(text("SELECT version_num FROM alembic_version")),
                "20261009_0014",
            )
            self.assertTrue(await conn.scalar(text(
                "SELECT to_regclass('public.free_event_candidate_queue') IS NOT NULL"
            )))


if __name__ == "__main__":
    unittest.main()
