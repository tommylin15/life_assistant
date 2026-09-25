import unittest

from fastapi.testclient import TestClient

from app.errors import normalize_request_id
from app.main import app

client = TestClient(app)


class ErrorContractTests(unittest.TestCase):
    def test_request_id_accepts_safe_client_value(self):
        self.assertEqual(normalize_request_id("req-123.A"), "req-123.A")

    def test_request_id_replaces_unsafe_value(self):
        value = normalize_request_id("unsafe request id with spaces")
        self.assertNotEqual(value, "unsafe request id with spaces")
        self.assertGreater(len(value), 10)

    def test_http_errors_use_unified_envelope_and_request_id(self):
        response = client.get(
            "/api/v1/not-a-real-route",
            headers={"X-Request-ID": "contract-test-1"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["X-Request-ID"], "contract-test-1")
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "http_404",
                    "message": "Not Found",
                    "request_id": "contract-test-1",
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
