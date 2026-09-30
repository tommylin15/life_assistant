import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class GoogleDriveFilesTests(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_fetch_uses_drive_file_scope_and_minimum_fields(self):
        from app.services.google_drive_files import get_drive_file_metadata

        response = MagicMock()
        response.json.return_value = {
            "id": "file-1",
            "name": "Spec",
            "mimeType": "application/vnd.google-apps.document",
            "webViewLink": "https://docs.google.com/document/d/file-1/edit",
            "modifiedTime": "2026-09-30T10:00:00Z",
            "parents": ["folder-1"],
        }
        request = AsyncMock(return_value=response)
        with patch("app.services.google_drive_files.request_google", request):
            metadata = await get_drive_file_metadata(MagicMock(), "user-a", "file-1")

        self.assertEqual(metadata.id, "file-1")
        self.assertEqual(metadata.name, "Spec")
        self.assertEqual(metadata.parents, ("folder-1",))
        call = request.await_args
        self.assertIn("drive.file", call.args[2])
        self.assertEqual(call.args[3], "GET")
        fields = call.kwargs["params"]["fields"]
        self.assertIn("id", fields)
        self.assertIn("mimeType", fields)
        self.assertNotIn("permissions", fields)

    async def test_google_doc_exports_plain_text_and_binary_is_unsupported(self):
        from app.services.google_drive_files import (
            GOOGLE_DOC_MIME,
            read_drive_text,
        )

        response = MagicMock()
        response.text = "hello\nworld"
        request = AsyncMock(return_value=response)
        with patch("app.services.google_drive_files.request_google", request):
            result = await read_drive_text(MagicMock(), "user-a", "file-1", GOOGLE_DOC_MIME)
        self.assertTrue(result.supported)
        self.assertEqual(result.text, "hello\nworld")
        self.assertTrue(request.await_args.args[4].endswith("/export"))
        self.assertEqual(request.await_args.kwargs["params"]["mimeType"], "text/plain")

        request.reset_mock()
        result = await read_drive_text(
            MagicMock(), "user-a", "file-2", "application/pdf"
        )
        self.assertFalse(result.supported)
        self.assertIsNone(result.text)
        request.assert_not_awaited()

    async def test_stored_text_file_downloads_as_bounded_text(self):
        from app.services.google_drive_files import read_drive_text

        response = MagicMock()
        response.text = "a" * 20000
        request = AsyncMock(return_value=response)
        with patch("app.services.google_drive_files.request_google", request):
            result = await read_drive_text(
                MagicMock(), "user-a", "file-3", "text/markdown"
            )
        self.assertTrue(result.supported)
        self.assertLessEqual(len(result.text or ""), 12000)
        self.assertEqual(request.await_args.kwargs["params"], {"alt": "media"})


if __name__ == "__main__":
    unittest.main()
