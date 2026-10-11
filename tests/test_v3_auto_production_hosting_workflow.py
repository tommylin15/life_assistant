"""Guard automated production Hosting dispatch against staging-only success."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / ".github/workflows/v3-auto-production-hosting-after-release.yml"
RELEASE = ROOT / ".github/workflows/v3-release-ghcr.yml"
HOSTING = ROOT / ".github/workflows/deploy-firebase-hosting.yml"


class AutoProductionHostingContractTests(unittest.TestCase):
    def test_only_completed_manual_promoted_v3_release_is_considered(self):
        content = DISPATCHER.read_text()
        self.assertIn('workflows: ["V3 Release - GHCR to Cloud Run"]', content)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", content)
        self.assertIn("github.event.workflow_run.event == 'workflow_dispatch'", content)
        self.assertIn(".head_repository.full_name == $repo", content)
        self.assertIn("MAIN_SHA", content)
        self.assertIn('[[ "$MAIN_SHA" != "$RELEASE_SHA" ]]', content)
        self.assertIn("actions: write", content)

    def test_every_production_gate_and_four_ci_jobs_required(self):
        content = DISPATCHER.read_text()
        release = RELEASE.read_text()
        for label in (
            "Promote exact Preview to independent fixed staging live and verify pinned routes",
            "Reconfirm source SHA and live traffic, then promote",
            "Post-promotion live health, PostgreSQL and access gates",
            "Controlled rollback rehearsal and restore promoted live traffic",
            "Retain latest 10 revisions after all live gates PASS",
            "Pin curated handoff Job after verified production promotion",
        ):
            with self.subTest(label=label):
                self.assertIn(label, content)
                self.assertIn("name: " + label, release)
        for label in ("flutter", "backend", "deployment-scripts", "free-events-postgres"):
            self.assertIn('.name == "' + label + '"', content)
        self.assertIn("all(.[];", content)
        self.assertIn("index($name)", content)

    def test_no_production_dispatch_from_regular_ci_or_staging(self):
        content = DISPATCHER.read_text()
        self.assertNotIn('workflows: ["CI"]', content)
        self.assertNotIn("--raw-field promote=true", content)
        self.assertNotIn("v3-release-ghcr.yml --ref", content)
        self.assertIn("any(.workflow_runs[]; .head_sha == $sha)", content)
        self.assertIn("deploy-firebase-hosting.yml --repo", content)
        self.assertIn('--ref main', content)
        self.assertIn('echo "dispatch=false" >> "$GITHUB_OUTPUT"', content)
        self.assertIn("steps.gate.outputs.dispatch == 'true'", content)
        self.assertIn("workflow_dispatch:", HOSTING.read_text())

    def test_hosting_readback_is_pinned_to_promoted_digest_and_rollback(self):
        hosting = HOSTING.read_text()
        self.assertIn("Guard same-SHA promoted backend and snapshot production Hosting", hosting)
        self.assertIn("test \"$(git rev-parse HEAD)\" = \"$RELEASE_SHA\"", hosting)
        self.assertIn("docker buildx imagetools inspect", hosting)
        self.assertIn("v3_image_identity.py --resource revision", hosting)
        self.assertIn("Capture exact published production Hosting version", hosting)
        self.assertIn("id: firebase_publish", hosting)
        self.assertIn("Restore previous production Hosting on failed readback", hosting)
        self.assertIn("steps.firebase_publish.outcome == 'success'", hosting)
        self.assertIn('[[ "$CURRENT" != "$PUBLISHED" ]]', hosting)
        self.assertIn('"$BASE/releases?versionName=$PREVIOUS"', hosting)
        self.assertIn('test "$RESTORED" = "$PREVIOUS"', hosting)

    def test_all_production_hosting_shell_steps_parse(self):
        hosting = HOSTING.read_text()
        for name in (
            "Guard same-SHA promoted backend and snapshot production Hosting",
            "Capture exact published production Hosting version",
            "Restore previous production Hosting on failed readback",
        ):
            with self.subTest(step=name):
                start = hosting.index("      - name: " + name)
                block = hosting[start:].split("        run: |", 1)[1]
                script = []
                for line in block.splitlines()[1:]:
                    if line.startswith("      - name:"):
                        break
                    if line.strip() and not line.startswith("          "):
                        break
                    script.append(line[10:] if line.startswith("          ") else "")
                result = subprocess.run(["bash", "-n"], input=chr(10).join(script),
                                        text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_workflow_shell_steps_parse(self):
        content = DISPATCHER.read_text()
        snippets = []
        for part in content.split("        run: |")[1:]:
            script = []
            for line in part.splitlines()[1:]:
                if line.startswith("      - name:"):
                    break
                if line.strip() and not line.startswith("          "):
                    break
                script.append(line[10:] if line.startswith("          ") else "")
            snippets.append("\n".join(script))
        self.assertEqual(len(snippets), 2)
        for snippet in snippets:
            with self.subTest(script=snippet[:80]):
                result = subprocess.run(["bash", "-n"], input=snippet, text=True,
                                        capture_output=True, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
