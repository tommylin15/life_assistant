"""V3 Cloud Run GHCR immutable index / platform child identity contract."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / ".github/scripts/v3_image_identity.py"
spec = importlib.util.spec_from_file_location("v3_image_identity", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

INDEX_DIGEST = "sha256:" + "0" * 64
CHILD_DIGEST = "sha256:" + "1" * 64
BAD_DIGEST = "sha256:" + "2" * 64
REF = "ghcr.io/tommylin15/life_assistant-backend@" + INDEX_DIGEST
CHILD = "ghcr.io/tommylin15/life_assistant-backend@" + CHILD_DIGEST
BAD = "ghcr.io/tommylin15/life_assistant-backend@" + BAD_DIGEST
CACHED = "cache.us-docker.pkg.dev/" + REF
CACHED_CHILD = "cache.us-docker.pkg.dev/" + CHILD

INDEX = {
    "schemaVersion": 2,
    "mediaType": "application/vnd.oci.image.index.v1+json",
    "manifests": [
        {"mediaType": "application/vnd.oci.image.manifest.v1+json",
         "digest": CHILD_DIGEST,
         "platform": {"os": "linux", "architecture": "amd64"}},
        {"mediaType": "application/vnd.oci.image.manifest.v1+json",
         "digest": BAD_DIGEST,
         "platform": {"os": "unknown", "architecture": "unknown"}},
    ],
}


def revision(image=CACHED, resolved=CACHED, ready="True"):
    return {"spec": {"containers": [{"image": image}]},
            "status": {"imageDigest": resolved,
                       "conditions": [{"type": "Ready", "status": ready}]}}


class ImageIdentityContract(unittest.TestCase):
    def test_direct_registry(self):
        self.assertEqual(m.verify(revision(REF, REF), REF, "revision")["status"], "PASS")

    def test_gcp_cache_rewrite_for_direct_digest(self):
        self.assertEqual(m.verify(revision(), REF, "revision")["status"], "PASS")

    def test_index_with_proven_amd64_child_matches_cloud_run(self):
        result = m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision", INDEX)
        self.assertEqual(result["identity_match"], "verified_linux_amd64_child")
        self.assertEqual(result["verified_digest"], CHILD_DIGEST)

    def test_child_without_manifest_proof_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "not the pinned GHCR"):
            m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision")

    def test_unknown_child_fails_even_with_index_proof(self):
        with self.assertRaisesRegex(ValueError, "not the pinned GHCR"):
            m.verify(revision("cache.us-docker.pkg.dev/" + BAD,
                              "cache.us-docker.pkg.dev/" + BAD), REF, "revision", INDEX)

    def test_reject_container_and_resolved_mismatch(self):
        with self.assertRaisesRegex(ValueError, "resolved revision image differs"):
            m.verify(revision(CACHED_CHILD, CACHED), REF, "revision", INDEX)

    def test_reject_other_registry(self):
        with self.assertRaisesRegex(ValueError, "approved"):
            m.verify(revision(image="example.invalid/" + REF), REF, "revision", INDEX)

    def test_reject_mutable_tag(self):
        with self.assertRaises(ValueError):
            m.verify(revision(image=REF.replace("@" + INDEX_DIGEST, ":main")), REF, "revision")

    def test_reject_not_ready(self):
        with self.assertRaisesRegex(ValueError, "not Ready"):
            m.verify(revision(ready="False"), REF, "revision")

    def test_reject_missing_status_digest(self):
        with self.assertRaises(ValueError):
            m.verify(revision(resolved=None), REF, "revision")

    def test_job_nested_readback_amd64_child(self):
        payload = {"spec": {"template": {"spec": {"template": {"spec":
            {"containers": [{"image": CACHED_CHILD}]}}}}}}
        self.assertEqual(
            m.verify(payload, REF, "job", INDEX)["identity_match"],
            "verified_linux_amd64_child",
        )

    def test_reject_missing_job_container(self):
        with self.assertRaises(ValueError):
            m.verify({"spec": {}}, REF, "job", INDEX)

    def test_reject_duplicate_amd64_children(self):
        index = {**INDEX, "manifests": [INDEX["manifests"][0], INDEX["manifests"][0]]}
        with self.assertRaisesRegex(ValueError, "exactly one"):
            m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision", index)

    def test_reject_only_attestation_or_other_platform(self):
        index = {**INDEX, "manifests": [INDEX["manifests"][1]]}
        with self.assertRaisesRegex(ValueError, "exactly one"):
            m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision", index)

    def test_reject_invalid_child_digest(self):
        index = {**INDEX, "manifests": [{**INDEX["manifests"][0], "digest": "sha256:bad"}]}
        with self.assertRaisesRegex(ValueError, "immutable"):
            m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision", index)

    def test_reject_unsupported_index_format(self):
        index = {**INDEX, "mediaType": "application/example+json"}
        with self.assertRaisesRegex(ValueError, "unsupported"):
            m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision", index)

    def test_reject_wrong_manifest_type_attestation(self):
        index = {**INDEX, "manifests": [
            {**INDEX["manifests"][0], "mediaType": "application/example-attestation"}
        ]}
        with self.assertRaisesRegex(ValueError, "immutable"):
            m.verify(revision(CACHED_CHILD, CACHED_CHILD), REF, "revision", index)


if __name__ == "__main__":
    unittest.main()
