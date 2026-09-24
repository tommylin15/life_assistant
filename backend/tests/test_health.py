from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app

client = TestClient(app)


def test_health_is_process_liveness_only():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_database_available():
    with patch("app.main.db_session.check_database", new=AsyncMock(return_value=None)):
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_ready_reports_database_unavailable_without_leaking_error_details():
    with patch(
        "app.main.db_session.check_database",
        new=AsyncMock(side_effect=SQLAlchemyError("sensitive connection failure")),
    ):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert "sensitive" not in response.text
