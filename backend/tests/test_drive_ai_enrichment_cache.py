import unittest

from app.services.ai_enrichment_provider import (
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    compute_enrichment_fingerprint,
)


class DriveAIEnrichmentCacheContractTests(unittest.TestCase):
    def test_content_fingerprint_does_not_self_invalidate_on_enrichment_outputs(self):
        before = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded source text",
            project_context=("Research",),
            existing_tags=("AI", "Planning"),
            max_related_notes=5,
        )
        after = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded source text",
            project_context=("Research",),
            existing_tags=("AI", "Planning", "Research"),
            max_related_notes=5,
        )
        candidates_before = [
            RelatedNoteCandidate(
                note_id="note-1",
                title="Research plan",
                snippet="Quarterly planning",
                project_id="project-1",
            )
        ]
        candidates_after = candidates_before + [
            RelatedNoteCandidate(
                note_id="note-2",
                title="Newly discoverable after AI Tag attachment",
                snippet="This candidate is an enrichment side effect.",
                project_id="project-1",
            )
        ]

        self.assertEqual(
            compute_enrichment_fingerprint(before, candidates_before),
            compute_enrichment_fingerprint(after, candidates_after),
        )

    def test_content_fingerprint_changes_when_source_or_user_settings_change(self):
        base = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded source text",
            project_context=("Research",),
            existing_tags=("AI",),
            max_related_notes=5,
        )
        changed_text = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="changed source text",
            project_context=("Research",),
            existing_tags=("AI",),
            max_related_notes=5,
        )
        changed_limit = DocumentEnrichmentContext(
            document_id="doc-1",
            title="Quarterly research notes",
            mime_type="application/vnd.google-apps.document",
            document_text="bounded source text",
            project_context=("Research",),
            existing_tags=("AI",),
            max_related_notes=3,
        )

        base_fp = compute_enrichment_fingerprint(base)
        self.assertNotEqual(base_fp, compute_enrichment_fingerprint(changed_text))
        self.assertNotEqual(base_fp, compute_enrichment_fingerprint(changed_limit))
        self.assertNotEqual(
            base_fp,
            compute_enrichment_fingerprint(base, enable_tags=False),
        )


if __name__ == "__main__":
    unittest.main()
