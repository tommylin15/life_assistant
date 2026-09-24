import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app

client = TestClient(app)


class HealthEndpointTests(unittest.TestCase):
    def test_health_is_process_liveness_only(self):
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ready_reports_database_available(self):
        with patch("app.main.db_session.check_database", new=AsyncMock(return_value=None)):
            response = client.get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_ready_reports_database_unavailable_without_leaking_error_details(self):
        with patch(
            "app.main.db_session.check_database",
            new=AsyncMock(side_effect=SQLAlchemyError("sensitive connection failure")),
        ):
            response = client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {"status": "unavailable", "database": "unavailable"},
        )
        self.assertNotIn("sensitive", response.text)


if __name__ == "__main__":
    unittest.main()
