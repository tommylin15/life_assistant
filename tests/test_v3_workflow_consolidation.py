"""Check the retained release path; all external changes stay GCP-gated."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WF=ROOT/".github/workflows"


class ConsolidatedV3Tests(unittest.TestCase):
    def test_one_time_triggers_retired(self):
        for old in ("life-01-07-one-time-acceptance.yml",
                    "life-cloud-run-retirement-apply.yml",
                    "v3-initial-bootstrap.yml",
                    "v3-cutover-once-after-release.yml"):
            self.assertFalse((WF/old).exists(), old)

    def test_document_only_ci_does_not_release(self):
        stage=(WF/"v3-auto-staging-after-ci.yml").read_text()
        self.assertIn("docs_only_ci_passed",stage)
        self.assertIn("length<300",stage)
        self.assertIn("four_jobs=PASS",stage)
        self.assertIn("--raw-field promote=false",stage)

    def test_retention_inline_and_isolated(self):
        release=(WF/"v3-release-ghcr.yml").read_text()
        self.assertIn("Retire old Cloud Run revisions after successful V3 gates",release)
        self.assertIn("life_cloud_run_retirement_apply.py",release)
        self.assertIn("continue-on-error: true",release)
        self.assertIn("retirement=FAIL maintenance_only",release)
        self.assertNotIn("gh workflow run life-gemini",release)
        self.assertIn("Controlled rollback rehearsal and restore promoted live traffic",release)

    def test_standalone_job_dependent_gemini_smoke_retired(self):
        self.assertFalse((WF / "life-gemini-p0v-signed-smoke.yml").exists())
        release = (WF / "v3-release-ghcr.yml").read_text(encoding="utf-8")
        self.assertIn("gemini_signed_smoke=RETIRED", release)
        self.assertIn("candidate_http=PASS health,ready,401,oauth-redirect", release)

    def test_staging_preflight_404_retry_is_bounded_and_identifiable(self):
        script=(ROOT/"scripts/v3_fixed_staging_release.sh").read_text()
        self.assertIn("preview_channel_release_index", script)
        self.assertIn("staging_live_release_index", script)
        self.assertIn("baseline_staging_public_sha", script)
        self.assertIn("non_retryable=true", script)
        self.assertIn("attempt<=8", script)
        self.assertIn("staging_http=FAIL", script)
        self.assertIn("v3_staging_gate.py", script)
        self.assertIn('if [[ "$current" != "$expected" ]]', script)

    def test_no_redundant_flutter_navigation_test(self):
        ci=(WF/"ci.yml").read_text()
        self.assertIn("flutter test --no-pub --reporter expanded",ci)
        self.assertNotIn("flutter test --no-pub test/drive_navigation_test.dart",ci)


if __name__=="__main__":
    unittest.main()
