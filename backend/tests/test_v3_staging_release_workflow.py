"""Fixed staging is an explicit, separate, rollback-capable V3 release gate."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
SCRIPT = ROOT / "scripts/v3_fixed_staging_release.sh"


class FixedStagingWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = RELEASE.read_text(encoding="utf-8")
        cls.staging = SCRIPT.read_text(encoding="utf-8")

    def test_staging_promotion_is_separate_explicit_manual_boolean(self):
        self.assertIn("publish_staging:", self.release)
        self.assertIn("default: false", self.release)
        self.assertIn("inputs.promote && !inputs.publish_staging", self.release)
        self.assertIn('if: ${{ inputs.publish_staging }}', self.release)
        self.assertNotIn("firebase deploy --only hosting", self.staging)

    def test_migration_and_readback_precede_live_and_production_traffic(self):
        r = self.release
        order = [
            "Apply additive 0018 schema before staging or production cutover",
            "Read-only fixed staging preview and rollback baseline preflight",
            "Promote exact Preview to independent fixed staging live",
            "Reconfirm source SHA and live traffic, then promote",
        ]
        positions = [r.index(x) for x in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("inputs.promote || inputs.publish_staging", r)
        self.assertNotIn("life-assistant-core-acceptance", r)
        self.assertNotIn("life-assistant-postdeploy-acceptance", r)

    def test_staging_fails_closed_uses_exact_versions_and_restores_old_live(self):
        s = self.staging
        for required in (
            'life-assistant-v3-stage-tl15',
            'gcloud auth print-access-token',
            'v3_staging_gate.py',
            '--preflight-only',
            'release_version',
            'pinned_routes',
            'verify_live',
            'ATTEMPTED=1',
            'restore_stage',
            'hosting_post "$BASELINE"',
            'staging_rollback=FAIL',
            'staging_live_readback=PASS layer=pins_and_api_401',
            'snapshot_cloud',
            'protected_traffic',
            'staging_live=PASS',
        ):
            self.assertIn(required, s)
        self.assertNotIn('gcloud run services update-traffic', s)
        self.assertNotIn('firebase deploy', s)
        self.assertNotIn('firebase hosting:clone', s)
        # Acceptance Jobs are retired; staging must not depend on their env vars.
        self.assertNotIn('CORE_ACCEPTANCE_JOB', s)
        self.assertNotIn('POSTDEPLOY_ACCEPTANCE_JOB', s)

    def test_staging_has_no_owner_oauth_gate_but_requires_pinned_401_readback(self):
        self.assertNotIn("staging_oauth_canary", self.staging)
        self.assertNotIn("verify_staging_google_e2e", self.staging)
        self.assertIn("/auth/staging/login", self.staging)
        self.assertIn("staging_google_redirect=PASS fixed_staging_callback", self.staging)
        self.assertIn("staging_live_readback=PASS layer=pins_and_api_401", self.staging)
        self.assertIn("production_traffic_unchanged", self.staging)


if __name__ == "__main__":
    unittest.main()
