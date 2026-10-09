"""M1 deterministic admission, separation of sessions and database guardrails.

No network, external AI or production database is used.
"""
from __future__ import annotations

import importlib.util
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import unittest

from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.session import Base
from app.models.free_events import (
    FreeEvent, FreeEventEvidence, FreeEventOrganizer,
    FreeEventRegistrationOpportunity, FreeEventSession, FreeEventSource,
)
from app.services.free_events_normalization import (
    CandidateOpportunity, CandidateSession, EventCandidate,
    canonical_event_key, meaningful_fingerprint, safe_provenance_url,
    should_enqueue_ai,
)


class FreeEventAdmissionTests(unittest.TestCase):
    @staticmethod
    def make(**override):
        data = {
            "source_id": "moc_events_all",
            "external_event_key": "official-123",
            "title": "市立展覽",
            "source_url": "https://example.org/events/123",
            "official_url": "https://organizer.example.tw/123",
            "official_verified": True,
            "sessions": [
                {"session_key": "s1", "starts_on": "2026-10-10",
                 "ends_on_exclusive": "2026-10-11",
                 "opportunities": [
                     {"opportunity_key": "ordinary",
                      "registration_url": "https://organizer.example.tw/register",
                      "fee_kind": "free", "official_verified": True},
                     {"opportunity_key": "workshop", "fee_kind": "unknown"}]},
                {"session_key": "s2", "starts_on": "2026-10-12",
                 "ends_on_exclusive": "2026-10-13",
                 "opportunities": []},
            ],
        }
        data.update(override)
        return EventCandidate.model_validate(data)

    def test_distinct_sessions_and_registration_opportunities(self):
        item = self.make()
        self.assertEqual(len(item.sessions), 2)
        self.assertEqual(len(item.sessions[0].opportunities), 2)
        self.assertEqual(item.sessions[0].ends_on_exclusive, date(2026, 10, 11))
        self.assertIsNone(item.sessions[0].opportunities[0].opens_at)
        self.assertIsNone(item.sessions[0].opportunities[0].closes_at)
        self.assertEqual(item.sessions[0].opportunities[1].fee_kind, "unknown")

    def test_official_same_url_merges_only_with_verification(self):
        a = self.make()
        b = self.make(source_id="beclass", external_event_key="other")
        self.assertEqual(canonical_event_key(a), canonical_event_key(b))
        self.assertEqual(meaningful_fingerprint(a), meaningful_fingerprint(b))
        c = self.make(source_id="beclass", external_event_key="other",
                      official_verified=False)
        self.assertNotEqual(canonical_event_key(a), canonical_event_key(c))

    def test_unverified_same_title_does_not_merge_across_sources(self):
        a = self.make(official_verified=False, source_id="beclass")
        b = self.make(official_verified=False, source_id="yii_calendar")
        self.assertNotEqual(canonical_event_key(a), canonical_event_key(b))

    def test_fingerprint_is_order_insensitive_and_ignores_source_external_key(self):
        a = self.make()
        b = self.make(external_event_key="revised-key", sessions=[
            {"session_key": "s2", "starts_on": "2026-10-12",
             "ends_on_exclusive": "2026-10-13", "opportunities": []},
            {"session_key": "s1", "starts_on": "2026-10-10",
             "ends_on_exclusive": "2026-10-11",
             "opportunities": [
                 {"opportunity_key": "workshop", "fee_kind": "unknown"},
                 {"opportunity_key": "ordinary",
                  "registration_url": "https://organizer.example.tw/register",
                  "fee_kind": "free", "official_verified": True}
             ]}
        ])
        self.assertEqual(meaningful_fingerprint(a), meaningful_fingerprint(b))
        altered = self.make(title="展覽改期")
        self.assertNotEqual(meaningful_fingerprint(a), meaningful_fingerprint(altered))

    def test_unchanged_or_deterministic_content_never_spends_ai(self):
        hash_a = meaningful_fingerprint(self.make())
        hash_b = meaningful_fingerprint(self.make(title="最新展覽"))
        self.assertFalse(should_enqueue_ai(hash_a, hash_a, False))
        self.assertFalse(should_enqueue_ai(hash_a, hash_b, True))
        self.assertTrue(should_enqueue_ai(hash_a, hash_b, False))
        self.assertTrue(should_enqueue_ai(None, hash_b, False))

    def test_provenance_rejects_internal_urls_no_fetch_is_possible(self):
        for url in ("http://example.tw/a", "https://localhost/x",
                    "https://127.0.0.1/a", "https://[::1]/a",
                    "https://169.254.169.254/latest", "https://foo.local",
                    "https://user:pass@example.tw/a", "https://example.tw/a#secret"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                safe_provenance_url(url)
        self.assertEqual(safe_provenance_url("https://Example.TW"),
                         "https://example.tw/")

    def test_unknown_registration_time_cannot_be_guessed(self):
        item = self.make(sessions=[{"session_key": "s1", "opportunities": [
            {"opportunity_key": "ticket", "registration_status": "unannounced",
             "fee_kind": "unknown"}]}])
        reg = item.sessions[0].opportunities[0]
        self.assertIsNone(reg.opens_at)
        self.assertIsNone(reg.closes_at)
        self.assertEqual(reg.fee_kind, "unknown")

    def test_reject_naive_dates_invalid_window_and_fee(self):
        cases = [
            {"starts_at": datetime(2026, 10, 10, 9)},
            {"starts_on": "2026-10-10", "ends_on_exclusive": "2026-10-10"},
            {"starts_at": datetime.now(timezone.utc), "starts_on": "2026-10-10"},
            {"starts_at": datetime(2026, 10, 10, 9, tzinfo=timezone.utc),
             "ends_at": datetime(2026, 10, 9, 9, tzinfo=timezone.utc)},
        ]
        for item in cases:
            with self.subTest(item=item), self.assertRaises(ValidationError):
                CandidateSession(session_key="s1", **item)
        now = datetime(2026, 10, 10, 9, tzinfo=timezone.utc)
        for data in (
            {"opens_at": now, "closes_at": now},
            {"opens_at": now.replace(tzinfo=None)},
            {"fee_kind": "free", "fee_amount": Decimal("1.00")},
            {"fee_kind": "paid", "fee_amount": Decimal("10.00")},
            {"fee_kind": "free", "official_verified": True},
            {"fee_kind": "FREE"},
        ):
            with self.subTest(item=data), self.assertRaises(ValidationError):
                CandidateOpportunity(opportunity_key="ticket", **data)

    def test_duplicate_keys_or_fake_verified_url_fail(self):
        with self.assertRaises(ValidationError):
            self.make(sessions=[{"session_key": "s"}, {"session_key": "s"}])
        with self.assertRaises(ValidationError):
            self.make(official_url=None, official_verified=True)
        with self.assertRaises(ValidationError):
            self.make(sessions=[{"session_key": "s1", "opportunities": [
                {"opportunity_key": "same"}, {"opportunity_key": "same"}]}])


class FreeEventCatalogSchemaTests(unittest.TestCase):
    def test_schema_is_public_and_keeps_sessions_registration_separate(self):
        names = {FreeEventSource.__tablename__, FreeEventOrganizer.__tablename__,
                 FreeEvent.__tablename__, FreeEventSession.__tablename__,
                 FreeEventRegistrationOpportunity.__tablename__,
                 FreeEventEvidence.__tablename__}
        self.assertEqual(len(names), 6)
        self.assertNotIn("user_sub", FreeEvent.__table__.c)
        self.assertNotIn("raw_html", FreeEvent.__table__.c)
        self.assertIn("ends_on_exclusive", FreeEventSession.__table__.c)
        self.assertTrue(FreeEventRegistrationOpportunity.__table__.c.registration_opens_at.nullable)
        self.assertTrue(FreeEventRegistrationOpportunity.__table__.c.fee_amount.nullable)
        checks = {v.name for v in FreeEventSource.__table__.constraints}
        self.assertIn("ck_free_event_source_fetch_approval", checks)
        checks = {v.name for v in FreeEventRegistrationOpportunity.__table__.constraints}
        self.assertIn("ck_free_event_registration_official_evidence", checks)

    def test_real_sqlite_constraints_reject_unsafe_records(self):
        engine = create_engine("sqlite:///:memory:")
        try:
            Base.metadata.create_all(engine)
            inspector = inspect(engine)
            self.assertTrue(inspector.has_table("free_event_sources"))
            with engine.begin() as c:
                c.execute(text("INSERT INTO free_event_sources "
                               "(id, tier, reference_url, access_review, fetch_enabled, expected_interval_hours) "
                               "VALUES ('safe', 'official_dataset', 'https://example.tw', 'pending', 0, 24)"))
            with self.assertRaises(IntegrityError):
                with engine.begin() as c:
                    c.execute(text("INSERT INTO free_event_sources "
                                   "(id, tier, reference_url, access_review, fetch_enabled, expected_interval_hours) "
                                   "VALUES ('unsafe', 'official_dataset', 'https://example.tw', 'pending', 1, 24)"))
        finally:
            engine.dispose()

    def test_migration_extends_0010_additive_only_and_release_requires_0011(self):
        root = Path(__file__).resolve().parents[1]
        migration_path = root / "alembic/versions/20261009_0011_free_event_catalog.py"
        spec = importlib.util.spec_from_file_location("m1_free_event_migration", migration_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual(module.revision, "20261009_0011")
        self.assertEqual(module.down_revision, "20261007_0010")
        source = migration_path.read_text(encoding="utf-8")
        upgrade = source.split("def upgrade() -> None:", 1)[1].split("def downgrade() -> None:", 1)[0]
        for table in ("free_event_sources", "free_event_organizers", "free_events",
                      "free_event_sessions", "free_event_registration_opportunities",
                      "free_event_evidence"):
            self.assertIn('"' + table + '"', upgrade)
        self.assertNotIn("drop_table", upgrade)
        self.assertNotIn("drop_column", upgrade)
        env = (root / "alembic/env.py").read_text(encoding="utf-8")
        self.assertIn("from app.models.free_events import", env)
        release = (root / "scripts/apply_cloud_domain_parity_release.py").read_text(encoding="utf-8")
        self.assertIn('PREVIOUS_RELEASE_REVISION = "20261009_0011"', release)
        self.assertIn('RELEASE_TARGET_REVISION = "20261009_0012"', release)
        self.assertIn('"20261002_0009"', release)


if __name__ == "__main__":
    unittest.main()
