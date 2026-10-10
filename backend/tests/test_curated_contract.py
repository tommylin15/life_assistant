"""Curated and UI-admin API safety regressions; no external services."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.api.auth import current_user
from app.db.session import get_db
from app.api.curated import CuratedBatchIn, normalize_url, identity
from app.api.ui_policies import UIPreferencesWrite, AIPolicyWrite, FEATURES, _default_rollout


class CuratedContractTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_url_canonical_identity_and_occurrence_split(self):
        url = normalize_url("https://example.org/show?utm_source=mail&id=4&fbclid=x")
        self.assertEqual(url, "https://example.org/show?id=4")
        first = CuratedBatchIn.model_validate({"items": [
            {"title": "Activity", "original_url": "https://example.org/show?id=4&fbclid=x"}
        ]}).items[0]
        retry = CuratedBatchIn.model_validate({"items": [
            {"title": "New title", "original_url": "https://example.org/show?utm_medium=c&id=4"}
        ]}).items[0]
        second_session = retry.model_copy(update={"occurrence_key": "session2"})
        self.assertEqual(identity(first), identity(retry))
        self.assertNotEqual(identity(first), identity(second_session))

    def test_rejects_unsafe_sources_bad_fees_dates_and_unbounded_batch(self):
        for url in ("http://example.org/a", "https://127.0.0.1/secret",
                    "https://localhost/a", "https://user:pass@example.org/path",
                    "https://example.org:9000/a", "https://metadata.google.internal/test"):
            with self.subTest(url=url), self.assertRaises(ValidationError):
                CuratedBatchIn.model_validate({"items": [
                    {"title": "Event", "original_url": url}
                ]})
        for extra in (
            {"fee_kind": "free", "fee_amount": "20.00"},
            {"importance": 6}, {"registration_status": "verified"},
            {"starts_on": "2026-10-20", "ends_on": "2026-10-19"},
        ):
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                CuratedBatchIn.model_validate({"items": [
                    {"title": "Event", "original_url": "https://example.org/e", **extra}
                ]})
        with self.assertRaises(ValidationError):
            CuratedBatchIn.model_validate({"items": [
                {"title": "Event", "original_url": "https://example.org/e"}
                for _ in range(41)
            ]})

    def test_writer_fails_closed_without_secret_or_on_wrong_token(self):
        with patch.dict(os.environ, {"LIFE_CURATED_INGEST_TOKEN": "a" * 40}):
            with TestClient(app) as client:
                for headers in ({}, {"Authorization": "Bearer incorrect"}):
                    response = client.post("/api/v1/free-events/curated:batch",
                        json={"items": [{"title": "Event", "original_url": "https://example.org/e"}]},
                        headers=headers)
                    self.assertEqual(response.status_code, 401)
        with patch.dict(os.environ, {"LIFE_CURATED_INGEST_TOKEN": ""}):
            with TestClient(app) as client:
                result = client.post("/api/v1/free-events/curated:batch", json={"items": [
                    {"title": "Event", "original_url": "https://example.org/e"}]})
                self.assertEqual(result.status_code, 503)

    def test_user_browse_requires_session_and_admin_requires_owner(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/api/v1/free-events/curated").status_code, 401)
            self.assertEqual(client.get("/api/v1/me/ui-preferences").status_code, 401)
        app.dependency_overrides[current_user] = lambda: {"sub": "other", "email": "other@example.org"}
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "owner@example.org"}):
            with TestClient(app) as client:
                self.assertEqual(client.get("/api/v1/admin/ai/providers").status_code, 403)
                self.assertEqual(client.get("/api/v1/admin/feature-rollouts").status_code, 403)
                self.assertEqual(client.post("/api/v1/admin/ai/probe/gemini").status_code, 403)

    def test_owner_prefs_and_ai_allowlists_cannot_be_forged(self):
        for body in (
            {"expected_revision": 0, "pinned": ["tasks", "tasks"],
             "more_order": [], "home_cards": []},
            {"expected_revision": 0, "pinned": ["admin"], "more_order": [], "home_cards": []},
            {"expected_revision": 0, "pinned": [], "more_order": [], "home_cards": ["unknown"]},
        ):
            with self.assertRaises(ValidationError):
                UIPreferencesWrite.model_validate(body)
        with self.assertRaises(ValidationError):
            AIPolicyWrite.model_validate({"expected_revision": 0,
                "enabled": True, "allowed_providers": ["gemini", "gemini"]})
        self.assertNotIn("admin", FEATURES)
        self.assertEqual(_default_rollout("events"), ("beta", "owner"))


if __name__ == "__main__":
    unittest.main()
