"""Read-only source observability endpoint is owner-only and fail-closed."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import current_user


class OwnerStatusReadbackTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_unauthenticated_is_401(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/free-events/status")
        self.assertEqual(response.status_code, 401)

    def test_no_owner_allowlist_deny_even_valid_google_user(self):
        app.dependency_overrides[current_user] = lambda: {"email": "owner@example.test"}
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": ""}):
            with TestClient(app) as client:
                response = client.get("/api/v1/free-events/status")
        self.assertEqual(response.status_code, 403)

    def test_other_user_is_denied_before_db_access(self):
        app.dependency_overrides[current_user] = lambda: {"email": "other@example.test"}
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.test"}):
            with patch("app.api.free_events.read_free_events_status", new_callable=AsyncMock) as db_read:
                with TestClient(app) as client:
                    response = client.get("/api/v1/free-events/status")
                db_read.assert_not_awaited()
        self.assertEqual(response.status_code, 403)

    def test_verified_owner_gets_only_aggregate_no_store(self):
        app.dependency_overrides[current_user] = lambda: {"email": "OWNER@example.test"}
        counts = {"status": "PASS_READ_ONLY", "observation_runs": 2,
                  "current_source_events": 140, "ui_unique_visible_events": 0,
                  "last_14_days_coverage_pass": False}
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.test"}):
            with patch("app.api.free_events.read_free_events_status",
                       new_callable=AsyncMock, return_value=counts) as db_read:
                with TestClient(app) as client:
                    response = client.get("/api/v1/free-events/status")
                db_read.assert_awaited_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.json(), counts)

    def test_status_has_no_write_methods(self):
        openapi = app.openapi()["paths"]["/api/v1/free-events/status"]
        self.assertEqual(set(openapi), {"get"})

if __name__ == "__main__":
    unittest.main()
