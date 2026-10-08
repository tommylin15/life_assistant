"""Contract tests for V3 Cloud Run revision cleanup (no cloud credentials required)."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / ".github/scripts/v3_revision_retention.py"
spec = importlib.util.spec_from_file_location("v3_revision_retention", FILE)
ret = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ret)


def rev(i):
    return {"metadata": {"name": f"life-assistant-api-{i:05d}",
                         "creationTimestamp": f"2026-10-08T{i:02d}:00:00Z"}}


def svc(live=14, tagged=13):
    return {"status": {
        "latestReadyRevisionName": f"life-assistant-api-{14:05d}",
        "latestCreatedRevisionName": f"life-assistant-api-{14:05d}",
        "traffic": [
            {"revisionName": f"life-assistant-api-{live:05d}", "percent": 100},
            {"revisionName": f"life-assistant-api-{tagged:05d}",
             "percent": 0, "tag": "v3-candidate"},
        ]}}


class RevisionRetentionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [rev(i) for i in range(1, 15)]

    def test_keeps_latest_ten_only(self):
        result = ret.plan(svc(), self.rows, 10)
        self.assertEqual(result["delete"],
                         [f"life-assistant-api-{i:05d}" for i in range(4, 0, -1)])
        self.assertEqual(len(result["retain"]), 10)

    def test_tagged_old_revision_is_preserved(self):
        result = ret.plan(svc(tagged=2), self.rows, 10)
        self.assertNotIn("life-assistant-api-00002", result["delete"])
        self.assertEqual(len(result["retain"]), 11)

    def test_explicit_rollback_baseline_is_preserved(self):
        result = ret.plan(svc(), self.rows, 10,
                          ["life-assistant-api-00001"])
        self.assertNotIn("life-assistant-api-00001", result["delete"])

    def test_cannot_reduce_retention_below_ten(self):
        with self.assertRaises(ValueError):
            ret.plan(svc(), self.rows, 2)

    def test_missing_inventory_timestamp_fails_closed(self):
        rows = self.rows.copy()
        rows[0] = {"metadata": {"name": "life-assistant-api-00001"}}
        with self.assertRaises(ValueError):
            ret.plan(svc(), rows, 10)

    def test_unknown_protected_revision_fails_closed(self):
        with self.assertRaises(ValueError):
            ret.plan(svc(), self.rows, 10,
                     ["life-assistant-api-99999"])

    def test_apply_requires_live_acceptance(self):
        args = type("Args", (), dict(project="project", region="us-central1",
                    service="life-assistant-api", keep=10, apply=True,
                    live_passed=False, expected_live_revision="life-assistant-api-00014",
                    protect=[]))()
        with patch.object(ret, "service_state", return_value=svc()), \
             patch.object(ret, "revision_list", return_value=self.rows), \
             patch.object(ret.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "Live gate evidence"):
                ret.execute(args)
            run.assert_not_called()

    def test_dry_run_is_non_destructive(self):
        args = type("Args", (), dict(project="project", region="us-central1",
                    service="life-assistant-api", keep=10, apply=False,
                    live_passed=False, expected_live_revision="life-assistant-api-00014",
                    protect=[]))()
        with patch.object(ret, "service_state", return_value=svc()), \
             patch.object(ret, "revision_list", return_value=self.rows), \
             patch.object(ret.subprocess, "run") as run:
            result = ret.execute(args)
            self.assertEqual(result["mode"], "DRY_RUN")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
