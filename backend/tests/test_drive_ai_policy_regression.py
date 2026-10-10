"""Regression: platform provider selection may NEVER replace note candidates."""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.models.curated import LifeAIPolicy
from app.models.drive import DriveNoteLinkSuggestion
from app.services import drive_enrichment as service
from app.services.ai_enrichment_provider import (
    ProviderEnrichmentOutcome,
    RelatedNoteCandidate,
    RelatedNoteSuggestion,
)


class DrivePlatformPolicyRegressionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.document = SimpleNamespace(
            id="document-test", name="Planning research",
            mime_type="application/vnd.google-apps.document",
        )
        self.settings = SimpleNamespace(
            allow_document_content=True,
            auto_tags_enabled=True,
            note_suggestions_enabled=True,
            max_related_note_suggestions=5,
        )
        self.notes = [RelatedNoteCandidate(
            note_id="note-preserved", title="Research plan",
            snippet="Plan", project_id="project-test",
        )]
        self.db = AsyncMock()
        self.db.add = Mock()
        self.db.get.return_value = LifeAIPolicy(
            policy_key="drive", revision=3,
            enabled=True, allowed_providers=["gemini"],
        )
        self.provider = SimpleNamespace(provider_name="gemini", model_name="fixture-model")

    async def _run(self, *, allow_document_content=True, enabled=True):
        self.settings.allow_document_content = allow_document_content
        self.db.get.return_value.enabled = enabled
        outcome = ProviderEnrichmentOutcome(
            status="succeeded" if allow_document_content and enabled else "skipped",
            provider="gemini", model="fixture-model",
            tags=(),
            related_notes=(RelatedNoteSuggestion(
                note_id="note-preserved",
                confidence=0.85, reason="Shared project",
            ),) if allow_document_content and enabled else (),
            error_code=None,
        )
        with (
            patch.object(service.drive_documents, "get_document",
                         AsyncMock(return_value=self.document)),
            patch.object(service, "get_enrichment_settings",
                         AsyncMock(return_value=self.settings)),
            patch.object(service, "_document_projects",
                         AsyncMock(return_value=(["project-test"], ("Project",)))),
            patch.object(service, "_document_tags",
                         AsyncMock(return_value=([], ()))),
            patch.object(service, "_candidate_notes",
                         AsyncMock(return_value=self.notes)),
            patch.object(service, "get_ai_enrichment_provider",
                         return_value=self.provider),
            patch.object(service, "execute_provider_enrichment",
                         AsyncMock(return_value=outcome)) as execution,
            patch.object(service, "_run_view", AsyncMock(return_value={"status": outcome.status})),
        ):
            result = await service.enrich_document(
                self.db, "owner-sub", "document-test", force=True,
            )
        return result, execution

    async def test_policy_selects_provider_without_clobbering_note_candidates(self):
        result, execution = await self._run()
        self.assertEqual(result["status"], "succeeded")
        args, kw = execution.await_args
        self.assertEqual(args[2], self.notes)
        self.assertTrue(kw["allow_ai"])
        created_links = [
            call.args[0] for call in self.db.add.call_args_list
            if isinstance(call.args[0], DriveNoteLinkSuggestion)
        ]
        self.assertEqual([link.note_id for link in created_links], ["note-preserved"])

    async def test_global_pause_disables_processing_even_with_user_consent(self):
        _, execution = await self._run(enabled=False)
        self.assertFalse(execution.await_args.kwargs["allow_ai"])
        self.assertFalse(any(
            isinstance(call.args[0], DriveNoteLinkSuggestion)
            for call in self.db.add.call_args_list
        ))

    async def test_no_personal_content_consent_blocks_processing(self):
        _, execution = await self._run(allow_document_content=False)
        self.assertFalse(execution.await_args.kwargs["allow_ai"])
        self.assertFalse(any(
            isinstance(call.args[0], DriveNoteLinkSuggestion)
            for call in self.db.add.call_args_list
        ))


if __name__ == "__main__":
    unittest.main()
