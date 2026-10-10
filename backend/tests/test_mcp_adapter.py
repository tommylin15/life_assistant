"""Source-level auth and REST-forwarding checks; no prod credentials or DB."""
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.mcp_adapter import curated_upsert, curated_list, curated_status
from app.api.curated import CuratedItemIn


class LifeCuratorMCPTests(unittest.TestCase):
    def test_mcp_fails_closed_without_keys(self):
        with patch.dict(os.environ, {"LIFE_MCP_CLIENT_TOKEN": "", "LIFE_CURATED_INGEST_TOKEN": ""}):
            with TestClient(app) as client:
                self.assertEqual(client.get("/mcp/").status_code, 503)

    def test_mcp_rejects_missing_wrong_and_same_token(self):
        with patch.dict(os.environ, {"LIFE_MCP_CLIENT_TOKEN": "m" * 40,
                                     "LIFE_CURATED_INGEST_TOKEN": "i" * 40}):
            with TestClient(app) as client:
                for headers in ({}, {"Authorization": "Bearer wrong"}):
                    result = client.post("/mcp/", headers=headers, json={})
                    self.assertEqual(result.status_code, 401)
                    self.assertEqual(result.headers.get("www-authenticate"), "Bearer")
        with patch.dict(os.environ, {"LIFE_MCP_CLIENT_TOKEN": "i" * 40,
                                     "LIFE_CURATED_INGEST_TOKEN": "i" * 40}):
            with TestClient(app) as client:
                self.assertEqual(client.get("/mcp/").status_code, 503)


class LifeCuratorForwardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_forward_to_existing_curated_rest_only(self):
        item = CuratedItemIn(title="Session", original_url="https://example.org/events/1",
                             importance=5)
        with patch("app.mcp_adapter._call_life_rest", new_callable=AsyncMock) as call:
            call.return_value = {"accepted": 1, "duplicates_within_batch": 0}
            result = await curated_upsert([item])
            self.assertEqual(result["accepted"], 1)
            args, kwargs = call.await_args
            self.assertEqual(args, ("POST", "/api/v1/free-events/curated:batch"))
            self.assertEqual(kwargs["payload"]["items"][0]["importance"], 5)
            self.assertNotIn("fee_amount", kwargs["payload"]["items"][0])
            await curated_list(min_importance=5)
            self.assertEqual(call.await_args.args[1], "/api/v1/free-events/curated:connector")
            await curated_status()
            self.assertEqual(call.await_args.args[1], "/api/v1/free-events/curated:connector/status")


if __name__ == "__main__":
    unittest.main()
