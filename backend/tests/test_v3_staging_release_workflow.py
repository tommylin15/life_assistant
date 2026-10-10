"""Fixed staging is an explicit, separate, rollback-capable V3 release gate."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
SCRIPT = ROOT / "scripts/v3_fixed_staging_release.sh"
AUTH_GATE = ROOT / "backend/scripts/verify_staging_google_e2e.py"


class FixedStagingWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = RELEASE.read_text(encoding="utf-8")
        cls.staging = SCRIPT.read_text(encoding="utf-8")
        cls.oauth = AUTH_GATE.read_text(encoding="utf-8")

    def test_staging_promotion_is_separate_explicit_manual_boolean(self):
        self.assertIn("publish_staging:", self.release)
        self.assertIn("default: false", self.release)
        self.assertIn("inputs.promote && !inputs.publish_staging", self.release)
        self.assertIn('if: ${{ inputs.publish_staging }}', self.release)
        self.assertNotIn("firebase deploy --only hosting", self.staging)

    def test_migration_and_readback_precede_live_and_production_traffic(self):
        r = self.release
        order = [
            "Read-only fixed staging preview and rollback baseline preflight",
            "Apply additive 0015 schema before production cutover",
            "Rollback-only curated pool migration and personal UI runtime acceptance",
            "Promote exact Preview to independent fixed staging live",
            "Reconfirm source SHA and live traffic, then promote",
        ]
        positions = [r.index(x) for x in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("inputs.promote || inputs.publish_staging", r)

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
            'staging_google_e2e',
            'snapshot_cloud',
            'protected_traffic',
            'staging_live=PASS',
        ):
            self.assertIn(required, s)
        self.assertNotIn('gcloud run services update-traffic', s)
        self.assertNotIn('firebase deploy', s)
        self.assertNotIn('firebase hosting:clone', s)

    def test_staging_oauth_canary_takes_real_revision_and_time_arguments(self):
        self.assertIn("EXPECTED_REVISION, CANARY_START_UTC = sys.argv[1:]", self.oauth)
        self.assertIn("count(DISTINCT action_type)=2", self.oauth)
        self.assertIn("staging_google_callback", self.oauth)
        self.assertIn("staging_google_session", self.oauth)


if __name__ == "__main__":
    unittest.main()
