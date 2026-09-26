from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class DeployCloudRunWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_batch_fast_forward_cannot_skip_backend_release(self):
        self.assertNotIn("git diff --quiet HEAD^ HEAD -- backend", self.text)
        self.assertNotIn("backend_changes.outputs.deploy", self.text)

    def test_runtime_migration_gate_runs_before_service_deploy(self):
        migration_marker = "Apply verified database migration"
        deploy_marker = "Deploy backend to Cloud Run"
        self.assertIn(migration_marker, self.text)
        self.assertIn("apply_cloud_domain_parity_migration.py", self.text)
        self.assertIn(deploy_marker, self.text)
        self.assertLess(self.text.index(migration_marker), self.text.index(deploy_marker))

    def test_failed_migration_surfaces_execution_and_logs_before_failing_gate(self):
        migration_marker = "Apply verified database migration"
        diagnostics_marker = "Collect failed migration diagnostics"
        fail_marker = "Fail migration gate"
        deploy_marker = "Deploy backend to Cloud Run"

        self.assertIn("id: migration", self.text)
        self.assertIn("continue-on-error: true", self.text)
        self.assertIn(diagnostics_marker, self.text)
        self.assertIn("steps.migration.outcome == 'failure'", self.text)
        self.assertIn("gcloud run jobs executions describe", self.text)
        self.assertIn("gcloud logging read", self.text)
        self.assertIn(fail_marker, self.text)
        self.assertLess(self.text.index(migration_marker), self.text.index(diagnostics_marker))
        self.assertLess(self.text.index(diagnostics_marker), self.text.index(fail_marker))
        self.assertLess(self.text.index(fail_marker), self.text.index(deploy_marker))

    def test_runtime_verification_remains_mandatory(self):
        self.assertIn("Verify Cloud Run health", self.text)
        self.assertIn("Verify Cloud Run database readiness", self.text)
        self.assertIn("Verify unauthenticated API is application-protected", self.text)


if __name__ == "__main__":
    unittest.main()
