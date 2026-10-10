import inspect
import unittest
from unittest.mock import AsyncMock, patch
from pathlib import Path

import httpx

from scripts import run_project_drive_runtime_acceptance as acceptance
from scripts import run_notes_product_acceptance as notes_acceptance


class ProjectDriveRuntimeAcceptanceContractTests(unittest.TestCase):
    def test_acceptance_uses_synthetic_identity_and_never_calls_google_drive(self):
        self.assertEqual(
            acceptance.ACCEPTANCE_USER_SUB,
            "acceptance-project-drive-runtime",
        )
        source = inspect.getsource(acceptance)
        self.assertIn("DriveDocument(", source)
        self.assertIn("ProjectDriveDocument", source)
        self.assertIn("explicit_confirmation_value", source)
        self.assertNotIn("get_drive_file_metadata", source)
        self.assertNotIn("googleapis.com", source)

    def test_workflow_runs_only_after_successful_cloud_run_release(self):
        workflow = (
            Path(__file__).parents[2]
            / ".github/workflows/postdeploy-runtime-acceptance.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("github.event.workflow_run.head_sha", workflow)
        self.assertIn(
            "POSTDEPLOY_ACCEPTANCE_JOB: life-assistant-postdeploy-acceptance",
            workflow,
        )
        self.assertIn("scripts.run_project_drive_runtime_acceptance", workflow)
        self.assertIn('gcloud run jobs execute "$POSTDEPLOY_ACCEPTANCE_JOB"', workflow)
        self.assertIn("--max-retries 0", workflow)
        self.assertIn("--task-timeout 5m", workflow)

    def test_acceptance_covers_relation_lifecycle_and_exact_cleanup(self):
        source = inspect.getsource(acceptance)
        for marker in (
            'project_drive_runtime_check={check}:PASS',
            'repeat_attach_idempotent',
            'project_delete_guard',
            'detach_preserves_drive_document',
            'project_delete_after_detach_preserves_document',
            'project_drive_runtime_acceptance=PASS',
        ):
            self.assertIn(marker, source)
        self.assertIn("delete(ProjectDriveDocument)", source)
        self.assertIn("delete(DriveDocument)", source)
        self.assertIn("delete(Project)", source)

    def test_delete_guard_reads_shared_error_envelope(self):
        response = httpx.Response(
            409,
            json={
                "error": {
                    "code": "http_409",
                    "message": "Project has linked Drive documents",
                    "request_id": "acceptance-request",
                }
            },
        )
        self.assertEqual(
            acceptance._error_message(response, "Project delete guard for Drive relation"),
            "Project has linked Drive documents",
        )

    def test_stage_exit_codes_are_unique_and_cover_runtime_path(self):
        expected = {
            "seed_drive_document",
            "project_create",
            "list_empty_before_attach",
            "attach",
            "attach_replay",
            "repeat_attach",
            "list_after_attach",
            "project_delete_guard",
            "detach",
            "list_empty_after_detach",
            "project_delete_after_detach",
            "cleanup",
        }
        self.assertEqual(set(acceptance.STAGE_EXIT_CODES), expected)
        codes = list(acceptance.STAGE_EXIT_CODES.values())
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(20 < code < 126 for code in codes))
        source = inspect.getsource(acceptance)
        self.assertIn("stage={exc.stage}", source)
        self.assertIn("return STAGE_EXIT_CODES[exc.stage]", source)


class PostdeployRolloutIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_notes_and_project_runners_remove_rollout_overrides_on_failure(self):
        for runner, key, error_type in (
            (notes_acceptance, "notes", RuntimeError),
            (acceptance, "projects", acceptance.AcceptanceStageError),
        ):
            with self.subTest(key=key):
                observed = {}

                def fail_client(**kwargs):
                    observed.update(runner.app.dependency_overrides)
                    raise RuntimeError("stop before requests")

                with patch.object(runner, "_cleanup", new_callable=AsyncMock) as cleanup, patch.object(
                    runner.httpx, "AsyncClient", side_effect=fail_client
                ), patch.object(acceptance, "_seed_drive_document", new_callable=AsyncMock):
                    with self.assertRaises(error_type):
                        await runner.run_acceptance()
                cleanup.assert_awaited_once()
                gate = runner.CORE_FEATURE_GATES[key]
                expected = {runner.current_user, gate}
                if runner is acceptance:
                    expected.add(runner.DRIVE_FEATURE_GATE)
                    self.assertIsNone(observed[runner.DRIVE_FEATURE_GATE]())
                self.assertEqual(set(observed), expected)
                self.assertIsNone(observed[gate]())
                self.assertFalse(set(observed) & set(runner.app.dependency_overrides))


if __name__ == "__main__":
    unittest.main()
