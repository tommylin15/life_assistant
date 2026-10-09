"""PostgreSQL ingest SQL and fail-closed source gate. No external database."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import unittest

from sqlalchemy.dialects import postgresql

from app.services.free_events_ingest import (
    FreeEventSourceNotApproved, _event_upsert, ingest_approved_candidate,
)
from app.services.free_events_normalization import EventCandidate


class FreeEventIngestionTests(unittest.IsolatedAsyncioTestCase):
    def candidate(self, **kwargs):
        obj = {
            "source_id": "moc_events_all",
            "external_event_key": "moc-1",
            "title": "真實資料需來源授權",
            "source_url": "https://example.tw/events/1",
            "sessions": [{
                "session_key": "slot1",
                "starts_on": "2026-10-20",
                "opportunities": [{"opportunity_key": "basic", "fee_kind": "unknown"}],
            }],
        }
        obj.update(kwargs)
        return EventCandidate.model_validate(obj)

    def session(self, source):
        db = MagicMock()
        db.execute = AsyncMock()
        # AsyncSession.execute() is async; its SQLAlchemy Result methods are
        # synchronous (scalar_one/scalar_one_or_none). Do not await Result.
        db.execute.return_value = MagicMock()
        db.begin.return_value.__aenter__ = AsyncMock()
        db.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        db.execute.return_value.scalar_one_or_none.return_value = source
        return db

    async def test_denied_source_never_reaches_insert(self):
        for source in (
            None,
            MagicMock(fetch_enabled=False, access_review="reviewed_with_evidence",
                      license_evidence_url="https://example.tw/license"),
            MagicMock(fetch_enabled=True, access_review="pending",
                      license_evidence_url="https://example.tw/license"),
            MagicMock(fetch_enabled=True, access_review="reviewed_with_evidence",
                      license_evidence_url=None),
        ):
            with self.subTest(source=source):
                db = self.session(source)
                with self.assertRaises(FreeEventSourceNotApproved):
                    await ingest_approved_candidate(
                        db, self.candidate(), observed_at=datetime.now(timezone.utc)
                    )
                self.assertEqual(db.execute.await_count, 1)
                sql = str(db.execute.await_args_list[0].args[0].compile(
                    dialect=postgresql.dialect()
                ))
                self.assertIn("FOR UPDATE", sql)
                self.assertNotIn("INSERT", sql)

    async def test_future_and_naive_observation_rejected_before_db(self):
        db = self.session(None)
        for timestamp in (
            datetime(2026, 10, 10),
            datetime.now(timezone.utc) + timedelta(days=1),
        ):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                await ingest_approved_candidate(
                    db, self.candidate(), observed_at=timestamp
                )
        db.execute.assert_not_awaited()

    async def test_hard_batch_limit_fails_before_db(self):
        candidate = self.candidate(sessions=[{
            "session_key": f"s{i}", "opportunities": []
        } for i in range(101)])
        db = self.session(None)
        with self.assertRaisesRegex(ValueError, "bounded ingestion"):
            await ingest_approved_candidate(
                db, candidate, observed_at=datetime.now(timezone.utc)
            )
        db.execute.assert_not_awaited()

    def test_event_upsert_is_atomic_and_conflict_invalidates_review(self):
        stmt = _event_upsert(self.candidate(), "a" * 64)
        sql = str(stmt.compile(dialect=postgresql.dialect()))
        self.assertIn("ON CONFLICT (canonical_key) DO UPDATE", sql)
        self.assertIn("RETURNING free_events.id", sql)
        self.assertIn("CASE WHEN", sql)
        params = stmt.compile(dialect=postgresql.dialect()).params
        self.assertIn(["verified", "stale"], params.values())
        self.assertIn("stale", params.values())
        self.assertIn("content_fingerprint", sql)
        self.assertNotIn("DELETE", sql)

    async def test_approved_ingestion_uses_nested_unique_keys_and_returns_unverified(self):
        source = MagicMock(
            fetch_enabled=True, access_review="reviewed_with_evidence",
            license_evidence_url="https://data.gov.tw/dataset/6478"
        )
        db = self.session(source)
        source_result = MagicMock()
        source_result.scalar_one_or_none.return_value = source
        event_result = MagicMock()
        event_result.scalar_one.return_value = "event-id"
        session_result = MagicMock()
        session_result.scalar_one.return_value = "session-id"
        db.execute.side_effect = [
            source_result, event_result, session_result, MagicMock(), MagicMock()
        ]
        result = await ingest_approved_candidate(
            db, self.candidate(), observed_at=datetime.now(timezone.utc)
        )
        self.assertEqual(result["event_id"], "event-id")
        self.assertEqual(result["session_count"], 1)
        self.assertEqual(result["registration_opportunity_count"], 1)
        self.assertEqual(result["publication_status"], "unverified")
        self.assertEqual(result["ai_calls"], 0)
        statements = [
            str(c.args[0].compile(dialect=postgresql.dialect()))
            for c in db.execute.await_args_list
        ]
        self.assertEqual(len(statements), 5)
        for part in statements[1:]:
            self.assertIn("ON CONFLICT", part)
        self.assertIn("DO NOTHING", statements[-1])


if __name__ == "__main__":
    unittest.main()
