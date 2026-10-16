import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, Response
from pydantic import ValidationError

from app.api.drive_file_manager import (
    DriveCreateFolder, DriveMoveDocument, _file_id, _q_escape,
    create_authorized_drive_folder, list_authorized_drive_files,
    move_registered_drive_document,
)
from app.services.google_drive_files import DriveFileMetadata


def response(payload):
    obj = MagicMock()
    obj.json.return_value = payload
    return obj


class DriveExplorerValidationTests(unittest.TestCase):
    def test_escape_drive_query_literals(self):
        self.assertEqual(_q_escape("O'Brien"), "O\\'Brien")
        self.assertEqual(_q_escape("a\\b"), "a\\\\b")

    def test_only_file_identifiers_pass_folder_check(self):
        for value in ("../../admin", "https://drive.google.com/id", "", "a b"):
            with self.subTest(value=value), self.assertRaises(HTTPException):
                _file_id(value)
        self.assertEqual(_file_id("Folder-123_ab"), "Folder-123_ab")

    def test_create_folder_and_move_disallow_untrusted_payload(self):
        with self.assertRaises(ValidationError):
            DriveCreateFolder(name="hello/../../world")
        with self.assertRaises(ValidationError):
            DriveMoveDocument(destination_folder_id="f", expected_modified_at="2026-10-16T13:00:00")


class DriveExplorerBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_is_user_scoped_and_paged(self):
        db = MagicMock()
        payload = {"files": [{"id": "file-1", "name": "Notes", "mimeType": "text/plain"}],
                   "nextPageToken": "second"}
        with patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock,
                   return_value=response(payload)) as google:
            http = Response()
            result = await list_authorized_drive_files(
                response=http, folder_id=None, q="O'Brien",
                page_token=None, page_size=20, user={"sub": "person-a"}, db=db)
            self.assertEqual(result["visibility"], "app_authorized_only")
            self.assertEqual(result["next_page_token"], "second")
            self.assertEqual(http.headers["Cache-Control"], "no-store")
            self.assertEqual(google.await_args.args[1], "person-a")
            self.assertIn("O\\'Brien", google.await_args.kwargs["params"]["q"])
            self.assertNotIn("allDrives", str(google.await_args.kwargs["params"]))

    async def test_folder_scope_verified_before_listing(self):
        db = MagicMock()
        with (
            patch("app.api.drive_file_manager._authorized_folder",
                  new_callable=AsyncMock, return_value="folder-1") as folder,
            patch("app.api.drive_file_manager._request_google",
                  new_callable=AsyncMock, return_value=response({"files": []})) as google,
        ):
            await list_authorized_drive_files(
                response=Response(), folder_id="folder-1", q=None,
                page_token=None, page_size=50, user={"sub": "person-a"}, db=db)
            folder.assert_awaited_once_with(db, "person-a", "folder-1")
            self.assertIn("'folder-1' in parents",
                          google.await_args.kwargs["params"]["q"])

    async def test_owner_authentication_precedes_folder_write(self):
        db = MagicMock()
        db.commit = AsyncMock()
        with (
            patch("app.api.drive_file_manager._authorized_folder",
                  new_callable=AsyncMock, return_value="folder-1") as authorized,
            patch("app.api.drive_file_manager._request_google",
                  new_callable=AsyncMock, return_value=response({
                      "id": "new-folder", "name": "Work", "mimeType": "application/vnd.google-apps.folder"
                  })) as google,
            patch("app.api.drive_file_manager.get_drive_file_metadata",
                  new_callable=AsyncMock, return_value=DriveFileMetadata(
                    id="new-folder", name="Work",
                    mime_type="application/vnd.google-apps.folder",
                    web_view_link=None, modified_at=None)),
        ):
            result = await create_authorized_drive_folder(
                body=DriveCreateFolder(name="Work", parent_id="folder-1"),
                user={"sub": "person-a"}, db=db)
            self.assertEqual(result["id"], "new-folder")
            authorized.assert_awaited_once_with(db, "person-a", "folder-1")
            self.assertEqual(google.await_args.kwargs["json"]["parents"], ["folder-1"])

    async def test_move_cannot_read_other_users_registered_documents(self):
        db = MagicMock()
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  side_effect=HTTPException(404, "Not found")) as lookup,
            patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock) as google,
        ):
            with self.assertRaises(HTTPException):
                await move_registered_drive_document(
                    document_id="user-b-document",
                    body=DriveMoveDocument(
                        destination_folder_id="folder-a",
                        expected_modified_at="2026-10-16T12:00:00Z"),
                    user={"sub": "user-a"}, db=db)
            lookup.assert_awaited_once_with(db, "user-a", "user-b-document")
            google.assert_not_awaited()

    async def test_stale_source_fails_without_drive_move(self):
        db = MagicMock()
        doc = SimpleNamespace(
            id="doc-1", google_file_id="google-file-1",
            user_sub="person-a")
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=doc),
            patch("app.api.drive_file_manager._authorized_folder", new_callable=AsyncMock,
                  return_value="folder-new"),
            patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock,
                  return_value=response({
                      "id": "google-file-1", "modifiedTime": "2026-10-16T12:01:00Z",
                      "parents": ["folder-old"],
                  })) as google,
        ):
            with self.assertRaises(HTTPException) as context:
                await move_registered_drive_document(
                    document_id="doc-1",
                    body=DriveMoveDocument(
                        destination_folder_id="folder-new",
                        expected_modified_at="2026-10-16T12:00:00Z"),
                    user={"sub": "person-a"}, db=db)
            self.assertEqual(context.exception.status_code, 409)
            self.assertEqual(google.await_count, 1)

    async def test_move_google_readback_and_database_commit(self):
        db = MagicMock()
        db.commit = AsyncMock()
        doc = SimpleNamespace(id="doc-1", google_file_id="google-file-1",
                              user_sub="person-a", modified_at=None)
        old = {"id": "google-file-1", "modifiedTime": "2026-10-16T12:00:00Z",
               "parents": ["folder-old"]}
        moved = {"id": "google-file-1", "modifiedTime": "2026-10-16T12:01:00Z",
                 "parents": ["folder-new"]}
        with (
            patch("app.api.drive_file_manager.get_document", new_callable=AsyncMock,
                  return_value=doc),
            patch("app.api.drive_file_manager._authorized_folder", new_callable=AsyncMock,
                  return_value="folder-new"),
            patch("app.api.drive_file_manager._request_google", new_callable=AsyncMock,
                  side_effect=[response(old), response(moved), response(moved)]) as google,
        ):
            result = await move_registered_drive_document(
                document_id="doc-1",
                body=DriveMoveDocument(destination_folder_id="folder-new",
                                       expected_modified_at="2026-10-16T12:00:00Z"),
                user={"sub": "person-a"}, db=db)
            self.assertFalse(result["unchanged"])
            self.assertEqual(google.await_count, 3)
            self.assertEqual(google.await_args_list[1].kwargs["params"]["addParents"], "folder-new")
            self.assertEqual(google.await_args_list[1].kwargs["params"]["removeParents"], "folder-old")
            db.commit.assert_awaited_once()
