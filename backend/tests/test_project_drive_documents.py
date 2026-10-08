import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.confirmation import confirmation_requirement, explicit_confirmation_value
from app.main import app
from app.models.drive import DriveDocument, ProjectDriveDocument
from app.models.drive_schemas import DriveProjectLinksCreate
from app.models.project import Project
from app.services import drive_documents


client = TestClient(app)


class DriveProjectLinkContractTests(unittest.TestCase):
    def test_project_document_routes_are_registered_and_protected(self):
        paths = {route.path for route in app.routes if hasattr(route, "path")}
        self.assertIn("/api/v1/drive/project-documents", paths)
        self.assertIn("/api/v1/drive/documents/{document_id}/projects", paths)
        self.assertIn(
            "/api/v1/drive/documents/{document_id}/projects/{project_id}",
            paths,
        )

        response = client.get(
            "/api/v1/drive/project-documents",
            params={"project_id": "project-1"},
        )
        self.assertEqual(response.status_code, 401)

    def test_bulk_attach_normalizes_duplicate_project_ids(self):
        body = DriveProjectLinksCreate(
            project_ids=[" project-1 ", "project-1", "project-2"]
        )
        self.assertEqual(body.project_ids, ["project-1", "project-2"])

        with self.assertRaises(ValueError):
            DriveProjectLinksCreate(project_ids=["  "])

    def test_detach_requires_target_bound_explicit_confirmation(self):
        path = "/api/v1/drive/documents/document-1/projects/project-1"
        target = "document-1:project-1"
        self.assertEqual(
            confirmation_requirement("DELETE", path),
            ("drive.document.project.detach", target),
        )
        self.assertEqual(
            explicit_confirmation_value("drive.document.project.detach", target),
            "explicit_user:drive.document.project.detach:document-1:project-1",
        )


class DriveProjectServiceTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _document():
        return DriveDocument(
            id="document-1",
            user_sub="user-1",
            google_file_id="google-file-1",
            name="Plan",
            mime_type="application/vnd.google-apps.document",
        )

    async def test_attach_is_user_scoped_and_idempotent_per_project(self):
        document = self._document()
        existing = ProjectDriveDocument(
            project_id="project-2",
            drive_document_id=document.id,
        )
        db = MagicMock()
        db.get = AsyncMock(
            side_effect=[
                Project(id="project-1", name="One"),
                Project(id="project-2", name="Two"),
                None,
                existing,
            ]
        )
        db.add = MagicMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ) as get_document:
            returned = await drive_documents.attach_document_projects(
                db,
                "user-1",
                document.id,
                ["project-1", "project-2"],
            )

        self.assertEqual(returned, ["project-1", "project-2"])
        get_document.assert_awaited_once_with(db, "user-1", document.id)
        db.add.assert_called_once()
        relation = db.add.call_args.args[0]
        self.assertEqual(relation.project_id, "project-1")
        self.assertEqual(relation.drive_document_id, document.id)

    async def test_attach_rejects_unknown_project_before_creating_relations(self):
        document = self._document()
        db = MagicMock()
        db.get = AsyncMock(return_value=None)
        db.add = MagicMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await drive_documents.attach_document_projects(
                    db,
                    "user-1",
                    document.id,
                    ["missing-project"],
                )

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Project not found")
        db.add.assert_not_called()

    async def test_project_document_listing_keeps_drive_document_user_scope(self):
        document = self._document()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [document]
        db = MagicMock()
        db.get = AsyncMock(return_value=Project(id="project-1", name="One"))
        db.execute = AsyncMock(return_value=result)

        documents = await drive_documents.list_project_documents(
            db,
            "user-1",
            "project-1",
        )

        self.assertEqual(documents, [document])
        statement = str(db.execute.await_args.args[0])
        self.assertIn("project_drive_documents.project_id", statement)
        self.assertIn("drive_documents.user_sub", statement)

    async def test_detach_deletes_only_the_relationship(self):
        document = self._document()
        relation = ProjectDriveDocument(
            project_id="project-1",
            drive_document_id=document.id,
        )
        db = MagicMock()
        db.get = AsyncMock(
            side_effect=[
                Project(id="project-1", name="One"),
                relation,
            ]
        )
        db.delete = AsyncMock()

        with patch(
            "app.services.drive_documents.get_document",
            new=AsyncMock(return_value=document),
        ):
            removed = await drive_documents.detach_document_project(
                db,
                "user-1",
                document.id,
                "project-1",
            )

        self.assertTrue(removed)
        db.delete.assert_awaited_once_with(relation)
        self.assertNotIn(
            "get_drive_file_metadata",
            inspect.getsource(drive_documents.detach_document_project),
        )


if __name__ == "__main__":
    unittest.main()
