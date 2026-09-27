import unittest

from fastapi.testclient import TestClient

from app.confirmation import (
    CONFIRMATION_HEADER,
    confirmation_requirement,
    confirmation_satisfied,
    explicit_confirmation_value,
)
from app.main import app


client = TestClient(app)


class ConfirmationPolicyTests(unittest.TestCase):
    def test_calendar_delete_requires_action_and_target_bound_confirmation(self):
        path = "/api/v1/integrations/google/calendar/events/event-123"
        self.assertEqual(
            confirmation_requirement("DELETE", path),
            ("calendar.delete", "event-123"),
        )
        self.assertFalse(confirmation_satisfied("DELETE", path, None))
        self.assertFalse(
            confirmation_satisfied(
                "DELETE",
                path,
                explicit_confirmation_value("calendar.delete", "other-event"),
            )
        )
        self.assertTrue(
            confirmation_satisfied(
                "DELETE",
                path,
                explicit_confirmation_value("calendar.delete", "event-123"),
            )
        )

    def test_non_destructive_requests_do_not_require_confirmation(self):
        self.assertIsNone(
            confirmation_requirement(
                "PATCH",
                "/api/v1/integrations/google/calendar/events/event-123",
            )
        )
        self.assertTrue(
            confirmation_satisfied(
                "PATCH",
                "/api/v1/integrations/google/calendar/events/event-123",
                None,
            )
        )

    def test_unauthenticated_calendar_delete_preserves_auth_precedence(self):
        response = client.delete(
            "/api/v1/integrations/google/calendar/events/event-123",
            headers={"X-Request-ID": "confirmation-auth-precedence"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "http_401")
        self.assertEqual(
            response.headers["X-Request-ID"],
            "confirmation-auth-precedence",
        )

    def test_authenticated_session_without_confirmation_is_blocked_before_provider(self):
        response = client.delete(
            "/api/v1/integrations/google/calendar/events/event-123",
            cookies={"__session": "id:synthetic-session"},
            headers={"X-Request-ID": "confirmation-required"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "confirmation_required",
                    "message": "Explicit user confirmation is required",
                    "request_id": "confirmation-required",
                }
            },
        )
        self.assertEqual(response.headers["X-Request-ID"], "confirmation-required")

    def test_wrong_target_confirmation_is_rejected(self):
        response = client.delete(
            "/api/v1/integrations/google/calendar/events/event-123",
            cookies={"__session": "id:synthetic-session"},
            headers={
                "X-Request-ID": "confirmation-wrong-target",
                CONFIRMATION_HEADER: explicit_confirmation_value(
                    "calendar.delete", "event-999"
                ),
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "confirmation_required")


if __name__ == "__main__":
    unittest.main()
