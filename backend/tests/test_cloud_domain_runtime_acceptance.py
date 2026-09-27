from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "run_cloud_domain_parity_acceptance.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class CloudDomainRuntimeAcceptanceContractTests(unittest.TestCase):
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

    def test_deploy_workflow_runs_acceptance_after_runtime_health(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("ACCEPTANCE_JOB: life-assistant-cloud-domain-acceptance", workflow)
        self.assertIn("Run authenticated cloud-domain acceptance", workflow)
        self.assertIn("--args=-m,scripts.run_cloud_domain_parity_acceptance", workflow)
        self.assertIn("--image \"$SERVICE_IMAGE\"", workflow)
        self.assertLess(
            workflow.index("Verify unauthenticated API is application-protected"),
            workflow.index("Run authenticated cloud-domain acceptance"),
        )


if __name__ == "__main__":
    unittest.main()
