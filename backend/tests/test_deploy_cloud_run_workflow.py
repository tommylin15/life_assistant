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

    def test_runtime_verification_remains_mandatory(self):
        self.assertIn("Verify Cloud Run health", self.text)
        self.assertIn("Verify Cloud Run database readiness", self.text)
        self.assertIn("Verify unauthenticated API is application-protected", self.text)


if __name__ == "__main__":
    unittest.main()
