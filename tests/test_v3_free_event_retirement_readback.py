import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github/scripts"))
from v3_free_event_retirement_readback import assess


class LegacyFreeEventsSchedulerAssessmentTests(unittest.TestCase):
    def test_paused_matching_and_unrelated_enabled_are_safe(self):
        result = assess([
            {"name": "projects/p/locations/us-central1/jobs/life-assistant-free-events-daily", "state": "PAUSED"},
            {"name": "projects/p/locations/us-central1/jobs/unrelated", "state": "ENABLED"},
        ])
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["matching_scheduler_jobs"]), 1)

    def test_enabled_scheduler_targeting_obsolete_job_is_failure(self):
        result = assess([{
            "name": "projects/p/locations/us-central1/jobs/legacy-scan",
            "state": "ENABLED",
            "httpTarget": {"uri": "https://run.googleapis.com/v2/projects/p/locations/us-central1/jobs/life-assistant-free-events:run"},
        }])
        self.assertEqual(result["status"], "FAIL")

    def test_unknown_scheduler_state_cannot_be_called_disabled(self):
        result = assess([{
            "name": "projects/p/locations/us-central1/jobs/life-assistant-free-events",
            "state": "UPDATE_FAILED",
        }])
        self.assertEqual(result["status"], "NOT_VERIFIED")

    def test_no_matching_jobs_is_only_scoped_negative(self):
        result = assess([{"name": "projects/p/locations/us-central1/jobs/other", "state": "ENABLED"}])
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["matching_scheduler_jobs"])


if __name__ == "__main__":
    unittest.main()
