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
