"""Shared Codex consumer contract: mock transport only; GCP live E2E is separate."""
import json
import unittest
import uuid
from unittest.mock import AsyncMock, patch

import httpx

from app import config
from app.services import ai_enrichment_provider as ai


class SharedCodexProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.owner = ai.codex_owner_uuid("google-sub-A")
        self.provider = ai.SharedCodexEnrichmentProvider(owner_id=self.owner)
        self.context = ai.DocumentEnrichmentContext(
            document_id="doc-1",
            title="Research",
            mime_type="application/vnd.google-apps.document",
            document_text="Bounded synthetic research",
        )

    async def _run_mock(self, handler):
        original = httpx.AsyncClient
        calls = []

        def wrap(request):
            calls.append(request)
            return handler(request)

        with (
            patch.object(ai.httpx, "AsyncClient", side_effect=lambda **kw: original(
                transport=httpx.MockTransport(wrap), **kw
            )),
            patch.object(self.provider, "_mint_google_id_token", new=AsyncMock(return_value="synthetic-id-token")),
        ):
            result = await self.provider.suggest_tags(self.context)
        return result, calls

    @staticmethod
    def _success(request, *, body=None):
        sent = json.loads(request.content)
        return httpx.Response(200, json=body or {
            "status": "completed",
            "project": "life-assistant",
            "ownerId": sent["ownerId"],
            "requestId": sent["requestId"],
            "result": {"text": json.dumps({"tags":[{"name":"Planning","confidence":0.91}]})},
            "providerIds": {"threadId":"thread","turnId":"turn"},
        })

    def test_stable_owner_is_project_scoped_and_not_google_sub_raw(self):
        self.assertEqual(self.owner, ai.codex_owner_uuid("google-sub-A"))
        self.assertNotEqual(self.owner, ai.codex_owner_uuid("google-sub-B"))
        self.assertNotEqual(self.owner, "google-sub-A")
        self.assertEqual(uuid.UUID(self.owner).version, 5)
        with self.assertRaises(ValueError):
            ai.codex_owner_uuid("")

    async def test_signed_private_request_and_envelope_success(self):
        def handler(request):
            self.assertEqual(request.url.path, "/v1/codex/execute")
            self.assertEqual(request.headers["Authorization"], "Bearer synthetic-id-token")
            sent = json.loads(request.content)
            self.assertEqual(sent["project"], "life-assistant")
            self.assertEqual(sent["ownerId"], self.owner)
            self.assertEqual(uuid.UUID(sent["requestId"]).version, 4)
            self.assertNotIn("model", sent)  # Don't assume unverified entitlement.
            self.assertLessEqual(len(sent["prompt"].encode("utf-8")), 16 * 1024)
            return self._success(request)
        tags, calls = await self._run_mock(handler)
        self.assertEqual([x.name for x in tags], ["Planning"])
        self.assertEqual(len(calls), 1)

    async def test_429_bounded_retry_then_success(self):
        count = 0
        def handler(request):
            nonlocal count
            count += 1
            if count == 1:
                return httpx.Response(429, json={"error": "busy"})
            return self._success(request)
        with patch.object(ai.asyncio, "sleep", new=AsyncMock()) as sleep:
            tags, calls = await self._run_mock(handler)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(tags), 1)
        sleep.assert_awaited_once_with(2)
        self.assertEqual(json.loads(calls[0].content)["requestId"], json.loads(calls[1].content)["requestId"])

    async def test_error_categories_and_no_retry_for_502(self):
        for status in (400,401,403,429,502):
            with self.subTest(status=status):
                count = 0
                def handler(request):
                    nonlocal count
                    count += 1
                    return httpx.Response(status, json={"error":"never log"})
                with patch.object(ai.asyncio, "sleep", new=AsyncMock()):
                    with self.assertRaises(ai.AIProviderError) as raised:
                        await self._run_mock(handler)
                self.assertEqual(raised.exception.status_code, status)
                self.assertEqual(count, 2 if status == 429 else 1)

    async def test_wrong_project_owner_request_id_or_empty_result_is_not_success(self):
        for patch_field, value in (
            ("project","market-mart"), ("ownerId", str(uuid.uuid4())),
            ("requestId", str(uuid.uuid4())), ("result", {"text": ""}),
            ("providerIds", {"threadId": "", "turnId": ""}),
        ):
            with self.subTest(field=patch_field):
                def handler(request):
                    good = self._success(request).json()
                    good[patch_field] = value
                    return httpx.Response(200, json=good)
                with self.assertRaises(ai.AIProviderError) as raised:
                    await self._run_mock(handler)
                self.assertEqual(raised.exception.code, "provider_invalid_output")

    async def test_prompt_utf8_limit_is_enforced_pre_network(self):
        too_big = ai.DocumentEnrichmentContext(
            document_id="doc", title="中文" * 12000, mime_type="text/plain",
            document_text="中文" * 12000
        )
        with patch.object(self.provider, "_mint_google_id_token", new=AsyncMock()) as minted:
            with self.assertRaises(ai.AIProviderError) as raised:
                await self.provider.suggest_tags(too_big)
        self.assertEqual(raised.exception.code, "provider_request_too_large")
        minted.assert_not_awaited()

    async def test_metadata_token_mints_dedicated_caller_audience(self):
        original = httpx.AsyncClient
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(request.url.host, "metadata.google.internal")
            self.assertEqual(request.headers["Metadata-Flavor"], "Google")
            if request.url.path.endswith("/email"):
                return httpx.Response(200, text=self.provider._caller_sa)
            self.assertTrue(request.url.path.endswith("/identity"))
            self.assertEqual(request.url.params["audience"], self.provider._base_url)
            self.assertEqual(request.url.params["format"], "full")
            return httpx.Response(200, text="synthetic-bound-id-token")
        async with original(transport=httpx.MockTransport(handler)) as client:
            token = await self.provider._mint_google_id_token(client)
        self.assertEqual(token, "synthetic-bound-id-token")
        self.assertEqual(len(calls), 2)

    async def test_metadata_rejects_other_runtime_identity(self):
        def handler(request):
            self.assertTrue(request.url.path.endswith("/email"))
            return httpx.Response(200, text="default-compute@example.com")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(ai.AIProviderError):
                await self.provider._mint_google_id_token(client)

    async def test_codex_primary_first_then_legacy_fallback(self):
        with (
            patch.object(config.settings,"ai_enrichment_provider","gemini"),
            patch.object(config.settings,"ai_enrichment_model","latest-3-flash"),
            patch.object(config.settings,"ai_enrichment_fallback_provider","groq"),
            patch.object(config.settings,"ai_enrichment_fallback_model","openai/gpt-oss-120b"),
            patch.object(config.settings,"ai_enrichment_tertiary_provider","openrouter"),
            patch.object(config.settings,"ai_enrichment_tertiary_model","openrouter/free"),
            patch.object(config.settings,"gemini_api_key","test"),
            patch.object(config.settings,"groq_api_key","test"),
            patch.object(config.settings,"openrouter_api_key","test"),
            patch.object(config.settings,"codex_primary_enabled",True),
        ):
            routed=ai.get_ai_enrichment_provider(owner_id=self.owner)
        self.assertEqual(routed.primary.provider_name,"codex")
        self.assertEqual(routed.fallback.primary.provider_name,"gemini")
        self.assertEqual(routed.fallback.fallback.primary.provider_name,"groq")
        self.assertEqual(routed.fallback.fallback.fallback.provider_name,"openrouter")

    async def test_no_owner_fail_closed_when_primary_enabled(self):
        with patch.object(config.settings,"codex_primary_enabled",True):
            p = ai.get_ai_enrichment_provider()
        self.assertEqual(p.provider_name,"disabled")


if __name__ == "__main__":
    unittest.main()
