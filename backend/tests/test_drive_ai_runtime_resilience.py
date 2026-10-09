from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app import config
from app.services import ai_enrichment_provider as providers
from app.services.ai_enrichment_provider import (
    AIProviderError,
    DocumentEnrichmentContext,
    TagSuggestion,
)
from scripts import run_drive_external_ai_acceptance as acceptance


class DriveAITransientRetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.context = DocumentEnrichmentContext(
            document_id="retry-test-document",
            title="Retry test",
            mime_type="application/vnd.google-apps.document",
            document_text="Synthetic retry test content.",
        )

    async def test_compatible_provider_retries_one_transient_503(self) -> None:
        calls = 0

        def handle(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": '{"tags":[{"name":"Planning","confidence":0.9}]}'
                            },
                        }
                    ]
                },
            )

        client_class = providers.httpx.AsyncClient
        transport = providers.httpx.MockTransport(handle)
        provider = providers.ChatCompletionsEnrichmentProvider(
            provider="gemini",
            api_key="test-key",
            model="gemini-test-flash",
            base_url="https://example.invalid",
        )
        with (
            patch.object(
                providers.httpx,
                "AsyncClient",
                side_effect=lambda **kwargs: client_class(transport=transport, **kwargs),
            ),
            patch.object(providers.asyncio, "sleep", new=AsyncMock()) as sleep,
        ):
            result = await provider.suggest_tags(self.context)

        self.assertEqual(result, [TagSuggestion("Planning", 0.9)])
        self.assertEqual(calls, 2)
        sleep.assert_awaited_once_with(1.0)

    async def test_compatible_provider_does_not_retry_non_transient_400(self) -> None:
        calls = 0

        def handle(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(400, json={"error": {"message": "bad request"}})

        client_class = providers.httpx.AsyncClient
        transport = providers.httpx.MockTransport(handle)
        provider = providers.ChatCompletionsEnrichmentProvider(
            provider="gemini",
            api_key="test-key",
            model="gemini-test-flash",
            base_url="https://example.invalid",
        )
        with (
            patch.object(
                providers.httpx,
                "AsyncClient",
                side_effect=lambda **kwargs: client_class(transport=transport, **kwargs),
            ),
            patch.object(providers.asyncio, "sleep", new=AsyncMock()) as sleep,
        ):
            with self.assertRaises(AIProviderError):
                await provider.suggest_tags(self.context)

        self.assertEqual(calls, 1)
        sleep.assert_not_awaited()


class DriveAIAcceptanceDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_providers_run_and_failure_mask_identifies_gemini(self) -> None:
        fake_run = AsyncMock(side_effect=[SystemExit(acceptance.EXIT_PROVIDER_FAILURE), None, None, None])
        with (
            patch.object(config.settings, "ai_enrichment_provider", "gemini"),
            patch.object(config.settings, "ai_enrichment_model", "latest-3-flash"),
            patch.object(config.settings, "ai_enrichment_fallback_provider", "openrouter"),
            patch.object(config.settings, "ai_enrichment_fallback_model", "openrouter/free"),
            patch.object(config.settings, "ai_enrichment_tertiary_provider", "groq"),
            patch.object(config.settings, "ai_enrichment_tertiary_model", "openai/gpt-oss-120b"),
            patch.object(acceptance, "run_acceptance", fake_run),
        ):
            with self.assertRaises(SystemExit) as raised:
                await acceptance.run_configured_providers()

        self.assertEqual(raised.exception.code, 91)
        self.assertEqual(fake_run.await_count, 4)
        self.assertEqual(
            [call.kwargs["provider_name"] for call in fake_run.await_args_list],
            ["gemini", "gemini_lite", "groq", "openrouter"],
        )

    async def test_configuration_failure_keeps_specific_exit_code(self) -> None:
        fake_run = AsyncMock(side_effect=[SystemExit(acceptance.EXIT_API_KEY_MISSING), None, None, None])
        with (
            patch.object(config.settings, "ai_enrichment_provider", "gemini"),
            patch.object(config.settings, "ai_enrichment_model", "latest-3-flash"),
            patch.object(config.settings, "ai_enrichment_fallback_provider", "openrouter"),
            patch.object(config.settings, "ai_enrichment_fallback_model", "openrouter/free"),
            patch.object(config.settings, "ai_enrichment_tertiary_provider", "groq"),
            patch.object(config.settings, "ai_enrichment_tertiary_model", "openai/gpt-oss-120b"),
            patch.object(acceptance, "run_acceptance", fake_run),
        ):
            with self.assertRaises(SystemExit) as raised:
                await acceptance.run_configured_providers()

        self.assertEqual(raised.exception.code, acceptance.EXIT_API_KEY_MISSING)
        self.assertEqual(fake_run.await_count, 4)


if __name__ == "__main__":
    unittest.main()
