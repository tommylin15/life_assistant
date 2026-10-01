import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.drive import DriveDocument, ProjectDriveDocument
from app.models.project import Project


class ProjectDriveDocumentTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_attach_allows_many_projects_and_is_idempotent(self):
        from app.services.drive_documents import attach_document_to_projects

        document = DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="g1",
            name="Spec",
            mime_type="text/plain",
        )
        p1 = Project(id="p1", name="P1", status="active")
        p2 = Project(id="p2", name="P2", status="active")
        db = AsyncMock()

        owned = MagicMock()
        owned.scalar_one_or_none.return_value = document
        project_rows = MagicMock()
        project_rows.scalars.return_value.all.return_value = [p1, p2]
        existing = MagicMock()
        existing.scalars.return_value.all.return_value = [
            ProjectDriveDocument(project_id="p1", drive_document_id="d1")
        ]
        db.execute.side_effect = [owned, project_rows, existing]

        links = await attach_document_to_projects(
            db,
            "user-a",
            "d1",
            ["p1", "p1", "p2"],
        )

        self.assertEqual({link.project_id for link in links}, {"p1", "p2"})
        db.add.assert_called_once()
        added = db.add.call_args.args[0]
        self.assertEqual((added.project_id, added.drive_document_id), ("p2", "d1"))
        db.commit.assert_awaited_once()

    async def test_attach_rejects_unknown_project_and_cross_user_document(self):
        from app.services.drive_documents import attach_document_to_projects

        db = AsyncMock()
        missing_doc = MagicMock()
        missing_doc.scalar_one_or_none.return_value = None
        db.execute.return_value = missing_doc
        with self.assertRaises(HTTPException) as cross_user:
            await attach_document_to_projects(db, "user-b", "d1", ["p1"])
        self.assertEqual(cross_user.exception.status_code, 404)

        document = DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="g1",
            name="Spec",
            mime_type="text/plain",
        )
        db = AsyncMock()
        owned = MagicMock()
        owned.scalar_one_or_none.return_value = document
        projects = MagicMock()
        projects.scalars.return_value.all.return_value = []
        db.execute.side_effect = [owned, projects]
        with self.assertRaises(HTTPException) as missing_project:
            await attach_document_to_projects(db, "user-a", "d1", ["missing"])
        self.assertEqual(missing_project.exception.status_code, 404)

    async def test_detach_removes_only_requested_relation(self):
        from app.services.drive_documents import detach_document_from_project

        document = DriveDocument(
            id="d1",
            owner_sub="user-a",
            google_file_id="g1",
            name="Spec",
            mime_type="text/plain",
        )
        db = AsyncMock()
        owned = MagicMock()
        owned.scalar_one_or_none.return_value = document
        relation = MagicMock()
        relation.scalar_one_or_none.return_value = ProjectDriveDocument(
            project_id="p1",
            drive_document_id="d1",
        )
        db.execute.side_effect = [owned, relation, MagicMock()]

        await detach_document_from_project(db, "user-a", "d1", "p1")

        self.assertEqual(db.execute.await_count, 3)
        statement = db.execute.await_args_list[-1].args[0]
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("project_id = 'p1'", compiled)
        self.assertIn("drive_document_id = 'd1'", compiled)
        db.commit.assert_awaited_once()

    async def test_project_delete_is_blocked_by_drive_relationship(self):
        from app.api.projects import delete_project

        project = Project(id="p1", name="P1", status="active")
        db = AsyncMock()
        db.get.return_value = project
        empty = MagicMock()
        empty.scalar_one_or_none.return_value = None
        linked_drive = MagicMock()
        linked_drive.scalar_one_or_none.return_value = "d1"
        db.execute.side_effect = [empty, empty, empty, linked_drive]

        with self.assertRaises(HTTPException) as ctx:
            await delete_project("p1", {"sub": "user-a"}, db)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("Drive", str(ctx.exception.detail))
        db.delete.assert_not_awaited()


class ProjectDriveApiContractTests(unittest.TestCase):
    def test_drive_router_has_project_link_routes(self):
        from app.api.drive import router

        routes = {
            (route.path, method)
            for route in router.routes
            for method in (route.methods or set())
        }
        self.assertIn(("/drive/project-documents", "GET"), routes)
        self.assertIn(("/drive/documents/{document_id}/projects", "POST"), routes)
        self.assertIn(
            ("/drive/documents/{document_id}/projects/{project_id}", "DELETE"),
            routes,
        )


if __name__ == "__main__":
    unittest.main()
