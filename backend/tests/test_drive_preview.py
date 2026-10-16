import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Response
from app.api.drive_file_manager import preview_authorized_drive_text, _MAX_PREVIEW_BYTES


def google_result(body=None, content=b""):
    response = MagicMock()
    response.json.return_value = body
    response.content = content
    return response


class DriveTextPreviewTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_owner_token_and_no_store(self):
        db = MagicMock()
        google = AsyncMock(side_effect=[
            google_result({
                "id": "file-id", "name": "notes.md",
                "mimeType": "text/markdown", "size": "12",
            }),
            google_result(content="您好 world".encode("utf-8")),
        ])
        with patch("app.api.drive_file_manager._request_google", google):
            response = Response()
            result = await preview_authorized_drive_text(
                "file-id", response, {"sub": "person-A"}, db)
            self.assertEqual(result["text"], "您好 world")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            self.assertEqual(google.await_count, 2)
            self.assertEqual(google.await_args_list[0].args[1], "person-A")
            self.assertEqual(google.await_args_list[1].args[1], "person-A")
            self.assertEqual(google.await_args_list[1].kwargs["params"]["alt"], "media")
            db.commit.assert_not_called()

    async def test_reject_oversized_file_before_media_download(self):
        db = MagicMock()
        google = AsyncMock(return_value=google_result({
            "id": "file-id", "name": "huge.txt",
            "mimeType": "text/plain", "size": str(_MAX_PREVIEW_BYTES + 1),
        }))
        with patch("app.api.drive_file_manager._request_google", google):
            with self.assertRaises(HTTPException) as raised:
                await preview_authorized_drive_text(
                    "file-id", Response(), {"sub": "person-A"}, db)
            self.assertEqual(raised.exception.status_code, 413)
            self.assertEqual(google.await_count, 1)

    async def test_binary_file_does_not_read_content(self):
        db = MagicMock()
        google = AsyncMock(return_value=google_result({
            "id": "file-id", "name": "data.pdf",
            "mimeType": "application/pdf", "size": "123",
        }))
        with patch("app.api.drive_file_manager._request_google", google):
            with self.assertRaises(HTTPException) as raised:
                await preview_authorized_drive_text(
                    "file-id", Response(), {"sub": "person-A"}, db)
            self.assertEqual(raised.exception.status_code, 415)
            self.assertEqual(google.await_count, 1)

    async def test_invalid_google_id_rejected_before_access(self):
        google = AsyncMock()
        with patch("app.api.drive_file_manager._request_google", google):
            with self.assertRaises(HTTPException):
                await preview_authorized_drive_text(
                    "https://evil.example/", Response(), {"sub": "person-A"},
                    MagicMock())
            google.assert_not_awaited()
