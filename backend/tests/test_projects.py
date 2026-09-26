import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.models.project import Project
from app.models.schemas import ProjectCreate, ProjectUpdate

client = TestClient(app)


class ProjectContractTests(unittest.TestCase):
    def test_project_model_matches_cloud_table_contract(self):
        self.assertEqual(Project.__tablename__, "projects")
        self.assertIn("id", Project.__table__.columns)
        self.assertIn("name", Project.__table__.columns)
        self.assertIn("summary", Project.__table__.columns)
        self.assertIn("status", Project.__table__.columns)

    def test_project_create_defaults_active_status(self):
        body = ProjectCreate(name="Home")
        self.assertEqual(body.status, "active")
        self.assertIsNone(body.summary)

    def test_project_update_requires_a_change(self):
        with self.assertRaises(ValueError):
            ProjectUpdate()
        with self.assertRaises(ValueError):
            ProjectUpdate(name=None)
        with self.assertRaises(ValueError):
            ProjectUpdate(status=None)

        update = ProjectUpdate(summary=None)
        self.assertIn("summary", update.model_fields_set)

    def test_projects_api_is_protected(self):
        response = client.get("/api/v1/projects")
        self.assertEqual(response.status_code, 401)
        self.assertIn("X-Request-ID", response.headers)


class ProjectDeleteGuardTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _linked_result(value):
        result = MagicMock()
        result.scalar_one_or_none.return_value = value
        return result

    @staticmethod
    def _project():
        return Project(id="project-1", name="Guarded project")

    async def test_delete_rejects_linked_task_before_starting_execution(self):
        from app.api.projects import delete_project

        db = AsyncMock()
        db.get.return_value = self._project()
        db.execute.return_value = self._linked_result("task-1")

        with patch("app.api.projects.start_execution", new=AsyncMock()) as start:
            with self.assertRaises(HTTPException) as ctx:
                await delete_project("project-1", {"sub": "u"}, db)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "Project has linked tasks")
        self.assertEqual(db.execute.await_count, 1)
        start.assert_not_awaited()
        db.delete.assert_not_awaited()

    async def test_delete_rejects_linked_note_before_starting_execution(self):
        from app.api.projects import delete_project

        db = AsyncMock()
        db.get.return_value = self._project()
        db.execute.side_effect = [
            self._linked_result(None),
            self._linked_result("note-1"),
        ]

        with (
            patch("app.api.projects.start_execution", new=AsyncMock(return_value=object())) as start,
            patch("app.api.projects.finish_execution", new=AsyncMock()),
            patch("app.api.projects.fail_execution", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await delete_project("project-1", {"sub": "u"}, db)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "Project has linked notes")
        self.assertEqual(db.execute.await_count, 2)
        start.assert_not_awaited()
        db.delete.assert_not_awaited()

    async def test_delete_rejects_linked_shopping_list_before_starting_execution(self):
        from app.api.projects import delete_project

        db = AsyncMock()
        db.get.return_value = self._project()
        db.execute.side_effect = [
            self._linked_result(None),
            self._linked_result(None),
            self._linked_result("shopping-list-1"),
        ]

        with (
            patch("app.api.projects.start_execution", new=AsyncMock(return_value=object())) as start,
            patch("app.api.projects.finish_execution", new=AsyncMock()),
            patch("app.api.projects.fail_execution", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await delete_project("project-1", {"sub": "u"}, db)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "Project has linked shopping lists")
        self.assertEqual(db.execute.await_count, 3)
        start.assert_not_awaited()
        db.delete.assert_not_awaited()

    async def test_delete_without_linked_entities_keeps_existing_delete_path(self):
        from app.api.projects import delete_project

        project = self._project()
        db = AsyncMock()
        db.get.return_value = project
        db.execute.side_effect = [
            self._linked_result(None),
            self._linked_result(None),
            self._linked_result(None),
        ]

        with (
            patch("app.api.projects.start_execution", new=AsyncMock(return_value=object())) as start,
            patch("app.api.projects.finish_execution", new=AsyncMock()) as finish,
            patch("app.api.projects.fail_execution", new=AsyncMock()) as fail,
        ):
            await delete_project("project-1", {"sub": "u"}, db)

        self.assertEqual(db.execute.await_count, 3)
        start.assert_awaited_once()
        db.delete.assert_awaited_once_with(project)
        db.commit.assert_awaited_once()
        finish.assert_awaited_once()
        fail.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
