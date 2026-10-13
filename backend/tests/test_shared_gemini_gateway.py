"""Offline contract tests for Life's signed Gemini Gateway caller and API."""
import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.api import auth, gemini_text
from app.config import settings
from app.main import app
from app.services import shared_gemini_gateway as gateway
from app.services.ai_enrichment_provider import codex_owner_uuid


class GatewayTextClientTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, handler, *, prompt="Say hello"):
        original = httpx.AsyncClient
        calls = []

        def record(request):
            calls.append(request)
            return handler(request)

        with (
            patch.object(settings, "gemini_gateway_text_enabled", True),
            patch.object(settings, "gemini_gateway_url", gateway.AUDIENCE),
            patch.object(gateway.httpx, "AsyncClient", side_effect=lambda **kw: original(
                transport=httpx.MockTransport(record), **kw
            )),
        ):
            result = await gateway.generate_text(prompt, user_sub="verified-google-sub")
        return result, calls

    @staticmethod
    def metadata_or_success(request):
        if request.url.host == "metadata.google.internal":
            if request.url.path.endswith("/email"):
                return httpx.Response(200, text=settings.codex_shared_caller_service_account)
            if request.url.path.endswith("/identity"):
                assert request.url.params["audience"] == gateway.AUDIENCE
                assert request.url.params["format"] == "full"
                return httpx.Response(200, text="synthetic-google-id-token")
        sent = json.loads(request.content)
        return httpx.Response(200, json={
            "status": "completed", "project": gateway.PROJECT,
            "ownerId": sent["ownerId"], "requestId": sent["requestId"],
            "model": gateway.MODEL, "result": {"text": "Hello from Gemini"},
        })

    async def test_signed_request_is_owner_scoped_and_one_provider_call(self):
        result, calls = await self._run(self.metadata_or_success)
        self.assertEqual(result["text"], "Hello from Gemini")
        self.assertEqual(result["model"], gateway.MODEL)
        self.assertEqual(len(calls), 3)
        request = calls[-1]
        self.assertEqual(request.url.path, "/v1/gemini/execute")
        self.assertEqual(request.headers["Authorization"], "Bearer synthetic-google-id-token")
        body = json.loads(request.content)
        self.assertEqual(body["project"], "life-assistant")
        self.assertEqual(body["ownerId"], codex_owner_uuid("verified-google-sub"))
        self.assertNotEqual(body["ownerId"], "verified-google-sub")
        self.assertEqual(uuid.UUID(body["requestId"]).version, 4)
        self.assertEqual(body["model"], "gemini-3.5-flash-lite")
        self.assertNotIn("ownerId", result)
        self.assertNotIn("prompt", result)

    async def test_disabled_is_zero_network(self):
        with patch.object(settings, "gemini_gateway_text_enabled", False), patch.object(
            gateway.httpx, "AsyncClient"
        ) as client:
            with self.assertRaises(gateway.GatewayTextError) as caught:
                await gateway.generate_text("text", user_sub="verified-google-sub")
        self.assertEqual(caught.exception.code, "gemini_text_disabled")
        client.assert_not_called()

    async def test_invalid_prompt_and_multibyte_limit_fail_before_network(self):
        with patch.object(settings, "gemini_gateway_text_enabled", True), patch.object(
            gateway.httpx, "AsyncClient"
        ) as client:
            for prompt in (" ", "繁" * 2731):
                with self.assertRaises(gateway.GatewayTextError) as caught:
                    await gateway.generate_text(prompt, user_sub="verified-google-sub")
                self.assertEqual(caught.exception.code, "invalid_prompt")
        client.assert_not_called()

    async def test_fail_closed_when_identity_is_not_dedicated(self):
        def wrong_email(request):
            self.assertTrue(request.url.path.endswith("/email"))
            return httpx.Response(200, text="default-compute@example.test")

        with self.assertRaises(gateway.GatewayTextError) as caught:
            await self._run(wrong_email)
        self.assertEqual(caught.exception.code, "service_identity_unavailable")

    async def test_gateway_project_owner_request_model_and_text_must_match(self):
        variants = [
            ("project", "market-mart"), ("ownerId", str(uuid.uuid4())),
            ("requestId", str(uuid.uuid4())), ("model", "gemini-3.0-flash-lite"),
            ("status", "queued"), ("result", {"text": ""}), ("result", {"text": "x" * 32001}),
        ]
        for field, invalid in variants:
            with self.subTest(field=field, invalid=str(invalid)[:25]):
                def bad_reply(request):
                    response = self.metadata_or_success(request)
                    if request.url.host == "metadata.google.internal":
                        return response
                    payload = response.json()
                    payload[field] = invalid
                    return httpx.Response(200, json=payload)
                with self.assertRaises(gateway.GatewayTextError) as caught:
                    await self._run(bad_reply)
                self.assertEqual(caught.exception.code, "gateway_invalid_response")

    async def test_quota_and_upstream_failures_are_not_retried(self):
        for code, expected in ((429, "gateway_busy"), (502, "gateway_execution_failed"),
                               (401, "gateway_identity_rejected")):
            calls = []
            def error(request):
                if request.url.host == "metadata.google.internal":
                    return self.metadata_or_success(request)
                calls.append(request)
                return httpx.Response(code, json={"error": "provider-secret-never-expose"})
            with self.subTest(code=code):
                with self.assertRaises(gateway.GatewayTextError) as caught:
                    await self._run(error)
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(len(calls), 1)

    async def test_wrong_gateway_url_is_fail_closed(self):
        with (
            patch.object(settings, "gemini_gateway_text_enabled", True),
            patch.object(settings, "gemini_gateway_url", "https://attacker.example"),
            patch.object(gateway.httpx, "AsyncClient") as client,
        ):
            with self.assertRaises(gateway.GatewayTextError) as caught:
                await gateway.generate_text("Hello", user_sub="verified-google-sub")
        self.assertEqual(caught.exception.code, "gateway_configuration_unavailable")
        client.assert_not_called()


class GatewayTextApiTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_requires_real_session_before_model_call(self):
        with patch.object(gemini_text, "generate_text", new_callable=AsyncMock) as generate:
            response = TestClient(app).post("/api/v1/ai/text", json={"prompt": "hello"})
        self.assertEqual(response.status_code, 401)
        generate.assert_not_awaited()

    def test_authenticated_owner_cannot_be_claimed_or_overridden(self):
        app.dependency_overrides[auth.current_user] = lambda: {"sub": "verified-A"}
        async def fake_generate(prompt, *, user_sub):
            self.assertEqual(prompt, "hello")
            self.assertEqual(user_sub, "verified-A")
            return {"status": "completed", "request_id": str(uuid.uuid4()),
                    "model": gateway.MODEL, "text": "Hi"}
        with patch.object(gemini_text, "generate_text", side_effect=fake_generate) as generate:
            response = TestClient(app).post("/api/v1/ai/text", json={"prompt": "hello"})
            override = TestClient(app).post(
                "/api/v1/ai/text", json={"prompt": "hello", "ownerId": str(uuid.uuid4())}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["text"], "Hi")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(override.status_code, 422)
        self.assertEqual(generate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
