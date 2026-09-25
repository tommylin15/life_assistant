import os
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from app.api.google_integrations import CAPABILITIES, CalendarEventCreate
from app.services import google_oauth


class GoogleIntegrationContractTests(TestCase):
    def test_default_services_use_least_privilege_scopes(self):
        services = google_oauth.normalize_services(None)
        scopes = google_oauth.scopes_for_services(services)
        self.assertIn("https://www.googleapis.com/auth/gmail.readonly", scopes)
        self.assertIn("https://www.googleapis.com/auth/calendar.events", scopes)
        self.assertIn("https://www.googleapis.com/auth/drive.file", scopes)
        self.assertNotIn("https://www.googleapis.com/auth/drive", scopes)
        self.assertNotIn("https://mail.google.com/", scopes)

    def test_authorization_url_requests_incremental_offline_consent(self):
        original_client_id = google_oauth.settings.google_client_id
        original_redirect = google_oauth.settings.google_redirect_uri
        try:
            google_oauth.settings.google_client_id = "client-id"
            google_oauth.settings.google_redirect_uri = "https://example.test/auth/callback"
            url = google_oauth.build_authorization_url("state", ("gmail", "drive"))
            query = parse_qs(urlparse(url).query)
            self.assertEqual(query["access_type"], ["offline"])
            self.assertEqual(query["prompt"], ["consent"])
            self.assertEqual(query["include_granted_scopes"], ["true"])
            self.assertIn("https://www.googleapis.com/auth/gmail.readonly", query["scope"][0])
            self.assertIn("https://www.googleapis.com/auth/drive.file", query["scope"][0])
            self.assertNotIn("https://www.googleapis.com/auth/calendar.events", query["scope"][0])
        finally:
            google_oauth.settings.google_client_id = original_client_id
            google_oauth.settings.google_redirect_uri = original_redirect

    def test_token_encryption_roundtrip_does_not_store_plaintext(self):
        original_key = os.environ.get("GOOGLE_TOKEN_ENCRYPTION_KEY")
        try:
            os.environ["GOOGLE_TOKEN_ENCRYPTION_KEY"] = "test-only-high-entropy-key"
            encrypted = google_oauth.encrypt_token("refresh-token-secret")
            self.assertNotIn("refresh-token-secret", encrypted)
            self.assertEqual(google_oauth.decrypt_token(encrypted), "refresh-token-secret")
            self.assertEqual(google_oauth.token_key_source(), "dedicated")
        finally:
            if original_key is None:
                os.environ.pop("GOOGLE_TOKEN_ENCRYPTION_KEY", None)
            else:
                os.environ["GOOGLE_TOKEN_ENCRYPTION_KEY"] = original_key

    def test_capability_catalog_contains_only_first_batch(self):
        names = {item["name"] for item in CAPABILITIES}
        self.assertEqual(
            names,
            {
                "gmail.list_metadata",
                "calendar.list",
                "calendar.create",
                "drive.bridge.ensure",
            },
        )
        self.assertNotIn("gmail.send", names)
        self.assertNotIn("calendar.delete", names)

    def test_calendar_create_requires_timezone_and_order(self):
        with self.assertRaises(ValueError):
            CalendarEventCreate(
                summary="No timezone",
                start="2026-09-25T14:00:00",
                end="2026-09-25T15:00:00",
            )
