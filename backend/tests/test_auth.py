from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException
from starlette.requests import Request

from app.api import auth


class AuthApiTests(IsolatedAsyncioTestCase):
    async def test_login_sets_state_cookie_and_uses_configured_redirect(self):
        original_client_id = auth.settings.google_client_id
        original_redirect = auth.settings.google_redirect_uri
        try:
            auth.settings.google_client_id = "client-id"
            auth.settings.google_redirect_uri = "https://example.test/auth/callback"

            response = await auth.login()

            location = response.headers["location"]
            query = parse_qs(urlparse(location).query)
            self.assertEqual(query["client_id"], ["client-id"])
            self.assertEqual(
                query["redirect_uri"],
                ["https://example.test/auth/callback"],
            )
            self.assertIn("state", query)
            self.assertIn(auth.SESSION_COOKIE, response.headers["set-cookie"])
            self.assertIn("HttpOnly", response.headers["set-cookie"])
            self.assertIn("Secure", response.headers["set-cookie"])
        finally:
            auth.settings.google_client_id = original_client_id
            auth.settings.google_redirect_uri = original_redirect

    async def test_current_user_rejects_missing_session(self):
        request = Request({"type": "http", "headers": []})
        with self.assertRaises(HTTPException) as ctx:
            await auth.current_user(request)
        self.assertEqual(ctx.exception.status_code, 401)

    async def test_current_user_accepts_verified_cookie(self):
        request = Request({
            "type": "http",
            "headers": [(b"cookie", b"__session=id:test-token")],
        })
        claims = {
            "sub": "123",
            "email": "user@example.test",
            "name": "User",
            "exp": 9999999999,
        }
        with patch(
            "app.api.auth._verify_id_token",
            new=AsyncMock(return_value=claims),
        ) as verify:
            user = await auth.current_user(request)

        self.assertEqual(user["email"], "user@example.test")
        verify.assert_awaited_once_with("test-token")
