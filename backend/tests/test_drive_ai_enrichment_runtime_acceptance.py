import py_compile
import unittest
from pathlib import Path


class DriveAIEnrichmentRuntimeAcceptanceContractTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).parents[2]
        self.script_path = (
            self.repo_root / "backend/scripts/run_drive_ai_enrichment_acceptance.py"
        )
        self.workflow_path = (
            self.repo_root / ".github/workflows/postdeploy-runtime-acceptance.yml"
        )

    def test_runtime_acceptance_script_exists_and_compiles(self):
        self.assertTrue(self.script_path.is_file())
        py_compile.compile(str(self.script_path), doraise=True)

    def test_runner_covers_privacy_cache_tags_suggestions_and_exact_cleanup(self):
        source = self.script_path.read_text(encoding="utf-8")
        for expected in (
            "ACCEPTANCE_USER_SUB",
            "AIEnrichmentProvider",
            "consent_disabled",
            "allow_document_content",
            "cache_hit",
            "ai_accepted",
            "accepted",
            "rejected",
            "DriveNoteLinkSuggestion",
            "EntityTag",
            "NoteDriveDocument",
            "cleanup",
            "drive_ai_runtime_acceptance=PASS",
        ):
            self.assertIn(expected, source)
        self.assertNotIn("googleapis.com", source)
        self.assertNotIn("OPENAI_API_KEY", source)
        self.assertNotIn("ANTHROPIC_API_KEY", source)

    def test_workflow_runs_exact_release_image_after_successful_cloud_run_release(self):
        self.assertTrue(self.workflow_path.is_file())
        source = self.workflow_path.read_text(encoding="utf-8")
        for expected in (
            "workflows: [Deploy Cloud Run]",
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.head_sha || github.sha",
            "life-assistant-backend",
            "POSTDEPLOY_ACCEPTANCE_JOB: life-assistant-postdeploy-acceptance",
            'echo "ref=${IMAGE_BASE}@${IMAGE_DIGEST}"',
            '--image "${{ steps.image.outputs.ref }}"',
            'gcloud run jobs execute "$POSTDEPLOY_ACCEPTANCE_JOB"',
            "scripts.run_drive_ai_enrichment_acceptance",
            "--update-secrets LIFE_ASSISTANT_BUNDLE=life-assistant-bundle:latest",
        ):
            self.assertIn(expected, source)


if __name__ == "__main__":
    unittest.main()
