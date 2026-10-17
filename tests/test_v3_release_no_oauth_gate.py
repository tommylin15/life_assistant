"""Owner-approved V3 release: automated OAuth checks remain; human sign-in is not gated."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
STAGE = ROOT / "scripts/v3_fixed_staging_release.sh"
ALT_STAGE = ROOT / ".github/workflows/v3-staging-live.yml"
HOSTING = ROOT / ".github/workflows/deploy-firebase-hosting.yml"

class ReleaseWithoutOAuthGate(unittest.TestCase):
    def test_no_interactive_owner_callback_session_gate(self):
        for path in (RELEASE, STAGE, ALT_STAGE, HOSTING):
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                for marker in ("scripts.verify_staging_google_e2e",
                               "staging_oauth_canary=ACTIVE", "staging_canary_next=",
                               "staging_e2e=true", 'PHASE="owner_google_auth"'):
                    self.assertNotIn(marker, content)

    def test_automated_google_oauth_checks_are_release_gates(self):
        release, stage, alt, hosting = (
            x.read_text(encoding="utf-8") for x in
            (RELEASE, STAGE, ALT_STAGE, HOSTING))
        self.assertIn("stage-oauth-preview-headers", release)
        self.assertIn("oauth:staging:", release)
        self.assertIn("DRIVE_ACCEPTANCE_GOOGLE_FILE_ID", release)
        self.assertIn("scripts.run_drive_google_integration_acceptance", release)
        self.assertIn("staging_google_redirect=PASS fixed_staging_callback", stage)
        self.assertIn("redirect_uri=https%3A%2F%2Flife-assistant-v3-stage-tl15.web.app", alt)
        self.assertIn("hosting_check=auth_redirect:PASS", hosting)

    def test_candidate_gate_retries_only_transient_and_keeps_security_checks(self):
        release = RELEASE.read_text(encoding="utf-8")
        candidate = release.split(
            "      - name: Candidate health, database readiness, auth and authorization", 1
        )[1].split("      - name: Pin migration job", 1)[0]
        for required in (
            "probe health /health 200",
            "probe ready /ready 200",
            "probe unauthorized /api/v1/tasks 401",
            "probe oauth /auth/login 307",
            "candidate_$label=FAIL http=$code",
            "candidate_$label=RETRY http=$code",
            "google_host_callback_or_state",
            'params.get("redirect_uri") == [expected]',
            'params.get("state", [""])[0]',
            'target.hostname == "accounts.google.com"',
        ):
            self.assertIn(required, candidate)
        # No bearer/cookie/OAuth token leaks; login headers are temp-only.
        self.assertNotIn('cat "$RUNNER_TEMP/v3-candidate-oauth.headers"', candidate)
        self.assertNotIn('echo "$location"', candidate)
        # 401/403 unauthorized failures must never be retried as transient.
        self.assertNotIn('"$code" == 401', candidate)
        self.assertNotIn('"$code" == 403', candidate)

    def test_candidate_sha_staging_401_rollback_and_production_hosting_still_gated(self):
        r, s, h = (f.read_text(encoding="utf-8") for f in
                   (RELEASE, STAGE, HOSTING))
        self.assertIn("inputs.promote && !inputs.publish_staging", r)
        self.assertIn("Production promotion requires publish_staging", r)
        self.assertIn("Verify pinned Preview API and static release", r)
        self.assertIn("Reconfirm source SHA and live traffic, then promote", r)
        self.assertIn("Post-promotion live health, PostgreSQL and access gates", r)
        self.assertIn("Controlled rollback rehearsal and restore promoted live traffic", r)
        self.assertIn("staging_live_readback=PASS layer=pins_and_api_401", s)
        self.assertIn("hosting_check=api_unauthenticated:PASS", h)
        self.assertIn("Promote exact Preview to independent fixed staging live and verify pinned routes", r)
        self.assertIn("Dispatch production Hosting after successful V3 gates", r)
        self.assertNotIn("verify owner OAuth", r.split("Dispatch production Hosting after successful V3 gates", 1)[1])

if __name__ == "__main__":
    unittest.main()
