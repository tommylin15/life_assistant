"""Owner-approved V3 release change: no manual/automatic OAuth acceptance gate."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
STAGE = ROOT / "scripts/v3_fixed_staging_release.sh"
ALT_STAGE = ROOT / ".github/workflows/v3-staging-live.yml"
HOSTING = ROOT / ".github/workflows/deploy-firebase-hosting.yml"
DISPATCH = ROOT / ".github/workflows/v3-auto-production-hosting-after-release.yml"

class ReleaseWithoutOAuthGate(unittest.TestCase):
    def test_no_oauth_login_or_callback_validation_in_release_workflows(self):
        for path in (RELEASE, STAGE, ALT_STAGE, HOSTING):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for forbidden in (
                    "verify_staging_google_e2e", "staging_oauth_canary=ACTIVE",
                    "staging_e2e=true", "run_drive_google_integration_acceptance",
                    "/auth/login", "/auth/staging/login", "oauth-redirect",
                    "oauth=PASS",
                ):
                    self.assertNotIn(forbidden, text)

    def test_candidate_sha_staging_401_rollback_and_production_hosting_still_gated(self):
        r, s, h, d = (f.read_text(encoding="utf-8") for f in
                      (RELEASE, STAGE, HOSTING, DISPATCH))
        self.assertIn("inputs.promote && !inputs.publish_staging", r)
        self.assertIn("Production promotion requires publish_staging", r)
        self.assertIn("Verify pinned Preview API and static release", r)
        self.assertIn("Reconfirm source SHA and live traffic, then promote", r)
        self.assertIn("Post-promotion live health, PostgreSQL and access gates", r)
        self.assertIn("Controlled rollback rehearsal and restore promoted live traffic", r)
        self.assertIn("staging_live_readback=PASS layer=pins_and_api_401", s)
        self.assertIn("hosting_check=api_unauthenticated:PASS", h)
        self.assertIn("Promote exact Preview to independent fixed staging live and verify pinned routes", d)
        self.assertNotIn("verify owner OAuth", d)

if __name__ == "__main__":
    unittest.main()
