import unittest

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


if __name__ == "__main__":
    unittest.main()
