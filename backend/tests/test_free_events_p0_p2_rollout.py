"""P0-P2 one-shot orchestrates audited V3 and protects MoC job settings."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/free-events-activation-once.yml"


class FreeEventsP0P2RolloutTests(unittest.TestCase):
    def test_only_one_time_push_with_four_ci_and_v3_gates(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        data = yaml.safe_load(source)
        self.assertIn("jobs", data)
        self.assertIn(".github/workflows/free-events-activation-once.yml", source)
        self.assertIn("github.event_name == 'push'", source)
        self.assertIn("check-runs?per_page=100", source)
        self.assertIn('if [ "$PASSED" -eq 4 ]', source)
        self.assertIn("gh workflow run v3-release-ghcr.yml", source)
        self.assertIn("promote=true", source)
        self.assertIn("moc_job_immutable_live_image=PASS", source)
        self.assertIn("gh workflow run free-events-moc-observations.yml", source)
        self.assertIn("p0_production_owner_authenticated_db_counts=NOT_VERIFIED", source)
        for forbidden in (
            "gcloud builds submit", "gcloud run jobs replace",
            "gh workflow run deploy-firebase-hosting.yml",
            "gcloud iam ", "gcloud run jobs delete",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
