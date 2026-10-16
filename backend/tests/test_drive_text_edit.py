"""Contract tests for bounded, owner-scoped Google Drive inline text edits."""
import hashlib
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from pydantic import ValidationError
from app.api.drive_file_manager import DriveTextEdit, save_registered_drive_text


def fake_google(payload=None, raw=b""):
    response = MagicMock()
    response.json.return_value = payload
    response.content = raw
    return response


def spec(text="Updated text", version="17", source=b"Initial text"):
    return DriveTextEdit(text=text, expected_version=version,
                         expected_sha256=hashlib.sha256(source).hexdigest())


def meta(mime="text/plain", version="17", can_edit=True):
    return {
        "id": "google-id-1", "name": "note.txt", "mimeType": mime,
        "version": version, "size": 12, "modifiedTime": "2026-10-16T13:30:00Z",
        "capabilities": {"canEdit": can_edit},
    }


class DriveTextEditValidation(TestCase):
    def test_unicode_limit_is_utf8_bytes_not_characters(self):
        with self.assertRaises(ValidationError):
            spec(text="測" * 23000)

    def test_hash_and_version_are_required(self):
        with self.assertRaises(ValidationError):
            DriveTextEdit(text="new", expected_version="", expected_sha256="abc")


class DriveTextEditTests(IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.db.commit = AsyncMock()
        self.doc = SimpleNamespace(
            user_sub="owner-a", google_file_id="google-id-1",
            name="note.txt", modified_at=None, mime_type="text/plain")

    async def test_foreign_document_cannot_trigger_google_read(self):
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  side_effect=HTTPException(404, "No document")) as owner,
            patch("app.api.drive_file_manager._request_google",
                  new_callable=AsyncMock) as google,
        ):
            with self.assertRaises(HTTPException) as context:
                await save_registered_drive_text(
                    "some-other-doc", spec(), {"sub": "owner-a"}, self.db)
            self.assertEqual(context.exception.status_code, 404)
            owner.assert_awaited_once_with(self.db, "owner-a", "some-other-doc")
            google.assert_not_awaited()

    async def test_stale_version_and_read_only_never_upload(self):
        for metadata, expected_status in [(meta(version="18"), 409),
                                          (meta(can_edit=False), 403)]:
            with (
                patch("app.api.drive_file_manager.get_document",
                      new_callable=AsyncMock, return_value=self.doc),
                patch("app.api.drive_file_manager._request_google",
                      new_callable=AsyncMock,
                      return_value=fake_google(metadata)) as google,
            ):
                with self.assertRaises(HTTPException) as context:
                    await save_registered_drive_text(
                        "doc-1", spec(), {"sub": "owner-a"}, self.db)
                self.assertEqual(context.exception.status_code, expected_status)
                self.assertEqual(google.await_count, 1)

    async def test_content_hash_changed_never_uploads(self):
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=self.doc),
            patch("app.api.drive_file_manager._request_google",
                  new_callable=AsyncMock, side_effect=[
                      fake_google(meta()), fake_google(raw=b"changed after preview"),
                  ]) as google,
        ):
            with self.assertRaises(HTTPException) as context:
                await save_registered_drive_text("doc-1", spec(),
                                                {"sub": "owner-a"}, self.db)
            self.assertEqual(context.exception.status_code, 409)
            self.assertEqual(google.await_count, 2)

    async def test_google_media_patch_and_readback_before_commit(self):
        updated=b"Updated text"
        after={"id": "google-id-1", "name": "note.txt",
               "mimeType": "text/plain", "version": "18",
               "modifiedTime": "2026-10-16T13:35:00Z"}
        google = AsyncMock(side_effect=[
            fake_google(meta()), fake_google(raw=b"Initial text"),
            fake_google({"id": "google-id-1"}),
            fake_google(raw=updated), fake_google(after),
        ])
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=self.doc),
            patch("app.api.drive_file_manager._request_google", google),
        ):
            result=await save_registered_drive_text(
                "doc-1", spec(), {"sub":"owner-a"}, self.db)
        self.assertTrue(result["verified"])
        self.assertFalse(result["unchanged"])
        self.assertEqual(result["version"], "18")
        self.assertEqual(google.await_count, 5)
        update = google.await_args_list[2]
        self.assertEqual(update.args[1], "owner-a")
        self.assertEqual(update.args[3], "PATCH")
        self.assertIn("/upload/drive/v3/files/google-id-1", update.args[4])
        self.assertEqual(update.kwargs["params"]["uploadType"], "media")
        self.assertEqual(update.kwargs["content"], updated)
        self.db.commit.assert_awaited_once()
        self.assertEqual(self.doc.name, "note.txt")

    async def test_verify_failure_never_reports_success_or_commits(self):
        google = AsyncMock(side_effect=[
            fake_google(meta()), fake_google(raw=b"Initial text"),
            fake_google({"id": "google-id-1"}),
            fake_google(raw=b"wrong readback"),
        ])
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=self.doc),
            patch("app.api.drive_file_manager._request_google", google),
        ):
            with self.assertRaises(HTTPException) as error:
                await save_registered_drive_text(
                    "doc-1", spec(), {"sub": "owner-a"}, self.db)
        self.assertEqual(error.exception.status_code, 502)
        self.db.commit.assert_not_awaited()

    async def test_unchanged_text_is_noop(self):
        google=AsyncMock(side_effect=[
            fake_google(meta()), fake_google(raw=b"Initial text"),
        ])
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=self.doc),
            patch("app.api.drive_file_manager._request_google", google),
        ):
            result=await save_registered_drive_text(
                "doc-1", spec(text="Initial text"), {"sub": "owner-a"}, self.db)
        self.assertTrue(result["unchanged"])
        self.assertEqual(google.await_count,2)
        self.db.commit.assert_not_awaited()
