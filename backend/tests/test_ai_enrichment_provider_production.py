import json
import unittest
from unittest.mock import AsyncMock, patch

from app import config
from app.services import ai_enrichment_provider as providers
from app.services.ai_enrichment_provider import (
    AIEnrichmentProvider,
    AIProviderError,
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    RelatedNoteSuggestion,
    TagSuggestion,
    execute_provider_enrichment,
)


class _ThresholdProvider(AIEnrichmentProvider):
    provider_name = "threshold-test"
    model_name = "deterministic"

    async def suggest_tags(self, document_context):
        del document_context
        return [
            TagSuggestion("below", 0.79),
            TagSuggestion("at-threshold", 0.80),
            TagSuggestion("high", 0.95),
        ]

    async def rank_related_notes(self, document_context, candidate_notes):
        del document_context, candidate_notes
        return [
            RelatedNoteSuggestion("n-low", 0.59, "below"),
            RelatedNoteSuggestion("n-at", 0.60, "at threshold"),
            RelatedNoteSuggestion("n-high", 0.91, "high"),
        ]


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, response, calls):
        self._response = response
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, *, headers, json):
        self._calls.append({"url": url, "headers": headers, "json": json})
        return self._response


class ProductionProviderContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_gemini_discovers_numeric_order_and_tries_only_top_three(self):
        calls = []
        def handle(request):
            if request.method == "GET":
                return providers.httpx.Response(200, json={"models": [
                    {"name": "models/" + name, "supportedGenerationMethods": ["generateContent"]}
                    for name in ("gemini-3.8-flash", "gemini-3.10-flash", "gemini-3.9-flash",
                                 "gemini-3.7-flash", "gemini-3.11-flash-lite", "gemini-4.0-flash-preview")
                ]})
            model = json.loads(request.content)["model"]
            calls.append(model)
            if model != "gemini-3.8-flash":
                return providers.httpx.Response(503, json={})
            return providers.httpx.Response(200, json={"choices": [{
                "finish_reason": "stop", "message": {"content": '{"tags":[]}'},
            }]})
        client_class = providers.httpx.AsyncClient
        with (
            patch.object(providers.httpx, "AsyncClient", side_effect=lambda **kw: client_class(
                transport=providers.httpx.MockTransport(handle), **kw,
            )),
            patch.object(providers.asyncio, "sleep", new=AsyncMock()),
            patch.object(
                providers,
                "load_ai_provider_preference",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                providers,
                "remember_ai_provider_preference",
                new=AsyncMock(),
            ),
        ):
            provider = providers.LatestGeminiEnrichmentProvider(api_key="test-key")
            self.assertEqual(await provider.suggest_tags(self.context), [])
            self.assertEqual(
                calls,
                ["gemini-3.10-flash", "gemini-3.9-flash", "gemini-3.8-flash"],
            )
            calls.clear()
            self.assertEqual(await provider.suggest_tags(self.context), [])
            self.assertEqual(calls, ["gemini-3.8-flash"])

            calls.clear()
            provider._models = ["gemini-3.10-flash", "gemini-3.9-flash", "gemini-3.7-flash"]
            provider._available_models = list(provider._models)
            provider._preferred_model = None
            provider._preference_loaded = True
            with self.assertRaises(AIProviderError):
                await provider.suggest_tags(self.context)
            self.assertEqual(len(calls), 9)

    async def test_gemini_flash_lite_has_independent_sticky_preference_and_three_slots(self):
        calls = []
        def handle(request):
            if request.method == "GET":
                return providers.httpx.Response(200, json={"models": [
                    {"name": "models/" + name, "supportedGenerationMethods": ["generateContent"]}
                    for name in (
                        "gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
                        "gemini-3.0-flash-lite", "gemini-4.0-flash-lite-preview",
                        "gemini-3.8-flash", "gemini-3.8-flash-lite-tts",
                    )
                ]})
            model = json.loads(request.content)["model"]
            calls.append(model)
            if model != "gemini-3.0-flash-lite":
                return providers.httpx.Response(503, json={})
            return providers.httpx.Response(200, json={"choices": [
                {"finish_reason": "stop", "message": {"content": '{"tags":[]}'}}]})
        original = providers.httpx.AsyncClient
        with (
            patch.object(providers.httpx, "AsyncClient", side_effect=lambda **kw: original(
                transport=providers.httpx.MockTransport(handle), **kw)),
            patch.object(providers.asyncio, "sleep", new=AsyncMock()),
            patch.object(providers, "load_ai_provider_preference", new=AsyncMock(
                side_effect=lambda key: "gemini-3.0-flash-lite" if key == "gemini_lite" else None)),
            patch.object(providers, "remember_ai_provider_preference", new=AsyncMock()) as remember,
        ):
            lite = providers.LatestGeminiEnrichmentProvider(api_key="test-key", variant="flash-lite")
            self.assertEqual(await lite.suggest_tags(self.context), [])
            self.assertEqual(calls, ["gemini-3.0-flash-lite"])
            self.assertEqual(lite._models, [
                "gemini-3.0-flash-lite", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"])
            remember.assert_awaited_once_with("gemini_lite", "gemini-3.0-flash-lite")
            calls.clear()
            self.assertEqual(await lite.suggest_tags(self.context), [])
            self.assertEqual(calls, ["gemini-3.0-flash-lite"])

    async def test_gemini_lite_explicit_adapter_reuses_gemini_api_key(self):
        with (
            patch.object(config.settings, "gemini_api_key", "test-key"),
            patch.object(config.settings, "codex_primary_enabled", False),
        ):
            provider = providers.get_ai_enrichment_provider(
                provider="gemini_lite", model="latest-3-flash-lite")
        self.assertIsInstance(provider, providers.LatestGeminiEnrichmentProvider)
        self.assertEqual(provider.provider_name, "gemini_lite")
        self.assertEqual(provider.model_name, "latest-3-flash-lite")

    async def test_latest_gemini_stops_model_sweep_on_rate_limit(self):
        calls = []

        def handle(request):
            if request.method == "GET":
                return providers.httpx.Response(200, json={"models": [
                    {"name": "models/" + name, "supportedGenerationMethods": ["generateContent"]}
                    for name in (
                        "gemini-4.0-flash",
                        "gemini-3.9-flash",
                        "gemini-3.8-flash",
                    )
                ]})
            model = json.loads(request.content)["model"]
            calls.append(model)
            return providers.httpx.Response(429, json={"error": {"message": "rate limited"}})

        client_class = providers.httpx.AsyncClient
        with (
            patch.object(providers.httpx, "AsyncClient", side_effect=lambda **kw: client_class(
                transport=providers.httpx.MockTransport(handle), **kw,
            )),
            patch.object(
                providers,
                "load_ai_provider_preference",
                new=AsyncMock(return_value=None),
            ),
        ):
            provider = providers.LatestGeminiEnrichmentProvider(api_key="test-key")
            with self.assertRaises(AIProviderError) as raised:
                await provider.suggest_tags(self.context)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(calls, ["gemini-4.0-flash"])

    async def test_latest_gemini_prefers_persisted_success_even_outside_newest_three(self):
        calls = []

        def handle(request):
            if request.method == "GET":
                return providers.httpx.Response(200, json={"models": [
                    {"name": "models/" + name, "supportedGenerationMethods": ["generateContent"]}
                    for name in (
                        "gemini-4.0-flash",
                        "gemini-3.9-flash",
                        "gemini-3.8-flash",
                        "gemini-3.6-flash",
                    )
                ]})
            model = json.loads(request.content)["model"]
            calls.append(model)
            return providers.httpx.Response(200, json={"choices": [{
                "finish_reason": "stop",
                "message": {"content": '{"tags":[]}'},
            }]})

        client_class = providers.httpx.AsyncClient
        remember = AsyncMock()
        with (
            patch.object(providers.httpx, "AsyncClient", side_effect=lambda **kw: client_class(
                transport=providers.httpx.MockTransport(handle), **kw,
            )),
            patch.object(
                providers,
                "load_ai_provider_preference",
                new=AsyncMock(return_value="gemini-3.6-flash"),
            ),
            patch.object(
                providers,
                "remember_ai_provider_preference",
                new=remember,
            ),
        ):
            provider = providers.LatestGeminiEnrichmentProvider(api_key="test-key")
            self.assertEqual(await provider.suggest_tags(self.context), [])

        self.assertEqual(calls, ["gemini-3.6-flash"])
        remember.assert_awaited_once_with("gemini", "gemini-3.6-flash")

    async def test_compatible_providers_use_vendor_endpoints_and_structured_output(self):
        for name, endpoint in (
            ("gemini", "https://generativelanguage.googleapis.com/v1beta/openai"),
            ("openrouter", "https://openrouter.ai/api/v1"),
            ("groq", "https://api.groq.com/openai/v1"),
        ):
            with (
                self.subTest(provider=name),
                patch.object(config.settings, "ai_enrichment_provider", name),
                patch.object(config.settings, "ai_enrichment_model", "test-model"),
                patch.object(config.settings, f"{name}_api_key", "test-key"),
                patch.object(config.settings, "ai_enrichment_fallback_provider", ""),
                patch.object(config.settings, "ai_enrichment_tertiary_provider", ""),
            ):
                provider = providers.get_ai_enrichment_provider()
                self.assertEqual(provider.provider_name, name)
                calls = []
                response = _FakeResponse(200, {"choices": [{
                    "finish_reason": "stop",
                    "message": {"content": '{"tags":[{"name":"Planning","confidence":0.92}]}'},
                }]})
                with patch.object(providers.httpx, "AsyncClient", side_effect=lambda **_: _FakeClient(response, calls)):
                    self.assertEqual(await provider.suggest_tags(self.context), [TagSuggestion("Planning", 0.92)])
                self.assertEqual(calls[0]["url"], endpoint + "/chat/completions")
                if name == "gemini":
                    self.assertEqual(calls[0]["json"]["reasoning_effort"], "low")
                if name == "openrouter":
                    self.assertEqual(calls[0]["json"]["response_format"], {"type": "json_object"})
                    self.assertIn('"required": ["tags"]', calls[0]["json"]["messages"][0]["content"])
                else:
                    self.assertTrue(calls[0]["json"]["response_format"]["json_schema"]["strict"])
                self.assertNotIn("test-key", json.dumps(calls[0]["json"]))
                if name == "openrouter":
                    self.assertEqual(calls[0]["json"]["provider"]["data_collection"], "deny")

    async def test_fallback_runs_once_per_failed_stage_and_preserves_errors(self):
        primary, fallback = _ThresholdProvider(), _ThresholdProvider()
        primary.provider_name, fallback.provider_name = "gemini", "openrouter"
        primary.suggest_tags = AsyncMock(side_effect=AIProviderError("provider_http_error"))
        fallback.suggest_tags = AsyncMock(return_value=[TagSuggestion("Planning", 0.92)])
        routed = providers.FallbackAIEnrichmentProvider(primary, fallback)
        self.assertEqual(await routed.suggest_tags(self.context), [TagSuggestion("Planning", 0.92)])
        fallback.suggest_tags.assert_awaited_once()
        fallback.suggest_tags.side_effect = AIProviderError("provider_invalid_output")
        with self.assertRaises(AIProviderError):
            await routed.suggest_tags(self.context)
        primary.suggest_tags = AsyncMock(return_value=[])
        fallback.suggest_tags.reset_mock()
        self.assertEqual(await routed.suggest_tags(self.context), [])
        fallback.suggest_tags.assert_not_awaited()

    async def test_three_provider_chain_uses_groq_only_after_first_two_fail(self):
        calls = []
        async def failed(name):
            calls.append(name)
            raise AIProviderError("provider_http_error")
        gemini, router, groq = _ThresholdProvider(), _ThresholdProvider(), _ThresholdProvider()
        async def gemini_failed(_):
            return await failed("gemini")
        async def router_failed(_):
            return await failed("openrouter")
        gemini.suggest_tags = AsyncMock(side_effect=gemini_failed)
        router.suggest_tags = AsyncMock(side_effect=router_failed)
        groq.suggest_tags = AsyncMock(return_value=[TagSuggestion("Planning", 0.9)])
        chain = providers.FallbackAIEnrichmentProvider(gemini, providers.FallbackAIEnrichmentProvider(router, groq))
        self.assertEqual(await chain.suggest_tags(self.context), [TagSuggestion("Planning", 0.9)])
        self.assertEqual(calls, ["gemini", "openrouter"])
        groq.suggest_tags.assert_awaited_once()

    async def test_compatible_provider_rejects_malformed_or_truncated_response(self):
        provider = providers.ChatCompletionsEnrichmentProvider(
            provider="gemini", api_key="test-key", model="test-model", base_url="https://example.invalid",
        )
        for payload in ({}, {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
                        {"choices": [{"finish_reason": "stop", "message": {"content": "[]"}}]}):
            with patch.object(providers.httpx, "AsyncClient", side_effect=lambda **_: _FakeClient(_FakeResponse(200, payload), [])):
                with self.assertRaises(AIProviderError):
                    await provider.suggest_tags(self.context)

    def test_cache_identity_changes_with_provider_model_and_fallback_policy(self):
        fingerprint = providers.compute_enrichment_fingerprint
        baseline = fingerprint(self.context, provider="gemini", model="model-a")
        self.assertNotEqual(baseline, fingerprint(self.context, provider="openrouter", model="model-a"))
        self.assertNotEqual(baseline, fingerprint(self.context, provider="gemini", model="model-b"))
        self.assertNotEqual(baseline, fingerprint(self.context, provider="gemini+openrouter", model="model-a+model-b"))

    def setUp(self):
        self.context = DocumentEnrichmentContext(
            document_id="document-1",
            title="Quarterly roadmap",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded Drive document text",
            project_context=("Roadmap project",),
            existing_tags=("planning",),
            max_related_notes=5,
        )
        self.candidates = [
            RelatedNoteCandidate(
                note_id="n-low",
                title="Low",
                snippet="low snippet",
                project_id="p1",
            ),
            RelatedNoteCandidate(
                note_id="n-at",
                title="At threshold",
                snippet="threshold snippet",
                project_id="p1",
            ),
            RelatedNoteCandidate(
                note_id="n-high",
                title="High",
                snippet="high snippet",
                project_id=None,
            ),
        ]

    async def test_thresholds_are_enforced_before_results_become_authoritative(self):
        outcome = await execute_provider_enrichment(
            _ThresholdProvider(),
            self.context,
            self.candidates,
            allow_ai=True,
            enable_tags=True,
            enable_related_notes=True,
        )
        self.assertEqual([tag.name for tag in outcome.tags], ["at-threshold", "high"])
        self.assertEqual(
            [item.note_id for item in outcome.related_notes],
            ["n-high", "n-at"],
        )

    def test_resolver_is_disabled_by_default_and_requires_complete_openai_config(self):
        openai_cls = getattr(providers, "OpenAIResponsesEnrichmentProvider", None)
        self.assertTrue(callable(openai_cls))

        with (
            patch.object(config.settings, "ai_enrichment_provider", "disabled", create=True),
            patch.object(config.settings, "ai_enrichment_model", "", create=True),
            patch.object(config.settings, "openai_api_key", "", create=True),
        ):
            resolved = providers.get_ai_enrichment_provider()
            self.assertEqual(resolved.provider_name, "disabled")

        with (
            patch.object(config.settings, "ai_enrichment_provider", "openai", create=True),
            patch.object(config.settings, "ai_enrichment_model", "gpt-test", create=True),
            patch.object(config.settings, "openai_api_key", "", create=True),
        ):
            resolved = providers.get_ai_enrichment_provider()
            self.assertEqual(resolved.provider_name, "disabled")

        with (
            patch.object(config.settings, "ai_enrichment_provider", "openai", create=True),
            patch.object(config.settings, "ai_enrichment_model", "gpt-test", create=True),
            patch.object(config.settings, "openai_api_key", "test-key", create=True),
            patch.object(
                config.settings,
                "openai_base_url",
                "https://api.openai.com/v1",
                create=True,
            ),
        ):
            resolved = providers.get_ai_enrichment_provider()
            self.assertIsInstance(resolved, openai_cls)
            self.assertEqual(resolved.model_name, "gpt-test")

    async def test_openai_tag_call_uses_responses_structured_output_and_minimal_context(self):
        openai_cls = getattr(providers, "OpenAIResponsesEnrichmentProvider", None)
        self.assertTrue(callable(openai_cls))
        if not callable(openai_cls):
            return

        calls = []
        response = _FakeResponse(
            200,
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "tags": [
                                            {"name": "Planning", "confidence": 0.92}
                                        ]
                                    }
                                ),
                            }
                        ],
                    }
                ],
            },
        )
        provider = openai_cls(
            api_key="test-secret-key",
            model="gpt-test",
            base_url="https://api.openai.com/v1",
        )
        with patch.object(
            providers.httpx,
            "AsyncClient",
            side_effect=lambda **_kwargs: _FakeClient(response, calls),
        ):
            tags = await provider.suggest_tags(self.context)

        self.assertEqual(tags, [TagSuggestion("Planning", 0.92)])
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(call["headers"]["Authorization"], "Bearer test-secret-key")
        body = call["json"]
        self.assertEqual(body["model"], "gpt-test")
        self.assertFalse(body["store"])
        output_format = body["text"]["format"]
        self.assertEqual(output_format["type"], "json_schema")
        self.assertTrue(output_format["strict"])
        self.assertEqual(output_format["name"], "drive_tag_suggestions")
        serialized = json.dumps(body, ensure_ascii=False)
        self.assertIn("Quarterly roadmap", serialized)
        self.assertIn("bounded Drive document text", serialized)
        self.assertIn("Roadmap project", serialized)
        self.assertIn("planning", serialized)
        self.assertNotIn("test-secret-key", serialized)
        self.assertNotIn("oauth", serialized.lower())
        self.assertNotIn("permission", serialized.lower())

    async def test_openai_note_rerank_is_candidate_bounded_and_returns_structured_results(self):
        openai_cls = getattr(providers, "OpenAIResponsesEnrichmentProvider", None)
        self.assertTrue(callable(openai_cls))
        if not callable(openai_cls):
            return

        calls = []
        response = _FakeResponse(
            200,
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "related_notes": [
                                            {
                                                "note_id": "n-high",
                                                "confidence": 0.88,
                                                "reason": "Same roadmap topic",
                                            }
                                        ]
                                    }
                                ),
                            }
                        ],
                    }
                ],
            },
        )
        provider = openai_cls(
            api_key="test-secret-key",
            model="gpt-test",
            base_url="https://api.openai.com/v1",
        )
        with patch.object(
            providers.httpx,
            "AsyncClient",
            side_effect=lambda **_kwargs: _FakeClient(response, calls),
        ):
            notes = await provider.rank_related_notes(self.context, self.candidates)

        self.assertEqual(
            notes,
            [RelatedNoteSuggestion("n-high", 0.88, "Same roadmap topic")],
        )
        body = calls[0]["json"]
        self.assertEqual(body["text"]["format"]["name"], "drive_related_note_suggestions")
        serialized = json.dumps(body, ensure_ascii=False)
        for candidate in self.candidates:
            self.assertIn(candidate.note_id, serialized)
            self.assertIn(candidate.title, serialized)
            self.assertIn(candidate.snippet, serialized)
        self.assertNotIn("test-secret-key", serialized)

    async def test_openai_provider_maps_http_and_invalid_output_to_stable_provider_errors(self):
        openai_cls = getattr(providers, "OpenAIResponsesEnrichmentProvider", None)
        self.assertTrue(callable(openai_cls))
        if not callable(openai_cls):
            return

        provider = openai_cls(
            api_key="test-secret-key",
            model="gpt-test",
            base_url="https://api.openai.com/v1",
        )
        with patch.object(
            providers.httpx,
            "AsyncClient",
            side_effect=lambda **_kwargs: _FakeClient(
                _FakeResponse(429, {"error": {"message": "rate limited"}}),
                [],
            ),
        ):
            with self.assertRaises(AIProviderError) as raised:
                await provider.suggest_tags(self.context)
        self.assertEqual(raised.exception.code, "provider_http_error")

        with patch.object(
            providers.httpx,
            "AsyncClient",
            side_effect=lambda **_kwargs: _FakeClient(
                _FakeResponse(200, {"status": "completed", "output": []}),
                [],
            ),
        ):
            with self.assertRaises(AIProviderError) as raised:
                await provider.suggest_tags(self.context)
        self.assertEqual(raised.exception.code, "provider_invalid_output")


if __name__ == "__main__":
    unittest.main()
