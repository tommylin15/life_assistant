from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.services import google_drive_files


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    @property
    def text(self):
        return self._payload if isinstance(self._payload, str) else ""


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse], calls: list[dict]):
        self._responses = responses
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, *, headers: dict, params: dict):
        self._calls.append({"url": url, "headers": headers, "params": params})
        return self._responses.pop(0)


class GoogleDriveFileAdapterTests(IsolatedAsyncioTestCase):
    async def test_metadata_request_uses_drive_file_scope_bearer_and_minimal_fields(self):
        responses = [
            _FakeResponse(
                200,
                {
                    "id": "file-1",
                    "name": "Roadmap",
                    "mimeType": "application/vnd.google-apps.document",
                    "webViewLink": "https://docs.google.com/document/d/file-1/edit",
                    "modifiedTime": "2026-10-01T07:00:00Z",
                },
            )
        ]
        calls: list[dict] = []
        fake_token = AsyncMock(return_value="drive-token")

        with (
            patch.object(google_drive_files, "get_access_token", fake_token),
            patch.object(
                google_drive_files.httpx,
                "AsyncClient",
                side_effect=lambda **_kwargs: _FakeClient(responses, calls),
            ),
        ):
            metadata = await google_drive_files.get_drive_file_metadata(
                AsyncMock(),
                "user-a",
                "file-1",
            )

        self.assertEqual(metadata.id, "file-1")
        self.assertEqual(metadata.name, "Roadmap")
        self.assertEqual(
            metadata.mime_type,
            "application/vnd.google-apps.document",
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer drive-token")
        self.assertEqual(
            calls[0]["params"],
            {"fields": "id,name,mimeType,webViewLink,modifiedTime"},
        )
        fake_token.assert_awaited_once_with(
            fake_token.call_args.args[0],
            "user-a",
            "https://www.googleapis.com/auth/drive.file",
        )

    async def test_unauthorized_response_refreshes_token_once(self):
        responses = [
            _FakeResponse(401, {}),
            _FakeResponse(
                200,
                {
                    "id": "file-1",
                    "name": "Roadmap",
                    "mimeType": "text/plain",
                    "modifiedTime": "2026-10-01T07:00:00Z",
                },
            ),
        ]
        calls: list[dict] = []
        fake_token = AsyncMock(side_effect=["old-token", "new-token"])

        with (
            patch.object(google_drive_files, "get_access_token", fake_token),
            patch.object(
                google_drive_files.httpx,
                "AsyncClient",
                side_effect=lambda **_kwargs: _FakeClient(responses, calls),
            ),
        ):
            metadata = await google_drive_files.get_drive_file_metadata(
                AsyncMock(),
                "user-a",
                "file-1",
            )

        self.assertEqual(metadata.id, "file-1")
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["headers"]["Authorization"], "Bearer old-token")
        self.assertEqual(calls[1]["headers"]["Authorization"], "Bearer new-token")
        self.assertTrue(fake_token.await_args_list[1].kwargs["force_refresh"])

    async def test_permission_loss_surfaces_stable_reauthorization_error(self):
        responses = [_FakeResponse(403, {})]
        calls: list[dict] = []

        with (
            patch.object(
                google_drive_files,
                "get_access_token",
                AsyncMock(return_value="drive-token"),
            ),
            patch.object(
                google_drive_files.httpx,
                "AsyncClient",
                side_effect=lambda **_kwargs: _FakeClient(responses, calls),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await google_drive_files.get_drive_file_metadata(
                    AsyncMock(),
                    "user-a",
                    "file-1",
                )

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("permission", str(raised.exception.detail).lower())

    async def test_mismatched_file_id_is_rejected(self):
        responses = [
            _FakeResponse(
                200,
                {
                    "id": "other-file",
                    "name": "Roadmap",
                    "mimeType": "text/plain",
                },
            )
        ]
        calls: list[dict] = []

        with (
            patch.object(
                google_drive_files,
                "get_access_token",
                AsyncMock(return_value="drive-token"),
            ),
            patch.object(
                google_drive_files.httpx,
                "AsyncClient",
                side_effect=lambda **_kwargs: _FakeClient(responses, calls),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await google_drive_files.get_drive_file_metadata(
                    AsyncMock(),
                    "user-a",
                    "file-1",
                )

        self.assertEqual(raised.exception.status_code, 502)

    async def test_google_doc_text_is_exported_as_plain_text(self):
        read_drive_text = getattr(google_drive_files, "read_drive_text", None)
        self.assertTrue(callable(read_drive_text))
        if not callable(read_drive_text):
            return

        responses = [
            _FakeResponse(
                200,
                {
                    "id": "file-1",
                    "name": "Roadmap",
                    "mimeType": "application/vnd.google-apps.document",
                },
            ),
            _FakeResponse(200, "Snapshot body"),
        ]
        calls: list[dict] = []
        with (
            patch.object(
                google_drive_files,
                "get_access_token",
                AsyncMock(return_value="drive-token"),
            ),
            patch.object(
                google_drive_files.httpx,
                "AsyncClient",
                side_effect=lambda **_kwargs: _FakeClient(responses, calls),
            ),
        ):
            result = await read_drive_text(AsyncMock(), "user-a", "file-1")

        self.assertTrue(result.supported)
        self.assertEqual(result.text, "Snapshot body")
        self.assertEqual(result.source_mime_type, "application/vnd.google-apps.document")
        self.assertEqual(calls[1]["url"], "https://www.googleapis.com/drive/v3/files/file-1/export")
        self.assertEqual(calls[1]["params"], {"mimeType": "text/plain"})

    async def test_unsupported_binary_is_reported_without_media_download(self):
        read_drive_text = getattr(google_drive_files, "read_drive_text", None)
        self.assertTrue(callable(read_drive_text))
        if not callable(read_drive_text):
            return

        responses = [
            _FakeResponse(
                200,
                {
                    "id": "file-1",
                    "name": "Attachment.pdf",
                    "mimeType": "application/pdf",
                },
            )
        ]
        calls: list[dict] = []
        with (
            patch.object(
                google_drive_files,
                "get_access_token",
                AsyncMock(return_value="drive-token"),
            ),
            patch.object(
                google_drive_files.httpx,
                "AsyncClient",
                side_effect=lambda **_kwargs: _FakeClient(responses, calls),
            ),
        ):
            result = await read_drive_text(AsyncMock(), "user-a", "file-1")

        self.assertFalse(result.supported)
        self.assertIsNone(result.text)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
