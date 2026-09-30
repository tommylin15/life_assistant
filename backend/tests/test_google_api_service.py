import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException


class GoogleApiServiceTests(unittest.IsolatedAsyncioTestCase):
    def _client(self, side_effect):
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.request = AsyncMock(side_effect=side_effect)
        return client

    async def test_401_refreshes_once_and_retries_with_new_token(self):
        from app.services.google_api import request_google

        first = MagicMock(status_code=401)
        second = MagicMock(status_code=200)
        client = self._client([first, second])
        token = AsyncMock(side_effect=["old-token", "new-token"])
        with (
            patch("app.services.google_api.get_access_token", token),
            patch("app.services.google_api.httpx.AsyncClient", return_value=client),
        ):
            response = await request_google(MagicMock(), "user-a", "scope-a", "GET", "https://example.invalid")

        self.assertIs(response, second)
        self.assertEqual(client.request.await_count, 2)
        self.assertEqual(
            client.request.await_args_list[0].kwargs["headers"]["Authorization"],
            "Bearer old-token",
        )
        self.assertEqual(
            client.request.await_args_list[1].kwargs["headers"]["Authorization"],
            "Bearer new-token",
        )
        self.assertTrue(token.await_args_list[1].kwargs["force_refresh"])

    async def test_repeated_permission_failure_is_stable_409(self):
        from app.services.google_api import request_google

        client = self._client([MagicMock(status_code=403)])
        with (
            patch("app.services.google_api.get_access_token", new=AsyncMock(return_value="token")),
            patch("app.services.google_api.httpx.AsyncClient", return_value=client),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await request_google(MagicMock(), "user-a", "scope-a", "GET", "https://example.invalid")
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("reauthorization", str(ctx.exception.detail).lower())

    async def test_network_and_other_provider_failures_are_mapped(self):
        from app.services.google_api import request_google

        client = self._client([httpx.ConnectError("offline")])
        with (
            patch("app.services.google_api.get_access_token", new=AsyncMock(return_value="token")),
            patch("app.services.google_api.httpx.AsyncClient", return_value=client),
        ):
            with self.assertRaises(HTTPException) as network:
                await request_google(MagicMock(), "user-a", "scope-a", "GET", "https://example.invalid")
        self.assertEqual(network.exception.status_code, 503)

        client = self._client([MagicMock(status_code=500)])
        with (
            patch("app.services.google_api.get_access_token", new=AsyncMock(return_value="token")),
            patch("app.services.google_api.httpx.AsyncClient", return_value=client),
        ):
            with self.assertRaises(HTTPException) as provider:
                await request_google(MagicMock(), "user-a", "scope-a", "GET", "https://example.invalid")
        self.assertEqual(provider.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
