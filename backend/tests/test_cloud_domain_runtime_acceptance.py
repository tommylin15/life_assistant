from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from scripts import run_cloud_domain_parity_acceptance as runner


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "run_cloud_domain_parity_acceptance.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class CloudDomainRuntimeAcceptanceContractTests(unittest.TestCase):
    def test_failure_diagnostic_does_not_print_response_body(self):
        response = httpx.Response(403, text="private response body")
        with patch("builtins.print") as output:
            with self.assertRaises(AssertionError):
                runner._expect(response, 201, "note create")
        output.assert_called_once_with(
            "acceptance_http_failure=note create:expected=201:actual=403", flush=True
        )

    def test_runtime_acceptance_script_exists(self):
        self.assertTrue(
            SCRIPT.is_file(),
            "dev-test cloud-domain acceptance runner must exist",
        )

    def test_runner_covers_required_api_and_cleanup_contract(self):
        source = SCRIPT.read_text(encoding="utf-8")
        compile(source, str(SCRIPT), "exec")
        for required in (
            "/api/v1/projects",
            "/api/v1/notes",
            "/api/v1/habits",
            "/api/v1/shopping-lists",
            "/api/v1/shopping-items",
            "/api/v1/templates",
            "/api/v1/activity",
            "app.dependency_overrides[current_user]",
            "[ACCEPTANCE TEST]",
            "cleanup_exact_artifacts",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_runner_exposes_phase_exit_codes_without_cloud_logging(self):
        source = SCRIPT.read_text(encoding="utf-8")
        compile(source, str(SCRIPT), "exec")
        for required in (
            "LAST_PASSED_CHECK",
            "FAILURE_EXIT_CODES",
            '"bootstrap": 41',
            '"project_create": 51',
            '"note_a_create": 52',
            '"project_delete_guard_note": 42',
            '"note_crud_link_persistence": 43',
            '"project_delete_guard_shopping": 44',
            '"shopping_nested_persistence": 45',
            '"habit_append_history_persistence": 46',
            '"template_opaque_payload_persistence": 47',
            '"project_delete_after_unlink": 48',
            '"execution_log": 49',
            "acceptance_failure_phase=",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_deploy_workflow_runs_acceptance_after_runtime_health(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("CORE_ACCEPTANCE_JOB: life-assistant-core-acceptance", workflow)
        self.assertIn("Configure shared core acceptance runner", workflow)
        self.assertIn("Run authenticated cloud-domain acceptance", workflow)
        self.assertIn("--args=-m,scripts.run_cloud_domain_parity_acceptance", workflow)
        self.assertIn('--image "${{ steps.backend_image.outputs.ref }}"', workflow)
        self.assertIn('gcloud run jobs execute "$CORE_ACCEPTANCE_JOB"', workflow)
        self.assertLess(
            workflow.index("Verify unauthenticated API is application-protected"),
            workflow.index("Configure shared core acceptance runner"),
        )
        self.assertLess(
            workflow.index("Configure shared core acceptance runner"),
            workflow.index("Run authenticated cloud-domain acceptance"),
        )


class CloudDomainRolloutIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_rollout_and_identity_overrides_are_removed_on_failure(self):
        observed = {}

        def fail_client(**kwargs):
            observed.update(runner.app.dependency_overrides)
            raise RuntimeError("stop before writes")

        with patch.object(runner.httpx, "AsyncClient", side_effect=fail_client), patch.object(
            runner, "cleanup_exact_artifacts", new_callable=AsyncMock
        ) as cleanup:
            with self.assertRaisesRegex(RuntimeError, "stop before writes"):
                await runner.run_acceptance()
        cleanup.assert_awaited_once()
        self.assertIn(runner.current_user, observed)
        gates = set(observed) - {runner.current_user}
        self.assertEqual(len(gates), 4)
        for gate in gates:
            self.assertEqual(gate.__qualname__, "feature_gate.<locals>.check")
            self.assertEqual(gate.__module__, "app.api.ui_policies")
            self.assertIsNone(observed[gate]())
        self.assertFalse(set(observed) & set(runner.app.dependency_overrides))


if __name__ == "__main__":
    unittest.main()
