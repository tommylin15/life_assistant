"""M1/M2 real PostgreSQL regression on ephemeral CI sidecar ONLY.

Never run with a production DSN. Unlike SQL compilation mocks, exercises the
actual Alembic 0011 schema, transaction boundaries, unique keys, and concurrency.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import os
import uuid
import unittest

from sqlalchemy import func, select, update, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.free_events import (
    FreeEvent, FreeEventEvidence, FreeEventOrganizer,
    FreeEventRegistrationOpportunity, FreeEventSession, FreeEventSource,
)
from app.services.free_events_normalization import EventCandidate, canonical_event_key
from app.services.free_events_ingest import (
    FreeEventSourceNotApproved, ingest_approved_candidate,
)
from app.services.free_events_discovery import list_verified_public_events


def _test_dsn():
    dsn = os.getenv("FREE_EVENTS_INTEGRATION_DATABASE_URL")
    if not dsn:
        return None
    url = make_url(dsn)
    if (
        url.drivername != "postgresql+asyncpg"
        or url.host not in ("127.0.0.1", "localhost")
        or url.port != 5432
        or url.database != "free_events_ci"
        or url.username != "postgres"
    ):
        raise RuntimeError("Refusing non-ephemeral PostgreSQL integration target")
    return dsn


@unittest.skipUnless(os.getenv("FREE_EVENTS_INTEGRATION_DATABASE_URL"), "CI PostgreSQL sidecar required")
class FreeEventPostgresIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(_test_dsn(), pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.now = datetime.now(timezone.utc)
        self.source_id = "moc_" + uuid.uuid4().hex[:20]

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def seed_source(self, *, approved: bool = True):
        async with self.session_factory() as session:
            async with session.begin():
                session.add(FreeEventSource(
                    id=self.source_id,
                    tier="official_dataset",
                    reference_url="https://data.gov.tw/dataset/6478",
                    license_evidence_url=(
                        "https://data.gov.tw/dataset/6478" if approved else None
                    ),
                    access_review="reviewed_with_evidence" if approved else "pending",
                    fetch_enabled=approved,
                    expected_interval_hours=12,
                    last_success_at=self.now if approved else None,
                ))

    def candidate(self, *, title="Test event", fee_kind="free",
                  status="open", venue="CI Venue"):
        return EventCandidate.model_validate({
            "source_id": self.source_id,
            "external_event_key": "event-1",
            "title": title,
            "source_url": "https://data.gov.tw/dataset/6478",
            "official_url": "https://organizer.example.tw/official/1",
            # Official URLs in source data are NOT automatically verification.
            "official_verified": False,
            "organizer_name": "Synthetic Organizer",
            "sessions": [{
                "session_key": "one",
                "starts_at": (self.now + timedelta(days=1)).isoformat(),
                "ends_at": (self.now + timedelta(days=1, hours=2)).isoformat(),
                "venue": venue,
                "opportunities": [{
                    "opportunity_key": "admission",
                    "registration_url": "https://organizer.example.tw/register/1",
                    "opens_at": (self.now - timedelta(hours=2)).isoformat(),
                    "closes_at": (self.now + timedelta(hours=2)).isoformat(),
                    "fee_kind": fee_kind,
                    "registration_status": status,
                    "official_verified": False,
                }],
            }],
        })

    async def ingest(self, candidate):
        async with self.session_factory() as db:
            return await ingest_approved_candidate(
                db, candidate, observed_at=self.now
            )

    async def records(self, candidate):
        async with self.session_factory() as db:
            event = (
                await db.execute(select(FreeEvent).where(
                    FreeEvent.canonical_key == canonical_event_key(candidate)
                ))
            ).scalar_one()
            session = (await db.execute(select(FreeEventSession).where(
                FreeEventSession.event_id == event.id
            ))).scalar_one()
            opportunity = (await db.execute(select(FreeEventRegistrationOpportunity).where(
                FreeEventRegistrationOpportunity.session_id == session.id
            ))).scalar_one()
            return event, session, opportunity

    async def verify_event_and_opportunity(self, candidate, *, verified_at=None):
        reviewed_at = verified_at or self.now
        event, session, opportunity = await self.records(candidate)
        async with self.session_factory() as db:
            async with db.begin():
                await db.execute(
                    update(FreeEvent).where(FreeEvent.id == event.id).values(
                        verification_status="verified",
                        last_verified_at=reviewed_at,
                    )
                )
                await db.execute(
                    update(FreeEventRegistrationOpportunity)
                    .where(FreeEventRegistrationOpportunity.id == opportunity.id)
                    .values(official_verified=True, last_verified_at=reviewed_at)
                )
        return event.id

    async def assert_exactly_one_chain(self, candidate):
        """Count only this test's unique source/event; other tests share sidecar."""
        event, session, _ = await self.records(candidate)
        async with self.session_factory() as db:
            conditions = (
                (FreeEvent, FreeEvent.source_id == self.source_id),
                (FreeEventSession, FreeEventSession.event_id == event.id),
                (FreeEventRegistrationOpportunity,
                 FreeEventRegistrationOpportunity.session_id == session.id),
                (FreeEventEvidence, FreeEventEvidence.event_id == event.id),
                (FreeEventOrganizer, FreeEventOrganizer.id == event.organizer_id),
            )
            for table, where in conditions:
                value = await db.scalar(
                    select(func.count()).select_from(table).where(where)
                )
                self.assertEqual(value, 1, table.__tablename__)

    async def mine(self, event_id):
        async with self.session_factory() as db:
            cards = await list_verified_public_events(db, now=self.now)
            return [card for card in cards if card.event_id == event_id]

    async def test_exact_alembic_head_and_additive_tables(self):
        async with self.engine.connect() as conn:
            revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            self.assertEqual(revision, "20261009_0012")
            rows = (await conn.execute(text(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' "
                "AND tablename LIKE 'free_event_%'"
            ))).scalars().all()
            self.assertEqual(len(rows), 7)
            self.assertIn("free_events", rows)
            self.assertIn("free_event_ingestion_leases", rows)
            self.assertIn("free_event_registration_opportunities", rows)
            other = await conn.scalar(text("SELECT to_regclass('public.tasks')"))
            self.assertIsNotNone(other)

    async def test_database_disallows_unreviewed_source_fetch(self):
        async with self.session_factory() as db:
            with self.assertRaises(IntegrityError):
                async with db.begin():
                    db.add(FreeEventSource(
                        id=self.source_id, tier="official_dataset",
                        reference_url="https://data.gov.tw/dataset/6478",
                        access_review="pending", fetch_enabled=True,
                        expected_interval_hours=12,
                    ))
                    await db.flush()

    async def test_source_approval_gate_rejects_without_inserts(self):
        await self.seed_source(approved=False)
        candidate = self.candidate()
        with self.assertRaises(FreeEventSourceNotApproved):
            await self.ingest(candidate)
        async with self.engine.connect() as conn:
            count = await conn.scalar(select(func.count()).select_from(FreeEvent).where(
                FreeEvent.source_id == self.source_id
            ))
            self.assertEqual(count, 0)

    async def test_idempotent_upsert_has_exactly_one_event_session_registration_evidence(self):
        await self.seed_source()
        candidate = self.candidate()
        first = await self.ingest(candidate)
        second = await self.ingest(candidate)
        self.assertEqual(first["event_id"], second["event_id"])
        event, _, opp = await self.records(candidate)
        self.assertEqual(opp.fee_kind, "free")
        self.assertEqual(event.verification_status, "unverified")
        self.assertFalse(opp.official_verified)
        await self.assert_exactly_one_chain(candidate)

    async def test_four_concurrent_retries_cannot_double_insert(self):
        await self.seed_source()
        candidate = self.candidate()
        results = await asyncio.wait_for(
            asyncio.gather(*(self.ingest(candidate) for _ in range(4))),
            timeout=20,
        )
        self.assertEqual(len({item["event_id"] for item in results}), 1)
        await self.assert_exactly_one_chain(candidate)

    async def test_reverification_and_real_read_filter_are_fresh_and_fail_closed(self):
        await self.seed_source()
        candidate = self.candidate()
        stored = await self.ingest(candidate)
        event_id = stored["event_id"]
        self.assertEqual(await self.mine(event_id), [])
        await self.verify_event_and_opportunity(candidate)
        cards = await self.mine(event_id)
        self.assertEqual(len(cards), 1)
        self.assertTrue(cards[0].window_confirmed_open)
        self.assertEqual(cards[0].fee_kind, "free")
        # Unchanged reingestion cannot silently lose explicit review.
        await self.ingest(candidate)
        self.assertEqual(len(await self.mine(event_id)), 1)
        # An updated verified source item must retract prior verification.
        changed = self.candidate(title="Corrected program")
        await self.ingest(changed)
        event, _, reg = await self.records(changed)
        self.assertEqual(event.verification_status, "stale")
        self.assertEqual(await self.mine(event_id), [])
        await self.verify_event_and_opportunity(changed)
        # Opportunity fee/status changed => its prior verified flag must be removed.
        await self.ingest(self.candidate(title="Corrected program", status="waitlist_available"))
        _, _, reg = await self.records(changed)
        self.assertFalse(reg.official_verified)
        self.assertIsNone(reg.last_verified_at)

    async def test_old_verification_is_not_a_permanent_pass(self):
        await self.seed_source()
        candidate = self.candidate()
        await self.ingest(candidate)
        stale = self.now - timedelta(days=3)
        event_id = await self.verify_event_and_opportunity(candidate, verified_at=stale)
        self.assertEqual(await self.mine(event_id), [], "Old review must expire")


if __name__ == "__main__":
    unittest.main()
