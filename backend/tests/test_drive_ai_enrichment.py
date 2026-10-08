import asyncio
import unittest

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.main import app
from app.models.drive import (
    DriveDocumentEnrichmentRun,
    DriveEnrichmentSettings,
    DriveNoteLinkSuggestion,
)
from app.models.drive_schemas import (
    DriveEnrichmentRunRequest,
    DriveEnrichmentSettingsOut,
    DriveEnrichmentSettingsUpdate,
    DriveNoteSuggestionDecision,
)
from app.services.ai_enrichment_provider import (
    AIEnrichmentProvider,
    AIProviderError,
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    RelatedNoteSuggestion,
    TagSuggestion,
    compute_enrichment_fingerprint,
    execute_provider_enrichment,
)


class _FakeProvider(AIEnrichmentProvider):
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self, *, fail_tags: bool = False, fail_notes: bool = False):
        self.fail_tags = fail_tags
        self.fail_notes = fail_notes
        self.tag_calls = 0
        self.note_calls = 0

    async def suggest_tags(self, document_context: DocumentEnrichmentContext):
        self.tag_calls += 1
        if self.fail_tags:
            raise AIProviderError("tag_stage_failed")
        return [TagSuggestion(name="Research", confidence=0.91)]

    async def rank_related_notes(
        self,
        document_context: DocumentEnrichmentContext,
        candidate_notes: list[RelatedNoteCandidate],
    ):
        self.note_calls += 1
        if self.fail_notes:
            raise AIProviderError("note_stage_failed")
        if not candidate_notes:
            return []
        return [
            RelatedNoteSuggestion(
                note_id=candidate_notes[0].note_id,
                confidence=0.82,
                reason="Same project and topic",
            )
        ]


class DriveAIEnrichmentContractTests(unittest.TestCase):
    def _context(self) -> DocumentEnrichmentContext:
        return DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded source text",
            project_context=("Research",),
            existing_tags=("AI", "Planning"),
            max_related_notes=5,
        )

    def test_persistence_models_have_required_status_and_decision_constraints(self):
        self.assertFalse(DriveEnrichmentSettings.__table__.c.user_sub.nullable)
        self.assertTrue(DriveEnrichmentSettings.__table__.c.auto_tags_enabled.default.arg)
        self.assertTrue(DriveEnrichmentSettings.__table__.c.note_suggestions_enabled.default.arg)
        self.assertFalse(DriveEnrichmentSettings.__table__.c.allow_document_content.default.arg)
        self.assertEqual(
            DriveEnrichmentSettings.__table__.c.max_related_note_suggestions.default.arg,
            5,
        )

        run_checks = {
            constraint.name: str(constraint.sqltext)
            for constraint in DriveDocumentEnrichmentRun.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        self.assertIn("succeeded", run_checks["ck_drive_enrichment_run_status"])
        self.assertIn("partial", run_checks["ck_drive_enrichment_run_status"])
        self.assertIn("failed", run_checks["ck_drive_enrichment_run_status"])
        self.assertIn("skipped", run_checks["ck_drive_enrichment_run_status"])

        suggestion_checks = {
            constraint.name: str(constraint.sqltext)
            for constraint in DriveNoteLinkSuggestion.__table__.constraints
            if isinstance(constraint, CheckConstraint)
        }
        self.assertIn("pending", suggestion_checks["ck_drive_note_suggestion_decision"])
        self.assertIn("accepted", suggestion_checks["ck_drive_note_suggestion_decision"])
        self.assertIn("rejected", suggestion_checks["ck_drive_note_suggestion_decision"])

        uniques = {
            tuple(column.name for column in constraint.columns)
            for constraint in DriveNoteLinkSuggestion.__table__.constraints
            if isinstance(constraint, UniqueConstraint)
        }
        self.assertIn(("enrichment_run_id", "note_id"), uniques)

    def test_settings_contract_defaults_to_explicit_content_opt_in(self):
        defaults = DriveEnrichmentSettingsOut(
            auto_tags_enabled=True,
            note_suggestions_enabled=True,
            allow_document_content=False,
            max_related_note_suggestions=5,
        )
        self.assertFalse(defaults.allow_document_content)
        self.assertEqual(defaults.max_related_note_suggestions, 5)

        update = DriveEnrichmentSettingsUpdate(
            allow_document_content=True,
            max_related_note_suggestions=3,
        )
        self.assertTrue(update.allow_document_content)
        self.assertEqual(update.max_related_note_suggestions, 3)
        with self.assertRaises(ValueError):
            DriveEnrichmentSettingsUpdate(max_related_note_suggestions=0)

    def test_enrichment_request_defaults_to_cache_reuse(self):
        body = DriveEnrichmentRunRequest()
        self.assertFalse(body.force)

    def test_suggestion_decision_only_allows_accept_or_reject(self):
        self.assertEqual(DriveNoteSuggestionDecision(decision="accepted").decision, "accepted")
        self.assertEqual(DriveNoteSuggestionDecision(decision="rejected").decision, "rejected")
        with self.assertRaises(ValueError):
            DriveNoteSuggestionDecision(decision="pending")

    def test_fingerprint_is_deterministic_and_changes_with_relevant_context(self):
        first = self._context()
        equivalent = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded source text",
            project_context=("Research",),
            existing_tags=("Planning", "AI"),
            max_related_notes=5,
        )
        changed = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="changed source text",
            project_context=("Research",),
            existing_tags=("AI", "Planning"),
            max_related_notes=5,
        )
        self.assertEqual(
            compute_enrichment_fingerprint(first),
            compute_enrichment_fingerprint(equivalent),
        )
        self.assertNotEqual(
            compute_enrichment_fingerprint(first),
            compute_enrichment_fingerprint(changed),
        )

    def test_consent_disabled_skips_without_provider_calls(self):
        provider = _FakeProvider()
        outcome = asyncio.run(
            execute_provider_enrichment(
                provider,
                self._context(),
                [],
                allow_ai=False,
                enable_tags=True,
                enable_related_notes=True,
            )
        )
        self.assertEqual(outcome.status, "skipped")
        self.assertEqual(outcome.error_code, "consent_disabled")
        self.assertEqual(provider.tag_calls, 0)
        self.assertEqual(provider.note_calls, 0)

    def test_one_provider_stage_failure_is_partial_and_keeps_successful_output(self):
        provider = _FakeProvider(fail_notes=True)
        candidates = [
            RelatedNoteCandidate(
                note_id="note-1",
                title="Research plan",
                snippet="Quarterly planning",
                project_id="project-1",
            )
        ]
        outcome = asyncio.run(
            execute_provider_enrichment(
                provider,
                self._context(),
                candidates,
                allow_ai=True,
                enable_tags=True,
                enable_related_notes=True,
            )
        )
        self.assertEqual(outcome.status, "partial")
        self.assertEqual(outcome.error_code, "note_stage_failed")
        self.assertEqual([item.name for item in outcome.tags], ["Research"])
        self.assertEqual(outcome.related_notes, ())

    def test_both_provider_stages_success_is_succeeded(self):
        provider = _FakeProvider()
        candidates = [
            RelatedNoteCandidate(
                note_id="note-1",
                title="Research plan",
                snippet="Quarterly planning",
                project_id="project-1",
            )
        ]
        outcome = asyncio.run(
            execute_provider_enrichment(
                provider,
                self._context(),
                candidates,
                allow_ai=True,
                enable_tags=True,
                enable_related_notes=True,
            )
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.error_code, None)
        self.assertEqual([item.name for item in outcome.tags], ["Research"])
        self.assertEqual([item.note_id for item in outcome.related_notes], ["note-1"])

    def test_drive_enrichment_routes_are_registered(self):
        paths = set(app.openapi()["paths"])
        expected = {
            "/api/v1/drive/enrichment/settings",
            "/api/v1/drive/documents/{document_id}/enrichment",
            "/api/v1/drive/note-suggestions/{suggestion_id}/decision",
        }
        self.assertTrue(expected.issubset(paths))


if __name__ == "__main__":
    unittest.main()
