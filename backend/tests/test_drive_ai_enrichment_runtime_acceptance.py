import py_compile
import unittest
import uuid
from unittest.mock import AsyncMock, patch
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.curated import FeatureRollout

from scripts import run_drive_ai_enrichment_acceptance as acceptance
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

    def test_synthetic_provider_resolver_supports_owner_id_keyword(self):
        provider = acceptance.AcceptanceProvider(
            "existing-tag", "generated-tag", ("note-one", "note-two")
        )
        resolver = acceptance._acceptance_provider_resolver(provider)
        self.assertIs(resolver(owner_id=uuid.uuid4()), provider)
        self.assertEqual(provider.tag_calls, 0)
        self.assertEqual(provider.note_calls, 0)

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
            "workflow_dispatch:",
            "github.event_name == 'workflow_dispatch'",
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


class DriveAIEnrichmentRolloutIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_hidden_drive_gate_is_scoped_to_runner_and_consent_stays_off(self):
        db = AsyncMock(spec=AsyncSession)
        db.get.side_effect = lambda model, key: (
            FeatureRollout(feature_key="drive", status="hidden", audience="all")
            if model is FeatureRollout else None
        )

        async def mock_db():
            yield db

        overrides = acceptance.app.dependency_overrides
        original = dict(overrides)
        overrides.update({get_db: mock_db, acceptance.current_user: acceptance._acceptance_user})
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=acceptance.app), base_url="http://test"
            ) as client:
                path = "/api/v1/drive/enrichment/settings"
                self.assertEqual((await client.get(path)).status_code, 403)
                overrides[acceptance.DRIVE_FEATURE_GATE] = lambda: None
                response = await client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.json()["allow_document_content"])
                overrides.pop(acceptance.DRIVE_FEATURE_GATE)
                self.assertEqual((await client.get(path)).status_code, 403)
        finally:
            overrides.clear()
            overrides.update(original)

    async def test_runner_overrides_registered_drive_gate_and_removes_it_on_failure(self):
        observed = {}

        def fail_client(**kwargs):
            observed.update(acceptance.app.dependency_overrides)
            raise RuntimeError("stop before requests")

        with patch.object(acceptance, "_seed", new_callable=AsyncMock), patch.object(
            acceptance, "_cleanup", new_callable=AsyncMock
        ) as cleanup, patch.object(
            acceptance.httpx, "AsyncClient", side_effect=fail_client
        ):
            with self.assertRaises(acceptance.AcceptanceStageError):
                await acceptance.run_acceptance()
        cleanup.assert_awaited_once()
        self.assertEqual(set(observed), {acceptance.current_user, acceptance.DRIVE_FEATURE_GATE})
        self.assertIsNone(observed[acceptance.DRIVE_FEATURE_GATE]())
        self.assertFalse(set(observed) & set(acceptance.app.dependency_overrides))


if __name__ == "__main__":
    unittest.main()
