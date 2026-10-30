#!/usr/bin/env python3
"""Fail-closed live/curated-Job digest alignment for release and manual fallback.

Never starts a Job or mutates production; caller owns the authenticated gcloud operations.
"""
import argparse
import json
import sys

from v3_image_identity import verify

SHEET_ID = "1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4"
MODULE = "scripts.import_curated_from_sheet"


def validate_live(service, revision, expected_revision, expected_image, upstream_manifest=None):
    entries = service.get("status", {}).get("traffic", [])
    if not isinstance(entries, list):
        raise ValueError("missing live traffic")
    active = [e for e in entries if int(e.get("percent") or 0) > 0]
    if (len(active) != 1 or active[0].get("revisionName") != expected_revision
            or int(active[0].get("percent") or 0) != 100):
        raise ValueError("expected revision is not the sole production live revision")
    verify(revision, expected_image, "revision", upstream_manifest)
    return {"status": "PASS", "check": "live_digest"}


def validate_job(job, expected_image, upstream_manifest=None):
    verify(job, expected_image, "job", upstream_manifest)
    containers = (job.get("spec", {}).get("template", {}).get("spec", {})
                  .get("template", {}).get("spec", {}).get("containers", []))
    container = containers[0]  # verified exactly one container by verify()
    if container.get("command") != ["python"] or container.get("args") != ["-m", MODULE]:
        raise ValueError("curated import command or arguments differ")
    settings = container.get("env", [])
    if not isinstance(settings, list):
        raise ValueError("curated import env unavailable")
    actual = [e for e in settings if e.get("name") in {"LIFE_CURATED_SHEET_ID", "LIFE_CURATED_IMPORT_APPLY"}]
    if (len(actual) != 2 or
            {e.get("name"): e.get("value") for e in actual}
            != {"LIFE_CURATED_SHEET_ID": SHEET_ID, "LIFE_CURATED_IMPORT_APPLY": "1"}):
        raise ValueError("curated import Sheet ID or apply configuration differs")
    return {"status": "PASS", "check": "job_digest_and_contract"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["live", "job"], required=True)
    p.add_argument("--json", required=True)
    p.add_argument("--expected-image", required=True)
    p.add_argument("--revision-json")
    p.add_argument("--expected-revision")
    p.add_argument("--manifest-json", help="Manifest fetched from exact immutable GHCR digest")
    args = p.parse_args()
    try:
        with open(args.json, encoding="utf-8") as f:
            payload = json.load(f)
        upstream_manifest = None
        if args.manifest_json:
            with open(args.manifest_json, encoding="utf-8") as f:
                upstream_manifest = json.load(f)
        if args.mode == "live":
            if not args.revision_json or not args.expected_revision:
                raise ValueError("live check requires revision metadata")
            with open(args.revision_json, encoding="utf-8") as f:
                revision = json.load(f)
            result = validate_live(payload, revision, args.expected_revision, args.expected_image, upstream_manifest)
        else:
            result = validate_job(payload, args.expected_image, upstream_manifest)
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)[:180]}), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
