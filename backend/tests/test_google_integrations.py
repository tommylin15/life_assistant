import os
from unittest import TestCase
from urllib.parse import parse_qs, urlparse

from app.api.google_integrations import (
    CAPABILITIES,
    CalendarEventCreate,
    CalendarEventUpdate,
    GmailToCalendarCreate,
    GmailToTaskCreate,
)
from app.api.google_project import GmailToProjectCreate
from app.models.task import TaskPriority
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
            google_oauth.settings.google_redirect_uri = (
                "https://example.test/auth/callback"
            )
            url = google_oauth.build_authorization_url(
                "state", ("gmail", "drive")
            )
            query = parse_qs(urlparse(url).query)
            self.assertEqual(query["access_type"], ["offline"])
            self.assertEqual(query["prompt"], ["consent"])
            self.assertEqual(query["include_granted_scopes"], ["true"])
            self.assertIn(
                "https://www.googleapis.com/auth/gmail.readonly",
                query["scope"][0],
            )
            self.assertIn(
                "https://www.googleapis.com/auth/drive.file",
                query["scope"][0],
            )
            self.assertNotIn(
                "https://www.googleapis.com/auth/calendar.events",
                query["scope"][0],
            )
        finally:
            google_oauth.settings.google_client_id = original_client_id
            google_oauth.settings.google_redirect_uri = original_redirect

    def test_token_encryption_roundtrip_does_not_store_plaintext(self):
        original_key = os.environ.get("GOOGLE_TOKEN_ENCRYPTION_KEY")
        try:
            os.environ["GOOGLE_TOKEN_ENCRYPTION_KEY"] = (
                "test-only-high-entropy-key"
            )
            encrypted = google_oauth.encrypt_token("refresh-token-secret")
            self.assertNotIn("refresh-token-secret", encrypted)
            self.assertEqual(
                google_oauth.decrypt_token(encrypted),
                "refresh-token-secret",
            )
            self.assertEqual(google_oauth.token_key_source(), "dedicated")
        finally:
            if original_key is None:
                os.environ.pop("GOOGLE_TOKEN_ENCRYPTION_KEY", None)
            else:
                os.environ["GOOGLE_TOKEN_ENCRYPTION_KEY"] = original_key

    def test_capability_catalog_contains_project_conversion(self):
        by_name = {item["name"]: item for item in CAPABILITIES}
        self.assertEqual(
            set(by_name),
            {
                "gmail.list_metadata",
                "gmail.to_task",
                "gmail.to_calendar",
                "gmail.to_project",
                "calendar.list",
                "calendar.create",
                "calendar.update",
                "calendar.delete",
                "drive.bridge.ensure",
            },
        )
        self.assertNotIn("gmail.send", by_name)
        self.assertEqual(
            by_name["calendar.delete"]["confirmation"],
            "explicit_user",
        )
        self.assertEqual(
            set(by_name["gmail.to_calendar"]["required_scopes"]),
            {
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/calendar.events",
            },
        )
        self.assertEqual(
            by_name["gmail.to_project"]["required_scopes"],
            ["https://www.googleapis.com/auth/gmail.readonly"],
        )

    def test_calendar_create_requires_timezone_and_order(self):
        with self.assertRaises(ValueError):
            CalendarEventCreate(
                summary="No timezone",
                start="2026-09-25T14:00:00",
                end="2026-09-25T15:00:00",
            )
        with self.assertRaises(ValueError):
            CalendarEventCreate(
                summary="Bad order",
                start="2026-09-25T15:00:00+08:00",
                end="2026-09-25T14:00:00+08:00",
            )

    def test_calendar_update_requires_fields_and_paired_times(self):
        with self.assertRaises(ValueError):
            CalendarEventUpdate()
        with self.assertRaises(ValueError):
            CalendarEventUpdate(start="2026-09-25T14:00:00+08:00")
        with self.assertRaises(ValueError):
            CalendarEventUpdate(summary=None)

        update = CalendarEventUpdate(summary="Updated")
        self.assertEqual(update.summary, "Updated")

        timed = CalendarEventUpdate(
            start="2026-09-25T14:00:00+08:00",
            end="2026-09-25T15:00:00+08:00",
        )
        self.assertIsNotNone(timed.start)
        self.assertIsNotNone(timed.end)

    def test_gmail_to_calendar_requires_explicit_valid_time_range(self):
        with self.assertRaises(ValueError):
            GmailToCalendarCreate(
                start="2026-09-25T14:00:00",
                end="2026-09-25T15:00:00",
            )
        with self.assertRaises(ValueError):
            GmailToCalendarCreate(
                start="2026-09-25T15:00:00+08:00",
                end="2026-09-25T14:00:00+08:00",
            )

        body = GmailToCalendarCreate(
            start="2026-09-25T14:00:00+08:00",
            end="2026-09-25T15:00:00+08:00",
        )
        self.assertIsNone(body.summary)

    def test_gmail_to_task_uses_normal_priority_by_default(self):
        body = GmailToTaskCreate()
        self.assertEqual(body.priority, TaskPriority.normal)

    def test_gmail_to_project_uses_active_status_by_default(self):
        body = GmailToProjectCreate()
        self.assertEqual(body.status, "active")
        self.assertIsNone(body.name)
