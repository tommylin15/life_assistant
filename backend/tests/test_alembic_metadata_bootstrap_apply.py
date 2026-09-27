from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / "backend" / "scripts" / "bootstrap_alembic_metadata.py"
RELEASE = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_release.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class MetadataBootstrapApplyContractTests(unittest.TestCase):
    def test_guarded_bootstrap_module_exists(self):
        self.assertTrue(
            BOOTSTRAP.is_file(),
            "guarded Alembic metadata bootstrap module must exist before release can write metadata",
        )

    def test_release_runner_uses_guarded_bootstrap(self):
        text = RELEASE.read_text(encoding="utf-8")
        self.assertIn("bootstrap_alembic_metadata", text)
        self.assertIn("run_bootstrap", text)

    def test_deploy_workflow_carries_revision_scoped_bootstrap_approval(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION: 20260926_0004",
            text,
        )
        self.assertIn(
            "ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION=$ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION",
            text,
        )


if __name__ == "__main__":
    unittest.main()
