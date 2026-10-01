import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.confirmation import confirmation_requirement
from app.main import app
from app.models.drive_schemas import (
    DriveDocumentRegister,
    DriveWorkspaceUpdate,
    PickerConfigOut,
)


client = TestClient(app)


class DriveApiContractTests(unittest.TestCase):
    def test_drive_routes_are_registered_under_versioned_api(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/api/v1/drive/workspaces",
            "/api/v1/drive/workspaces/{workspace_id}",
            "/api/v1/drive/picker-config",
            "/api/v1/drive/documents/register",
            "/api/v1/drive/documents",
            "/api/v1/drive/documents/{document_id}/refresh",
        }
        self.assertTrue(expected.issubset(paths))
        self.assertNotIn("/api/v1/drive/picker-session", paths)

    def test_registration_normalizes_repeated_picker_selection(self):
        body = DriveDocumentRegister(
            google_file_ids=[" file-1 ", "file-1", "file-2"],
            workspace_id="workspace-1",
        )
        self.assertEqual(body.google_file_ids, ["file-1", "file-2"])

    def test_workspace_update_requires_explicit_non_null_change(self):
        with self.assertRaises(ValueError):
            DriveWorkspaceUpdate()
        with self.assertRaises(ValueError):
            DriveWorkspaceUpdate(name=None)

        body = DriveWorkspaceUpdate(name="  Research  ", is_default=True)
        self.assertEqual(body.name, "Research")
        self.assertTrue(body.is_default)

    def test_drive_workspace_delete_uses_destructive_confirmation_policy(self):
        path = "/api/v1/drive/workspaces/workspace-1"
        self.assertEqual(
            confirmation_requirement("DELETE", path),
            ("drive.workspace.delete", "workspace-1"),
        )

    def test_unauthenticated_drive_registry_is_protected(self):
        for method, path in (
            ("get", "/api/v1/drive/workspaces"),
            ("get", "/api/v1/drive/documents"),
            ("get", "/api/v1/drive/picker-config"),
        ):
            with self.subTest(method=method, path=path):
                response = getattr(client, method)(path)
                self.assertEqual(response.status_code, 401)

    def test_authenticated_workspace_delete_without_confirmation_is_blocked_before_database(self):
        response = client.delete(
            "/api/v1/drive/workspaces/workspace-1",
            cookies={"__session": "id:synthetic-session"},
            headers={"X-Request-ID": "drive-workspace-confirmation"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "confirmation_required")

    def test_registry_service_is_user_scoped_and_does_not_delete_google_files(self):
        service_source = (
            Path(__file__).parents[1] / "app/services/drive_documents.py"
        ).read_text(encoding="utf-8")
        self.assertIn("DriveWorkspace.user_sub == user_sub", service_source)
        self.assertIn("DriveDocument.user_sub == user_sub", service_source)
        self.assertNotIn("googleapis.com", service_source)
        self.assertNotIn('"DELETE"', service_source)

    def test_drive_adapter_only_addresses_explicit_file_ids_not_whole_drive_search(self):
        adapter_source = (
            Path(__file__).parents[1] / "app/services/google_drive_files.py"
        ).read_text(encoding="utf-8")
        self.assertIn("files/{file_id}", adapter_source)
        self.assertNotIn("/drive/v3/files?", adapter_source)
        self.assertNotIn("pageToken", adapter_source)

    def test_picker_config_exposes_only_picker_safe_public_configuration(self):
        body = PickerConfigOut(
            client_id="web-client.apps.googleusercontent.com",
            developer_key="restricted-browser-key",
            app_id="123456789",
            scope="https://www.googleapis.com/auth/drive.file",
        ).model_dump()
        self.assertEqual(
            set(body),
            {"client_id", "developer_key", "app_id", "scope"},
        )
        self.assertEqual(
            body["scope"],
            "https://www.googleapis.com/auth/drive.file",
        )
        for forbidden in (
            "access_token",
            "refresh_token",
            "client_secret",
            "gmail",
            "calendar",
        ):
            self.assertNotIn(forbidden, body)

    def test_picker_config_never_returns_stored_backend_oauth_tokens(self):
        api_source = (Path(__file__).parents[1] / "app/api/drive.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('response.headers["Cache-Control"] = "no-store"', api_source)
        self.assertIn("GOOGLE_PICKER_DEVELOPER_KEY", api_source)
        self.assertIn("GOOGLE_PICKER_APP_ID", api_source)
        self.assertIn('SERVICE_SCOPES["drive"][0]', api_source)
        self.assertNotIn("get_access_token", api_source)
        self.assertNotIn("GoogleConnection", api_source)
        self.assertNotIn("access_token=", api_source)
        self.assertNotIn("refresh_token", api_source)


if __name__ == "__main__":
    unittest.main()
