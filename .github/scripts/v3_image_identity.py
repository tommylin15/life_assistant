#!/usr/bin/env python3
"""Verify immutable GHCR identity across Cloud Run's external-image cache.

GHCR may publish an OCI/Docker image index and Cloud Run may serve its
linux/amd64 child manifest. The different hashes are safe ONLY when the child
is explicitly listed in the manifest inspected by immutable GHCR digest.
No comparison is bypassed and no mutable tags/foreign registries are allowed.
"""
import argparse
import json
import re
import sys

GHCR_PATTERN = re.compile(
    r"^ghcr\.io/tommylin15/life_assistant-backend@sha256:[a-f0-9]{64}$"
)
CACHE_PATTERN = re.compile(r"^cache\.[a-z0-9-]+\.pkg\.dev/")
DIGEST_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")
INDEX_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}
IMAGE_TYPES = {
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
}


def canonical(image: str) -> str:
    if not isinstance(image, str):
        raise ValueError("image reference is missing")
    result = CACHE_PATTERN.sub("", image, count=1)
    if not GHCR_PATTERN.fullmatch(result):
        raise ValueError("not an approved, immutable GHCR digest")
    return result


def permitted_images(expected: str, upstream_manifest: dict | None) -> set[str]:
    """Accept only the pinned parent index or its unique linux/amd64 child."""
    if canonical(expected) != expected:
        raise ValueError("expected image must be the direct GHCR digest")
    allowed = {expected}
    if upstream_manifest is None:
        return allowed
    if not isinstance(upstream_manifest, dict) or upstream_manifest.get("schemaVersion") != 2:
        raise ValueError("invalid upstream GHCR manifest")
    media_type = upstream_manifest.get("mediaType")
    if media_type in IMAGE_TYPES:
        # The pinned ref is already an image manifest, not an index.
        if "manifests" in upstream_manifest:
            raise ValueError("unexpected manifest children on image manifest")
        return allowed
    if media_type not in INDEX_TYPES:
        raise ValueError("unsupported upstream GHCR manifest format")
    entries = upstream_manifest.get("manifests")
    if not isinstance(entries, list) or not entries:
        raise ValueError("upstream GHCR image index is empty")
    matches = [
        entry for entry in entries
        if isinstance(entry, dict)
        and isinstance(entry.get("platform"), dict)
        and entry["platform"].get("os") == "linux"
        and entry["platform"].get("architecture") == "amd64"
        and not entry["platform"].get("variant")
    ]
    if len(matches) != 1:
        raise ValueError("GHCR index must have exactly one linux/amd64 image")
    child = matches[0]
    digest = child.get("digest")
    if child.get("mediaType") not in IMAGE_TYPES or not isinstance(digest, str) or not DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("GHCR linux/amd64 child is not an immutable image manifest")
    allowed.add(expected.split("@", 1)[0] + "@" + digest)
    return allowed


def verify(payload: dict, expected: str, resource: str,
           upstream_manifest: dict | None = None) -> dict:
    if resource not in {"revision", "job"}:
        raise ValueError("unsupported resource")
    allowed = permitted_images(expected, upstream_manifest)
    if resource == "revision":
        containers = payload.get("spec", {}).get("containers")
    else:
        containers = (payload.get("spec", {}).get("template", {})
                      .get("spec", {}).get("template", {})
                      .get("spec", {}).get("containers"))
    if not isinstance(containers, list) or len(containers) != 1:
        raise ValueError("exactly one container identity is required")
    actual = canonical(containers[0].get("image"))
    if actual not in allowed:
        raise ValueError("deployed container image is not the pinned GHCR index or linux/amd64 child")
    if resource == "revision":
        resolved = canonical(payload.get("status", {}).get("imageDigest"))
        if resolved != actual:
            raise ValueError("resolved revision image differs from deployed container image")
        conditions = payload.get("status", {}).get("conditions", [])
        if not any(x.get("type") == "Ready" and x.get("status") == "True"
                   for x in conditions):
            raise ValueError("revision is not Ready")
    return {
        "status": "PASS",
        "resource": resource,
        "upstream_digest": expected.split("@", 1)[1],
        "verified_digest": actual.split("@", 1)[1],
        "identity_match": "upstream_index" if actual == expected else "verified_linux_amd64_child",
        "container_count": 1,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource", choices=["revision", "job"], required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument(
        "--manifest-json", help="Manifest fetched from exact immutable GHCR digest")
    args = parser.parse_args()
    try:
        with open(args.json, encoding="utf-8") as f:
            payload = json.load(f)
        upstream_manifest = None
        if args.manifest_json:
            with open(args.manifest_json, encoding="utf-8") as f:
                upstream_manifest = json.load(f)
        result = verify(payload, args.expected, args.resource, upstream_manifest)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)[:200]}),
              file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
