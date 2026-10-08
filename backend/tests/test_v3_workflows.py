"""Static V3 CI/CD safety contracts: parse real YAML, prohibit legacy writes."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
WF = ROOT / ".github/workflows"


def load(name):
    source = (WF / name).read_text(encoding="utf-8")
    return source, yaml.safe_load(source)


class V3PipelineContractTests(unittest.TestCase):
    def test_every_v3_workflow_is_valid_yaml(self):
        for path in sorted(WF.glob("v3-*.yml")):
            with self.subTest(path=path.name):
                obj = yaml.safe_load(path.read_text())
                self.assertIsInstance(obj, dict)
                self.assertIn("jobs", obj)

    def test_full_main_push_ci_is_enabled(self):
        source, jobs = load("ci.yml")
        self.assertNotIn("github.event_name != 'push'", source)
        self.assertIn("push", source)
        for name in ("flutter", "backend", "deployment-scripts"):
            self.assertIn(name, jobs["jobs"])

    def test_new_workflows_never_use_cloud_build_or_gcs_ar_write(self):
        for path in sorted(WF.glob("v3-*.yml")):
            source = path.read_text().lower()
            with self.subTest(path=path.name):
                self.assertNotIn("gcloud builds submit", source)
                self.assertNotIn("gcloud builds triggers run", source)
                self.assertNotIn("gcloud storage rm", source)
                self.assertNotIn("gcloud artifacts repositories delete", source)
                self.assertNotIn("gcloud artifacts docker images delete", source)

    def test_candidate_is_digest_pinned_and_no_traffic(self):
        source, data = load("v3-release-ghcr.yml")
        for item in ("workflow_dispatch:", "--no-traffic", "--tag",
                     "docker manifest inspect", "pinTag", "CANDIDATE_REVISION",
                     "Post-promotion live health",
                     "Controlled rollback rehearsal",
                     "v3_revision_retention.py",
                     "--keep 10", "--apply --live-passed",
                     "Restore original Cloud Run traffic"):
            self.assertIn(item, source)
        self.assertIn("aquasecurity/trivy-action@v0.36.0", source)
        self.assertIn("release", data["jobs"])
        self.assertNotIn("push:", source)

    def test_drive_ai_consent_acceptance_precedes_promotion(self):
        source, _ = load("v3-release-ghcr.yml")
        preflight = source.index("      - name: Pre-promotion Drive AI consent runtime acceptance")
        promote = source.index("      - name: Reconfirm source SHA and live traffic, then promote")
        self.assertLess(preflight, promote)
        self.assertIn("scripts.run_drive_ai_enrichment_acceptance", source[preflight:promote])
        self.assertIn('--image "$IMAGE_REF"', source[preflight:promote])
        self.assertIn('if: ${{ inputs.promote }}', source[preflight:promote])

    def test_staging_hosting_isolated_from_live_rewrites(self):
        for filename in ("v3-release-ghcr.yml",
                         "v3-firebase-preview-probe.yml"):
            source, _ = load(filename)
            with self.subTest(workflow=filename):
                self.assertIn("life-assistant-v3-stage-tl15", source)
                self.assertIn('cfg["hosting"]["site"]', source)
                self.assertIn("--no-authorized-domains", source)
                self.assertIn('test "$STAGING_HOSTING_SITE" != "$GCP_PROJECT_ID"', source)
                self.assertNotIn("firebase deploy --only hosting", source)
        config = (ROOT / "firebase.json").read_text()
        self.assertNotIn('"pinTag": true', config)
        self.assertNotIn('"site": "life-assistant-v3-stage-tl15"', config)

    def test_cutover_requires_successful_promoted_and_rolled_back_release(self):
        source, _ = load("v3-cutover-disable-triggers.yml")
        for step in ("Post-promotion live health", "Controlled rollback rehearsal",
                     "Retain latest 10 revisions", "conclusion==\"success\"",
                     "updateMask=disabled", "disabled==true"):
            self.assertIn(step, source)
        self.assertNotIn("gcloud builds triggers delete", source)

    def test_cutover_requires_exact_serving_revision_and_ten_retained(self):
        source, _ = load("v3-cutover-disable-triggers.yml")
        for requirement in (
            "VERIFIED_RELEASE_SHA",
            "LIVE_REVISION",
            "EXPECTED_TAG",
            "gcloud run revisions describe",
            "v3_image_identity.py",
            "--resource revision",
            'test "$REV_COUNT" -le 10',
        ):
            self.assertIn(requirement, source)
        self.assertNotIn("value(spec.template.spec.containers[0].image)", source)

    def test_one_time_bootstrap_cannot_trigger_on_every_push(self):
        source, data = load("v3-initial-bootstrap.yml")
        self.assertIn(".github/workflows/v3-initial-bootstrap.yml",
                      str(data.get(True, data.get("on"))))
        self.assertIn("gh workflow run v3-release-ghcr.yml", source)


if __name__ == "__main__":
    unittest.main()
