"""Cloud Run OAuth diagnostic smoke with fake gcloud; no Google/GCP access."""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/run_cloud_run_job_with_diagnostics.sh"


class CloudRunOAuthDiagnosticTests(unittest.TestCase):
    def _run(self, task_code, marker=True):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp, "gcloud")
            fake.write_text("""#!/bin/sh
case "$*" in
  *"jobs executions list"*) echo "synthetic-execution" ;;
  *"jobs executions tasks list"*) echo "synthetic-execution-task0" ;;
  *"jobs executions tasks describe"*)
    case "$*" in
      *"value(status.lastAttemptResult.exitCode)"*) echo "$FAKE_TASK_EXIT" ;;
      *) echo "status: synthetic task" ;;
    esac ;;
  *"logging read"*) echo "PERMISSION_DENIED: log viewer unavailable" >&2; exit 1 ;;
esac
""")
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            env = {**os.environ,
                   "PATH": tmp + os.pathsep + os.environ.get("PATH", ""),
                   "GCP_PROJECT_ID": "synthetic-project",
                   "GCP_REGION": "test-region",
                   "FAKE_TASK_EXIT": str(task_code),
                   "RUN_JOB_HEARTBEAT_SECONDS": "1",
                   "RUN_JOB_MAX_WAIT_SECONDS": "25",
                   "GITHUB_STEP_SUMMARY": str(Path(tmp, "step-summary"))}
            command = ["sh", "-c", "exit 1", "scripts.verify_staging_google_e2e" if marker else "unrelated_script"]
            result = subprocess.run(
                ["bash", str(SCRIPT), "life-assistant-core-acceptance", *command],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=18,
            )
            output = result.stdout + result.stderr
            summary = Path(tmp, "step-summary")
            return result.returncode, output, summary.read_text() if summary.exists() else ""

    def test_missing_owner_callback_is_visible_without_cloud_logging(self):
        code, log, summary = self._run(20)
        self.assertEqual(code, 1)
        self.assertIn("staging_oauth_e2e=NOT_VERIFIED reason=missing_owner_callback_session", log)
        self.assertIn("missing_owner_callback_session", summary)
        self.assertIn("PERMISSION_DENIED", log)

    def test_verifier_error_is_not_misclassified_as_missing_owner(self):
        code, log, summary = self._run(21)
        self.assertEqual(code, 1)
        self.assertIn("staging_oauth_e2e=FAIL reason=verifier_runtime_error", log)
        self.assertNotIn("missing_owner_callback_session", summary)

    def test_other_jobs_cannot_inherit_oauth_reason(self):
        code, log, summary = self._run(20, marker=False)
        self.assertEqual(code, 1)
        self.assertNotIn("staging_oauth_e2e=", log)
        self.assertNotIn("staging_oauth_e2e=", summary)


if __name__ == "__main__":
    unittest.main()
