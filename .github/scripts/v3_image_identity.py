#!/usr/bin/env python3
"""Verify immutable GHCR image identity after Cloud Run's managed cache import.

Cloud Run rewrites public external image names to cache.*.pkg.dev on readback.
This is valid only when BOTH the canonical upstream name and its digest match.
Reject missing readback, mutable tags and any arbitrary registry substitution.
"""
import argparse
import json
import re
import sys

GHCR_PATTERN = re.compile(
    r"^ghcr\.io/tommylin15/life_assistant-backend@sha256:[a-f0-9]{64}$"
)
CACHE_PATTERN = re.compile(r"^cache\.[a-z0-9-]+\.pkg\.dev/")


def canonical(image: str) -> str:
    if not isinstance(image, str):
        raise ValueError("image reference is missing")
    result = CACHE_PATTERN.sub("", image, count=1)
    if not GHCR_PATTERN.fullmatch(result):
        raise ValueError("not an approved, immutable GHCR digest")
    return result


def verify(payload: dict, expected: str, resource: str) -> dict:
    if resource not in {"revision", "job"}:
        raise ValueError("unsupported resource")
    if canonical(expected) != expected:
        raise ValueError("expected image must be the direct GHCR digest")
    if resource == "revision":
        containers = payload.get("spec", {}).get("containers")
    else:
        containers = (payload.get("spec", {}).get("template", {})
                      .get("spec", {}).get("template", {})
                      .get("spec", {}).get("containers"))
    if not isinstance(containers, list) or len(containers) != 1:
        raise ValueError("exactly one container identity is required")
    if canonical(containers[0].get("image")) != expected:
        raise ValueError("deployed container image differs from expected digest")
    if resource == "revision":
        if canonical(payload.get("status", {}).get("imageDigest")) != expected:
            raise ValueError("resolved revision image digest differs from expected")
        conditions = payload.get("status", {}).get("conditions", [])
        if not any(x.get("type") == "Ready" and x.get("status") == "True"
                   for x in conditions):
            raise ValueError("revision is not Ready")
    return {"status": "PASS", "resource": resource,
            "canonical_digest": expected, "container_count": 1}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource", choices=["revision", "job"], required=True)
    parser.add_argument("--json", required=True)
    parser.add_argument("--expected", required=True)
    args = parser.parse_args()
    try:
        with open(args.json, encoding="utf-8") as f:
            payload = json.load(f)
        result = verify(payload, args.expected, args.resource)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)[:180]}),
              file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
