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
        self.assertIn("release", data["jobs"])
        self.assertNotIn("push:", source)

    def test_cutover_requires_successful_promoted_and_rolled_back_release(self):
        source, _ = load("v3-cutover-disable-triggers.yml")
        for step in ("Post-promotion live health", "Controlled rollback rehearsal",
                     "Retain latest 10 revisions", "conclusion==\"success\"",
                     "updateMask=disabled", "disabled==true"):
            self.assertIn(step, source)
        self.assertNotIn("gcloud builds triggers delete", source)

    def test_one_time_bootstrap_cannot_trigger_on_every_push(self):
        source, data = load("v3-initial-bootstrap.yml")
        self.assertIn(".github/workflows/v3-initial-bootstrap.yml",
                      str(data.get(True, data.get("on"))))
        self.assertIn("gh workflow run v3-release-ghcr.yml", source)


if __name__ == "__main__":
    unittest.main()
