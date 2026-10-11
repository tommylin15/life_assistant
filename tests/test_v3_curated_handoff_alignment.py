"""The curated handoff Job follows *promoted* production, not the daily cron."""
import copy
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
from v3_curated_handoff_alignment import validate_live, validate_job, SHEET_ID


IMAGE = "ghcr.io/tommylin15/life_assistant-backend@sha256:" + "f" * 64
REV = "life-assistant-api-00200-test"


def service():
    return {"status": {"traffic": [{"revisionName": REV, "percent": 100}]}}


def revision():
    return {"spec": {"containers": [{"image": IMAGE}]},
            "status": {"imageDigest": IMAGE, "conditions": [{"type": "Ready", "status": "True"}]}}


def job():
    return {"spec": {"template": {"spec": {"template": {"spec": {"containers": [{
        "image": IMAGE,
        "command": ["python"],
        "args": ["-m", "scripts.import_curated_from_sheet"],
        "env": [{"name": "LIFE_CURATED_SHEET_ID", "value": SHEET_ID},
                {"name": "LIFE_CURATED_IMPORT_APPLY", "value": "1"}]
    }]}}}}}}


class CuratedAlignmentTests(unittest.TestCase):
    def test_verified_live_revision(self):
        self.assertEqual(validate_live(service(), revision(), REV, IMAGE)["status"], "PASS")

    def test_split_traffic_or_wrong_revision_rejected(self):
        split = service()
        split["status"]["traffic"] = [{"revisionName": REV, "percent": 60},
                                      {"revisionName": "other", "percent": 40}]
        with self.assertRaises(ValueError):
            validate_live(split, revision(), REV, IMAGE)
        with self.assertRaises(ValueError):
            validate_live(service(), revision(), "wrong", IMAGE)

    def test_revision_unready_or_wrong_digest_rejected(self):
        wrong = revision()
        wrong["status"]["imageDigest"] = IMAGE.replace("f" * 64, "a" * 64)
        with self.assertRaises(ValueError):
            validate_live(service(), wrong, REV, IMAGE)
        unready = revision()
        unready["status"]["conditions"] = [{"type": "Ready", "status": "False"}]
        with self.assertRaises(ValueError):
            validate_live(service(), unready, REV, IMAGE)

    def test_curated_job_identity_and_contract(self):
        self.assertEqual(validate_job(job(), IMAGE)["status"], "PASS")

    def test_unsafe_job_configuration_rejected(self):
        for edit in ("image", "command", "args", "sheet", "apply", "duplicates"):
            payload = job()
            c = payload["spec"]["template"]["spec"]["template"]["spec"]["containers"][0]
            if edit == "image":
                c["image"] = "ghcr.io/other/image:latest"
            if edit == "command":
                c["command"] = ["bash"]
            if edit == "args":
                c["args"] = ["-m", "scripts.run_free_events_moc_batch"]
            if edit == "sheet":
                c["env"][0]["value"] = "other"
            if edit == "apply":
                c["env"][1]["value"] = "0"
            if edit == "duplicates":
                c["env"].append(copy.copy(c["env"][0]))
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                validate_job(payload, IMAGE)

    def test_old_cron_off_and_release_owns_update(self):
        daily = (ROOT / ".github" / "workflows" / "curated-handoff-daily.yml").read_text()
        release = (ROOT / ".github" / "workflows" / "v3-release-ghcr.yml").read_text()
        self.assertIn("workflow_dispatch:", daily)
        self.assertNotIn("schedule:", daily)
        self.assertNotIn("gcloud run jobs update", daily)
        self.assertIn("--mode job", daily)
        self.assertIn("gcloud run jobs update", release)
        self.assertIn("Pin curated handoff Job after verified production promotion", release)
        self.assertGreater(release.index("Pin curated handoff Job after verified production promotion"),
                           release.index("Retain latest 10 revisions after all live gates PASS"))
        self.assertIn("if: ${{ inputs.promote && success() }}", release)


if __name__ == "__main__":
    unittest.main()
