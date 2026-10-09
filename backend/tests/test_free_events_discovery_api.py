"""Verified-only M2 read-only free-event contract tests, no real database."""
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.main import app
from app.api.auth import current_user
from app.db.session import get_db
from app.services.free_events_discovery import (
    as_verified_card, list_verified_public_events, verified_catalog_query,
)


class FreeEventDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 9, 4, tzinfo=timezone.utc)
        self.event = SimpleNamespace(
            id="event-1", title="免費展覽", summary="已人工核對", category="展覽",
            official_url="https://organizer.example.tw/1"
        )
        self.session = SimpleNamespace(
            id="session-1", city="台北", venue="文化中心",
            starts_at=self.now + timedelta(days=2), ends_at=self.now + timedelta(days=2, hours=1),
            starts_on=None, ends_on_exclusive=None, timezone_name="Asia/Taipei"
        )
        self.registration = SimpleNamespace(
            id="opportunity-1", fee_kind="free", fee_amount=Decimal("0.00"),
            fee_currency="TWD", eligibility_note=None,
            registration_url="https://organizer.example.tw/register",
            registration_opens_at=None, registration_closes_at=None,
            registration_status="open", last_verified_at=self.now - timedelta(hours=1),
        )

    def test_select_sql_filters_only_verified_free_official_active_sources(self):
        query = verified_catalog_query(now=self.now, limit=20, offset=0)
        compiled = query.compile(dialect=postgresql.dialect())
        sql = str(compiled)
        self.assertIn("free_events.verification_status =", sql)
        self.assertIn("free_events.last_verified_at IS NOT NULL", sql)
        self.assertIn("free_event_sources.fetch_enabled IS true", sql)
        self.assertIn("free_event_sources.access_review =", sql)
        self.assertIn("free_event_registration_opportunities.official_verified IS true", sql)
        self.assertIn("free_event_registration_opportunities.registration_url IS NOT NULL", sql)
        self.assertIn("free_event_sessions.is_cancelled IS false", sql)
        self.assertIn("free_event_registration_opportunities.fee_kind IN", sql)
        self.assertIn("free_event_sessions.starts_on", sql)
        self.assertIn("LIMIT", sql)
        self.assertIn("OFFSET", sql)
        parameters = str(compiled.params)
        self.assertIn("reviewed_with_evidence", parameters)
        self.assertIn("verified", parameters)

    def test_ambiguous_open_status_never_claims_confirmed_window(self):
        card = as_verified_card(self.event, self.session, self.registration, now=self.now)
        self.assertFalse(card.window_confirmed_open)
        self.assertEqual(card.registration_status, "open")
        self.assertEqual(card.notice, "external_registration_requires_recheck")
        self.assertIsNone(card.registration_opens_at)

    def test_window_requires_explicit_both_bounds(self):
        self.registration.registration_opens_at = self.now - timedelta(hours=1)
        self.registration.registration_closes_at = self.now + timedelta(hours=1)
        self.assertTrue(as_verified_card(self.event, self.session, self.registration,
                                         now=self.now).window_confirmed_open)
        self.registration.registration_closes_at = None
        self.assertFalse(as_verified_card(self.event, self.session, self.registration,
                                          now=self.now).window_confirmed_open)
        self.registration.registration_closes_at = self.now + timedelta(hours=1)
        self.registration.registration_status = "full"
        self.assertFalse(as_verified_card(self.event, self.session, self.registration,
                                          now=self.now).window_confirmed_open)

    def test_missing_official_or_registration_proof_is_not_renderable(self):
        self.event.official_url = None
        with self.assertRaises(ValueError):
            as_verified_card(self.event, self.session, self.registration, now=self.now)
        self.event.official_url = "https://organizer.example.tw/1"
        self.registration.registration_url = None
        with self.assertRaises(ValueError):
            as_verified_card(self.event, self.session, self.registration, now=self.now)

    async def test_read_service_never_writes_and_is_bounded(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.execute.return_value.all.return_value = [
            (self.event, self.session, self.registration)
        ]
        result = await list_verified_public_events(
            db, limit=15, offset=0, now=self.now
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].title, "免費展覽")
        db.execute.assert_awaited_once()
        for invalid in (
            {"limit": 0}, {"limit": 51}, {"offset": -1}, {"offset": 5001}
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                await list_verified_public_events(db, now=self.now, **invalid)
        self.assertEqual(db.execute.await_count, 1)


class FreeEventDiscoveryApiTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_registered_with_bounded_query_and_no_writes(self):
        path = app.openapi()["paths"]["/api/v1/free-events"]
        self.assertIn("get", path)
        for method in ("post", "patch", "delete", "put"):
            self.assertNotIn(method, path)
        app.openapi_schema = None

    def test_unauthenticated_request_returns_401(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/free-events")
        self.assertEqual(response.status_code, 401)
        self.assertIn("error", response.json())

    def test_authenticated_empty_read_is_no_store(self):
        db = MagicMock()
        db.execute = AsyncMock()
        db.execute.return_value.all.return_value = []
        app.dependency_overrides[current_user] = lambda: {"sub": "synthetic-owner"}
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            response = client.get("/api/v1/free-events")
            assert response.status_code == 200, response.text
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.json()["returned"], 0)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["policy"], "verified_public_catalog_only")
        db.execute.assert_awaited_once()

    def test_limit_validation_at_api_boundary(self):
        app.dependency_overrides[current_user] = lambda: {"sub": "synthetic-owner"}
        app.dependency_overrides[get_db] = lambda: MagicMock()
        with TestClient(app) as client:
            for query in ("?limit=100", "?limit=0", "?offset=-2"):
                with self.subTest(query=query):
                    response = client.get("/api/v1/free-events" + query)
                    self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
