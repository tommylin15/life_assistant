"""Direct production Hosting handoff contract and rollback invariants."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
LEGACY = ROOT / ".github/workflows/v3-auto-production-hosting-after-release.yml"
HOSTING = ROOT / ".github/workflows/deploy-firebase-hosting.yml"


class AutoProductionHostingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.release = RELEASE.read_text()
        cls.hosting = HOSTING.read_text()
        cls.handoff_name = "Dispatch production Hosting after successful V3 gates"
        cls.handoff = cls.release.split("- name: " + cls.handoff_name, 1)[1]

    def test_no_recursive_workflow_run_and_permissions(self):
        self.assertFalse(LEGACY.exists())
        self.assertIn("actions: write", self.release)
        self.assertNotIn('workflows: ["V3 Release - GHCR to Cloud Run"]', self.release)

    def test_staging_only_cannot_dispatch(self):
        self.assertIn("inputs.promote && inputs.publish_staging && success()", self.handoff)
        for ident in ("staging_live", "promote_live", "live_acceptance",
                      "rollback_drill", "revision_retention", "curated_handoff"):
            with self.subTest(ident=ident):
                self.assertIn("id: " + ident, self.release)
                self.assertIn("steps." + ident + ".outcome == 'success'", self.handoff)
        for unsafe in ("--raw-field promote=true", "firebase deploy",
                       "gcloud run services update-traffic"):
            self.assertNotIn(unsafe, self.handoff)

    def test_after_all_production_live_gates(self):
        ordered = ("Promote exact Preview to independent fixed staging live and verify pinned routes",
                   "Reconfirm source SHA and live traffic, then promote",
                   "Post-promotion live health, PostgreSQL and access gates",
                   "Controlled rollback rehearsal and restore promoted live traffic",
                   "Retain latest 10 revisions after all live gates PASS",
                   "Pin curated handoff Job after verified production promotion",
                   self.handoff_name)
        indices = [self.release.index("- name: " + x) for x in ordered]
        self.assertEqual(indices, sorted(indices))
        self.assertIn("Restore original Cloud Run traffic on failed live gate", self.release)

    def test_sha_four_ci_live_digest_and_dedupe(self):
        for required in ('test "$(git rev-parse HEAD)" = "$RELEASE_SHA"',
                         'CURRENT_MAIN="$(gh api',
                         'if [[ "$CURRENT_MAIN" != "$RELEASE_SHA" ]]',
                         '.head_repository.full_name==$repo',
                         '.event=="workflow_dispatch"',
                         'select(.conclusion=="success")',
                         '.name=="backend"', '.name=="flutter"',
                         '.name=="deployment-scripts"', '.name=="free-events-postgres"',
                         'length==5', '.[0].revisionName==$rev', '.[0].percent==100',
                         'v3_image_identity.py --resource revision',
                         '--expected "$IMAGE_REF"',
                         'any(.workflow_runs[]; .head_sha==$sha)',
                         'production_hosting_dispatch=SKIP existing_run_for_sha',
                         'gh workflow run deploy-firebase-hosting.yml',
                         '--ref main',
                         'production_hosting_runtime=NOT_VERIFIED'):
            with self.subTest(required=required):
                self.assertIn(required, self.handoff)
        self.assertEqual(self.handoff.count("gh workflow run deploy-firebase-hosting.yml"), 1)

    def test_existing_hosting_readback_and_rollback_unchanged(self):
        h = self.hosting
        for marker in ('workflow_dispatch:',
                       'Guard same-SHA promoted backend and snapshot production Hosting',
                       'docker buildx imagetools inspect',
                       'v3_image_identity.py --resource revision',
                       'Capture exact published production Hosting version',
                       'Restore previous production Hosting on failed readback',
                       "steps.firebase_publish.outcome == 'success'",
                       '[["$CURRENT" != "$PUBLISHED" ]]',
                       '"$BASE/releases?versionName=$PREVIOUS"',
                       'test "$RESTORED" = "$PREVIOUS"'):
            with self.subTest(marker=marker):
                if marker.startswith("[["):
                    self.assertIn('[[ "$CURRENT" != "$PUBLISHED" ]]', h)
                else:
                    self.assertIn(marker, h)
        self.assertNotIn("workflow_run:", h)

    def test_shell_scripts_parse(self):
        sources = [(self.handoff, "Direct Hosting Dispatch")]
        for name in ("Guard same-SHA promoted backend and snapshot production Hosting",
                     "Capture exact published production Hosting version",
                     "Restore previous production Hosting on failed readback"):
            sources.append((self.hosting.split("      - name: " + name, 1)[1],
                            name))
        for source, name in sources:
            block = source.split("        run: |", 1)[1]
            result_lines = []
            for line in block.splitlines()[1:]:
                if line.startswith("      - name:"):
                    break
                if line.strip() and not line.startswith("          "):
                    break
                result_lines.append(line[10:] if line.startswith("          ") else "")
            result = subprocess.run(["bash", "-n"], input="\n".join(result_lines),
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, name + ": " + result.stderr)


if __name__ == "__main__":
    unittest.main()
