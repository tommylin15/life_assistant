from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

RETIRED_NAMES = (
    "life-assistant-core-acceptance",
    "life-assistant-postdeploy-acceptance",
)
RETIRED_WORKFLOWS = (
    "_reusable-acceptance.yml",
    "postdeploy-runtime-acceptance.yml",
    "calendar-true-account-acceptance.yml",
    "life-gemini-p0v-signed-smoke.yml",
)

class CloudRunJobTopologyTests(unittest.TestCase):
    def test_retired_jobs_have_no_active_workflow_consumers(self):
        for path in WORKFLOWS.glob("*.yml"):
            if path.name == "retire-life-acceptance-jobs-once.yml":
                continue
            text = path.read_text(encoding="utf-8")
            for name in RETIRED_NAMES:
                with self.subTest(path=path.name, job=name):
                    self.assertNotIn(name, text)

    def test_legacy_standalone_workflows_are_absent(self):
        for name in RETIRED_WORKFLOWS:
            self.assertFalse((WORKFLOWS / name).exists(), name)

    def test_real_migration_and_non_job_release_gates_remain(self):
        legacy = (WORKFLOWS / "deploy-cloud-run.yml").read_text(encoding="utf-8")
        v3 = (WORKFLOWS / "v3-release-ghcr.yml").read_text(encoding="utf-8")
        self.assertIn("MIGRATION_JOB: life-assistant-db-migrate", legacy)
        self.assertIn("Apply verified database migration", legacy)
        self.assertIn("Apply additive 0018 schema", v3)
        self.assertIn("Verify unauthenticated API is application-protected", legacy)
        self.assertIn("Controlled rollback rehearsal and restore promoted live traffic", v3)
        self.assertIn("Post-promotion live health, PostgreSQL and access gates", v3)
        self.assertNotIn("Run real database/auth acceptance using release digest", v3)

    def test_only_one_scoped_retirement_workflow_deletes_jobs(self):
        cleanup = "retire-life-acceptance-jobs-once.yml"
        for path in WORKFLOWS.glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            if path.name == cleanup:
                self.assertIn("gcloud run jobs delete", text)
                for name in RETIRED_NAMES:
                    self.assertIn(name, text)
                self.assertIn("life-assistant-db-migrate", text)
            else:
                self.assertNotIn("gcloud run jobs delete", text)

if __name__ == "__main__":
    unittest.main()
