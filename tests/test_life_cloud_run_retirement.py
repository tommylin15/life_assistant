"""Bounded revision-tag retirement candidate selection; no Google account needed."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / ".github" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sp = importlib.util.spec_from_file_location("life_cloud_run_retirement_apply",
                                            SCRIPTS / "life_cloud_run_retirement_apply.py")
mod = importlib.util.module_from_spec(sp)
sp.loader.exec_module(mod)


def revisions():
    return [{"metadata": {"name": f"life-assistant-api-{n:05d}",
                          "creationTimestamp": f"2026-10-{n:02d}T10:00:00Z"}}
            for n in range(1, 15)]


def service(live=14, oldtag="v3-123456789a", old_rev=2):
    return {"status": {"latestReadyRevisionName": "life-assistant-api-00014",
                       "latestCreatedRevisionName": "life-assistant-api-00014",
                       "traffic": [
                           {"revisionName": f"life-assistant-api-{live:05d}",
                            "percent": 100, "tag": "v3-aaaaaaaaaa"},
                           {"revisionName": f"life-assistant-api-{old_rev:05d}",
                            "percent": 0, "tag": oldtag}]}}


class LifeRetentionTests(unittest.TestCase):
    def test_only_old_zero_traffic_candidate_tags(self):
        result = mod.select(service(), revisions())
        self.assertEqual(result["before"], 14)
        self.assertEqual(len(result["old"]), 4)
        self.assertEqual(result["tags"], ["v3-123456789a"])
        self.assertEqual(result["live"], "life-assistant-api-00014")

    def test_concurrent_ready_switch_inside_newest_ten_aborts(self):
        original_service = service()
        baseline = mod.select(original_service, revisions())
        baseline["preserved_tags"] = {
            (n, tag) for n, tag, _ in mod.traffic_snapshot(original_service)
            if tag and n in baseline["newest"]
        }
        baseline["latest_ready"] = original_service["status"]["latestReadyRevisionName"]
        baseline["latest_created"] = original_service["status"]["latestCreatedRevisionName"]
        changed = service()
        changed["status"]["latestReadyRevisionName"] = "life-assistant-api-00013"
        with patch.object(mod, "service_state", return_value=changed):
            with self.assertRaisesRegex(ValueError, "Concurrent ready revision changed"):
                mod.verify_baseline(baseline, "gen-lang-client-0593591102", "us-central1")

    def test_active_old_revision_denied(self):
        with self.assertRaisesRegex(ValueError, "Live revision"):
            mod.select(service(live=2, old_rev=14), revisions())

    def test_unknown_tag_denied(self):
        with self.assertRaisesRegex(ValueError, "Unknown old tag"):
            mod.select(service(oldtag="custom-unknown"), revisions())

    def test_legacy_v2_tag_allowed_only_outside_latest_ten(self):
        self.assertEqual(mod.select(service(oldtag="v2-candidate"),
                                        revisions())["tags"], ["v2-candidate"])
        self.assertEqual(mod.select(service(oldtag="v3-123456789a", old_rev=13),
                                        revisions())["tags"], [])


if __name__ == "__main__":
    unittest.main()
