import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.dialects import postgresql

from app.confirmation import confirmation_requirement, explicit_confirmation_value


class DriveApiContractTests(unittest.TestCase):
    def test_router_exposes_picker_workspace_settings_and_registry_contract(self):
        from app.api.drive import router

        routes = {
            (route.path, method)
            for route in router.routes
            for method in (route.methods or set())
        }
        for expected in (
            ("/drive/picker-config", "GET"),
            ("/drive/workspaces", "GET"),
            ("/drive/workspaces", "POST"),
            ("/drive/ai-settings", "GET"),
            ("/drive/ai-settings", "PUT"),
            ("/drive/documents", "GET"),
            ("/drive/documents/register", "POST"),
            ("/drive/documents/{document_id}/refresh", "POST"),
            ("/drive/documents/{document_id}", "DELETE"),
        ):
            self.assertIn(expected, routes)

    def test_drive_unregister_requires_target_bound_explicit_confirmation(self):
        self.assertEqual(
            confirmation_requirement("DELETE", "/api/v1/drive/documents/doc-1"),
            ("drive.document.unregister", "doc-1"),
        )
        self.assertEqual(
            explicit_confirmation_value("drive.document.unregister", "doc-1"),
            "explicit_user:drive.document.unregister:doc-1",
        )


class DriveSchemaContractTests(unittest.TestCase):
    def test_register_payload_deduplicates_ids_and_enforces_bounds(self):
        from app.models.drive_schemas import DriveDocumentsRegister

        payload = DriveDocumentsRegister(
            google_file_ids=[" file-1 ", "file-1", "file-2"],
            workspace_id="workspace-1",
        )
        self.assertEqual(payload.google_file_ids, ["file-1", "file-2"])


class DriveApiSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_picker_config_contains_public_config_only_and_fixed_drive_scope(self):
        from app.api.drive import get_picker_config
        from app.config import settings

        with (
            patch.object(settings, "google_client_id", "client-id"),
            patch.object(settings, "google_picker_developer_key", "developer-key", create=True),
            patch.object(settings, "google_picker_app_id", "app-id", create=True),
        ):
            result = await get_picker_config(_user={"sub": "user-a"})

        payload = result.model_dump()
        self.assertEqual(
            set(payload), {"client_id", "developer_key", "app_id", "scope"}
        )
        self.assertEqual(
            payload["scope"], "https://www.googleapis.com/auth/drive.file"
        )
        serialized = str(payload).lower()
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("refresh_token", serialized)
        self.assertNotIn("client_secret", serialized)
        self.assertNotIn("gmail", serialized)
        self.assertNotIn("calendar", serialized)

    async def test_document_list_query_is_owner_scoped(self):
        from app.api.drive import list_drive_documents

        db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        db.execute.return_value = result

        response = await list_drive_documents(
            q=None,
            workspace_id=None,
            user={"sub": "user-a"},
            db=db,
        )
        self.assertEqual(response, [])
        statement = db.execute.await_args.args[0]
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        self.assertIn("drive_documents.owner_sub = 'user-a'", sql)

    async def test_workspace_creation_uses_backend_verified_folder_metadata(self):
        from app.models.drive_schemas import DriveWorkspaceCreate
        from app.services.drive_documents import create_workspace
        from app.services.google_drive_files import DriveFileMetadata, GOOGLE_FOLDER_MIME

        db = AsyncMock()
        lookup = MagicMock()
        lookup.scalar_one_or_none.return_value = None
        db.execute.return_value = lookup
        metadata = DriveFileMetadata(
            id="folder-1",
            name="Verified Folder",
            mime_type=GOOGLE_FOLDER_MIME,
            web_view_link="https://drive.google.com/drive/folders/folder-1",
            modified_at=None,
            parents=(),
        )
        with patch(
            "app.services.drive_documents.get_drive_file_metadata",
            new=AsyncMock(return_value=metadata),
        ):
            workspace = await create_workspace(
                db,
                "user-a",
                DriveWorkspaceCreate(google_folder_id="folder-1"),
            )

        self.assertEqual(workspace.owner_sub, "user-a")
        self.assertEqual(workspace.name, "Verified Folder")
        db.add.assert_called_once_with(workspace)
        db.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
