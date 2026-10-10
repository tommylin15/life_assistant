"""Automatic V3 staging dispatch remains same-SHA, gated and production-isolated."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
AUTO = ROOT / ".github/workflows/v3-auto-staging-after-ci.yml"
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
CI = ROOT / ".github/workflows/ci.yml"


class AutoStagingAfterCIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = AUTO.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.source)
        cls.release = RELEASE.read_text(encoding="utf-8")

    def test_trigger_requires_main_ci_completion_not_push_or_manual_ci(self):
        event = self.workflow.get("on", self.workflow.get(True))
        self.assertEqual(event["workflow_run"]["workflows"], ["CI"])
        self.assertEqual(event["workflow_run"]["types"], ["completed"])
        self.assertEqual(event["workflow_run"]["branches"], ["main"])
        self.assertNotIn("push", event)
        gate = self.workflow["jobs"]["dispatch-staging"]["if"]
        for guard in (
            "workflow_run.conclusion == 'success'",
            "workflow_run.event == 'push'",
            "workflow_run.head_branch == 'main'",
            "workflow_run.head_repository.full_name == github.repository",
        ):
            self.assertIn(guard, gate)

    def test_four_exact_ci_jobs_and_stale_sha_are_mandatory(self):
        self.assertIn('RELEASE_SHA: ${{ github.event.workflow_run.head_sha }}', self.source)
        self.assertIn('CI_RUN_ID: ${{ github.event.workflow_run.id }}', self.source)
        for name in ("flutter", "backend", "deployment-scripts", "free-events-postgres"):
            self.assertIn(f'.name == "{name}"', self.source)
            self.assertIn(f"  {name}:", CI.read_text(encoding="utf-8"))
        self.assertIn('.conclusion == "success"', self.source)
        self.assertIn('MAIN_SHA" != "$RELEASE_SHA"', self.source)
        self.assertIn('commits/main', self.source)
        self.assertIn('auto_staging=SKIP', self.source)

    def test_dispatch_is_staging_only_and_deduplicated(self):
        self.assertEqual(self.workflow["permissions"]["actions"], "write")
        self.assertEqual(self.workflow["permissions"]["contents"], "read")
        self.assertIn("cancel-in-progress: false", self.source)
        self.assertIn('any(.workflow_runs[]; .head_sha == $sha)', self.source)
        self.assertIn("gh workflow run v3-release-ghcr.yml --ref main", self.source)
        self.assertIn("--raw-field promote=false", self.source)
        self.assertIn("--raw-field publish_staging=true", self.source)
        self.assertNotIn("gcloud run services update-traffic", self.source)
        self.assertNotIn("firebase deploy", self.source)
        self.assertNotIn("--raw-field promote=true", self.source)

    def test_real_preview_and_owner_oauth_gates_are_not_bypassed(self):
        self.assertIn("Verify pinned Preview API and static release", self.release)
        self.assertIn("stage-oauth-preview-headers", self.release)
        self.assertIn("Promote exact Preview to independent fixed staging live and verify owner OAuth", self.release)
        self.assertIn("bash scripts/v3_fixed_staging_release.sh", self.release)
        self.assertIn('if: ${{ inputs.promote }}', self.release)
        self.assertIn('if: ${{ inputs.publish_staging }}', self.release)
        self.assertIn("github.sha", self.release)


if __name__ == "__main__":
    unittest.main()
