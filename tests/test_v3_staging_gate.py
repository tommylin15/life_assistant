"""Offline fail-closed tests for exact Firebase version -> Cloud Run revision."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github" / "scripts"))
from v3_staging_gate import STAGE_SITE, pinned_routes, release_version, verify_snapshot

SHA = "a" * 40
REV = "life-assistant-api-00199-abc"
OLD = "life-assistant-api-00198-xyz"

def version(name, tag):
    return {
        "name": f"sites/{STAGE_SITE}/versions/{name}",
        "status": "FINALIZED",
        "config": {"rewrites": [
            {"glob": "/api/**", "run": {"serviceId": "life-assistant-api", "region": "us-central1", "tag": tag}},
            {"glob": "/auth/**", "run": {"serviceId": "life-assistant-api", "region": "us-central1", "tag": tag}},
            {"glob": "**", "path": "/index.html"},
        ]},
    }

def release(channel, ver):
    return {"releases": [{
        "name": f"sites/{STAGE_SITE}/channels/{channel}/releases/123",
        "releaseTime": "2026-10-09T12:00:00Z",
        "version": {"name": ver["name"]},
    }]}

def service():
    return {"status": {"traffic": [
        {"revisionName": REV, "tag": "fh-candidate", "percent": 0},
        {"revisionName": OLD, "tag": "fh-old", "percent": 100},
    ]}}

class StagingVersionGateTest(unittest.TestCase):
    def setUp(self):
        self.new = version("new", "fh-candidate")
        self.old = version("old", "fh-old")
        self.svc = service()

    def check(self, **kwargs):
        d = dict(preview_releases=release("v3-aaaaaaaaaa", self.new),
                 preview_version=self.new, stage_releases=release("live", self.old),
                 stage_version=self.old, cloud_run=self.svc,
                 expected_sha=SHA, candidate_revision=REV, preview_visible_sha=SHA)
        d.update(kwargs)
        return verify_snapshot(**d)

    def test_exact_release_and_both_pins_pass(self):
        result = self.check()
        self.assertEqual(result["candidate_routes"]["/api/**"]["revision"], REV)
        self.assertEqual(result["previous_live_version"], self.old["name"])

    def test_unsafe_absent_live_baseline_fails(self):
        with self.assertRaises(ValueError):
            self.check(stage_releases={"releases": []})

    def test_old_tag_missing_fails_closed(self):
        with self.assertRaises(ValueError):
            self.check(cloud_run={"status": {"traffic": [self.svc["status"]["traffic"][0]]}})

    def test_missing_auth_rewrite_fails(self):
        self.new["config"]["rewrites"].pop(1)
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.check()

    def test_api_auth_divergence_fails(self):
        self.new["config"]["rewrites"][1]["run"]["tag"] = "fh-old"
        with self.assertRaises(ValueError):
            self.check()

    def test_candidate_wrong_revision_fails(self):
        with self.assertRaises(ValueError):
            self.check(candidate_revision=OLD)

    def test_preview_wrong_sha_fails(self):
        with self.assertRaises(ValueError):
            self.check(preview_visible_sha="b" * 40)

    def test_cross_site_release_fails(self):
        d = release("live", self.old)
        d["releases"][0]["name"] = d["releases"][0]["name"].replace(STAGE_SITE, "gen-lang-client-0593591102")
        with self.assertRaises(ValueError):
            self.check(stage_releases=d)

    def test_unpinned_rewrite_fails(self):
        del self.new["config"]["rewrites"][0]["run"]["tag"]
        with self.assertRaises(ValueError):
            self.check()

    def test_nonfinal_version_fails(self):
        self.new["status"] = "CREATED"
        with self.assertRaises(ValueError):
            self.check()

    def test_duplicate_critical_rewrite_fails(self):
        self.new["config"]["rewrites"].append(self.new["config"]["rewrites"][0].copy())
        with self.assertRaises(ValueError):
            self.check()

    def test_release_version_selects_latest_timestamp(self):
        old = release("live", self.old)["releases"][0]
        fresh = release("live", self.new)["releases"][0]
        fresh["releaseTime"] = "2026-10-10T12:00:00Z"
        self.assertEqual(release_version({"releases": [old, fresh]}, STAGE_SITE, "live"), self.new["name"])

if __name__ == "__main__":
    unittest.main()
