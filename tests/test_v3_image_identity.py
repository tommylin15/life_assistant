"""V3 Cloud Run public GHCR cache/digest identity contract."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / ".github/scripts/v3_image_identity.py"
spec = importlib.util.spec_from_file_location("v3_image_identity", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
DIGEST = "sha256:" + "0" * 64
REF = "ghcr.io/tommylin15/life_assistant-backend@" + DIGEST
CACHED = "cache.us-docker.pkg.dev/" + REF


def revision(image=CACHED, resolved=CACHED, ready="True"):
    return {"spec": {"containers": [{"image": image}]},
            "status": {"imageDigest": resolved,
                       "conditions": [{"type": "Ready", "status": ready}]}}


class ImageIdentityContract(unittest.TestCase):
    def test_direct_registry(self):
        self.assertEqual(m.verify(revision(REF, REF), REF, "revision")["status"],
                         "PASS")

    def test_real_gcp_managed_cache_rewrite(self):
        self.assertEqual(m.verify(revision(), REF, "revision")["status"], "PASS")

    def test_reject_other_digest(self):
        with self.assertRaisesRegex(ValueError, "differs"):
            m.verify(revision(resolved=CACHED[:-1] + "1"), REF, "revision")

    def test_reject_other_registry(self):
        with self.assertRaisesRegex(ValueError, "approved"):
            m.verify(revision(image="example.invalid/" + REF), REF, "revision")

    def test_reject_mutable_tag(self):
        with self.assertRaises(ValueError):
            m.verify(revision(image=REF.replace("@"+DIGEST, ":main")), REF,
                     "revision")

    def test_reject_not_ready(self):
        with self.assertRaisesRegex(ValueError, "not Ready"):
            m.verify(revision(ready="False"), REF, "revision")

    def test_reject_missing_status_digest(self):
        with self.assertRaises(ValueError):
            m.verify(revision(resolved=None), REF, "revision")

    def test_job_nested_readback(self):
        payload = {"spec": {"template": {"spec": {"template": {"spec":
            {"containers": [{"image": CACHED}]}}}}}}
        self.assertEqual(m.verify(payload, REF, "job")["status"], "PASS")

    def test_reject_missing_job_container(self):
        with self.assertRaises(ValueError):
            m.verify({"spec": {}}, REF, "job")


if __name__ == "__main__":
    unittest.main()
