"""Drive manager permissions and source readback contracts."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.drive_file_manager import (
    DriveRenameRequest, _same_instant, rename_registered_document,
)
from app.services.google_drive_files import DriveFileMetadata


def file_meta(name: str, minute: int = 0) -> DriveFileMetadata:
    return DriveFileMetadata(
        id="google-file-a", name=name, mime_type="text/plain",
        web_view_link="https://drive.google.com/file/d/google-file-a/view",
        modified_at=datetime(2026, 10, 16, 10, minute, tzinfo=timezone.utc),
    )


class DriveManagerContractTests(TestCase):
    def test_single_user_routes_share_versioned_api(self):
        from app.main import app
        routes = {route.path: route for route in app.routes}
        self.assertIn("/api/v1/drive/manager/documents/{document_id}/rename", routes)
        self.assertIn("/api/v1/integrations/google/gmail/radar/quick-scan", routes)
        self.assertNotIn("/integrations/google/gmail/radar/quick-scan", routes)
        self.assertEqual(
            {"PATCH"}, routes["/api/v1/drive/manager/documents/{document_id}/rename"].methods,
        )

    def test_empty_name_and_naive_timestamp_are_rejected(self):
        with self.assertRaises(ValidationError):
            DriveRenameRequest(name=" ", expected_modified_at="2026-10-16T10:00:00Z")
        with self.assertRaises(ValidationError):
            DriveRenameRequest(name="readme", expected_modified_at="2026-10-16T10:00:00")
        with self.assertRaises(ValidationError):
            DriveRenameRequest(name="../bad", expected_modified_at="2026-10-16T10:00:00Z")

    def test_timestamp_same_instant_normalizes_offsets(self):
        old = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
        new = datetime(2026, 10, 16, 18, 0, tzinfo=timezone(timedelta(hours=8)))
        self.assertTrue(_same_instant(old, new))


class DriveRenameIsolationTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.doc = SimpleNamespace(
            id="doc-a", user_sub="owner-A",
            google_file_id="google-file-a", name="old.txt",
            mime_type="text/plain", modified_at=file_meta("old.txt").modified_at,
            web_view_link=None,
        )
        self.body = DriveRenameRequest(
            name="new.txt", expected_modified_at=file_meta("old.txt").modified_at,
        )

    async def test_owner_mismatch_never_calls_google(self):
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock) as owned,
            patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock) as google,
        ):
            owned.side_effect = HTTPException(404, "Not found")
            with self.assertRaises(HTTPException) as exc:
                await rename_registered_document(
                    "doc-b", self.body, {"sub": "owner-A"}, self.db)
            self.assertEqual(exc.exception.status_code, 404)
            owned.assert_awaited_once_with(self.db, "owner-A", "doc-b")
            google.assert_not_awaited()

    async def test_stale_drive_source_is_rejected_without_write(self):
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=self.doc),
            patch("app.api.drive_file_manager.get_drive_file_metadata", new_callable=AsyncMock,
                  return_value=file_meta("old.txt", 1)),
            patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock) as google,
        ):
            with self.assertRaises(HTTPException) as exc:
                await rename_registered_document(
                    "doc-a", self.body, {"sub": "owner-A"}, self.db)
            self.assertEqual(exc.exception.status_code, 409)
            google.assert_not_awaited()
            self.db.commit.assert_not_awaited()

    async def test_google_and_database_readback_match_before_commit(self):
        response = MagicMock()
        response.json.return_value = {"id": "google-file-a", "name": "new.txt"}
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=self.doc),
            patch("app.api.drive_file_manager.get_drive_file_metadata", new_callable=AsyncMock,
                  side_effect=[file_meta("old.txt"), file_meta("new.txt", 1)]) as metadata,
            patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock,
                  return_value=response) as google,
        ):
            renamed = await rename_registered_document(
                "doc-a", self.body, {"sub": "owner-A"}, self.db)
            self.assertEqual(renamed.name, "new.txt")
            self.assertEqual(self.doc.user_sub, "owner-A")
            self.assertEqual(metadata.await_count, 2)
            self.assertEqual(google.await_args.args[1], "owner-A")
            self.assertEqual(google.await_args.kwargs["json"], {"name": "new.txt"})
            self.db.commit.assert_awaited_once()
