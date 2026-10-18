from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "run_google_failure_acceptance.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class GoogleFailureRuntimeAcceptanceContractTests(unittest.TestCase):
    def test_runtime_acceptance_script_exists_and_compiles(self):
        self.assertTrue(
            SCRIPT.is_file(),
            "dev-test Google failure acceptance runner must exist",
        )
        source = SCRIPT.read_text(encoding="utf-8")
        compile(source, str(SCRIPT), "exec")

    def test_runner_covers_failure_partial_success_activity_and_cleanup(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "/api/v1/integrations/google/calendar/events",
            "/api/v1/integrations/google/gmail/messages/",
            "/api/v1/integrations/google/drive/bridge",
            "/api/v1/activity?limit=100",
            '"failure"',
            '"partial_success"',
            '"http_503"',
            "gmail_failure_no_internal_write",
            "google_failure_cleanup",
            "app.dependency_overrides[current_user]",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_google_failure_runner_no_longer_blocks_deploy(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("CORE_ACCEPTANCE_JOB", workflow)
        self.assertNotIn("Run Google provider failure-path runtime acceptance", workflow)
        self.assertNotIn("--args=-m,scripts.run_google_failure_acceptance", workflow)
        self.assertIn("Verify unauthenticated API is application-protected", workflow)


if __name__ == "__main__":
    unittest.main()
