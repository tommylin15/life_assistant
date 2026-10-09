#!/usr/bin/env python3
"""One-time bounded cleanup of retired Cloud Build source objects.

Approved Oct 9, 2026: remove 77 source/ objects from the TWO exact buckets.
Never delete bucket, other object prefix, application or database backup.
Do not modify any other GCS resources. Fail closed on unexpected drift.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import v3_gcs_object_inventory as src

PROJECT = "gen-lang-client-0593591102"
BUCKETS = {
    "gen-lang-client-0593591102-cloudbuild-regional": (188, 57, 131),
    "gen-lang-client-0593591102_cloudbuild": (20, 20, 0),
}
TRIGGERS = {
    "janus-dev-v2",
    "life-assistant-v2-main",
    "life-assistant-v2-release",
    "omniagent-main-v2",
    "omniagent-release-v2",
}
BLOCKED = (
    "backup", "database", "postgres", "pg_dump", "snapshot",
    "ledger", "private", "users", "secrets", "credential", "storage", "uploads",
)


def trigger_guard():
    p = subprocess.run(
        ["gcloud", "builds", "triggers", "list", "--project", PROJECT,
         "--region", "us-central1", "--format=json"],
        text=True, capture_output=True, check=True, timeout=75)
    rows = json.loads(p.stdout)
    observed = {r.get("name"): r for r in rows}
    if len(observed) != len(TRIGGERS) or set(observed) != TRIGGERS:
        raise RuntimeError("Cloud Build trigger set drift; fail-closed")
    if not all(observed[t].get("disabled") is True for t in TRIGGERS):
        raise RuntimeError("Cloud Build trigger re-enabled; fail-closed")


def safe(row):
    name = row["name"]
    generation = row.get("generation", "")
    return (isinstance(name, str) and name.startswith("source/")
            and not any(s in name.lower() for s in BLOCKED)
            and isinstance(generation, str) and generation.isdecimal())


def fingerprint(rows):
    manifest = sorted((r["name"], str(r["generation"])) for r in rows)
    return hashlib.sha256(json.dumps(manifest).encode()).hexdigest()


def execute():
    trigger_guard()
    originals = {}
    for bucket, (total, eligible, untouched) in BUCKETS.items():
        rows = src.list_objects(bucket)
        actual_eligible = [r for r in rows if safe(r)]
        protected = [r for r in rows if not safe(r)]
        if (len(rows), len(actual_eligible), len(protected)) != (total, eligible, untouched):
            raise RuntimeError("Expected bounded GCS inventory changed for " + bucket)
        originals[bucket] = {
            "protected_fingerprint": fingerprint(protected),
            "candidates": actual_eligible,
        }
    deleted = {b: 0 for b in BUCKETS}
    errors = []
    for bucket in BUCKETS:
        token = subprocess.run(["gcloud", "auth", "print-access-token"],
                               capture_output=True, text=True, check=True).stdout.strip()
        if not token:
            raise RuntimeError("No GCS access token")
        for obj in originals[bucket]["candidates"]:
            name = obj["name"]
            generation = obj["generation"]
            url = (
                "https://storage.googleapis.com/storage/v1/b/"
                + urllib.parse.quote(bucket, safe="")
                + "/o/"
                + urllib.parse.quote(name, safe="")
                + "?"
                + urllib.parse.urlencode({"ifGenerationMatch": generation})
            )
            req = urllib.request.Request(
                url, method="DELETE",
                headers={"Authorization": "Bearer " + token})
            try:
                with urllib.request.urlopen(req, timeout=35) as resp:
                    if resp.status != 204:
                        raise RuntimeError("Unexpected GCS delete response")
                deleted[bucket] += 1
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                errors.append({"bucket": bucket, "error_type": type(exc).__name__,
                               "http_status": getattr(exc, "code", None)})
                # Do not leak private object names to public Actions logs.
                if getattr(exc, "code", None) in (401, 403):
                    break
    readback = {}
    for bucket in BUCKETS:
        try:
            remaining = src.list_objects(bucket)
            protected = [r for r in remaining if not safe(r)]
            remaining_eligible = [r for r in remaining if safe(r)]
            readback[bucket] = {
                "remaining": len(remaining),
                "remaining_source": len(remaining_eligible),
                "protected_unchanged":
                    fingerprint(protected) == originals[bucket]["protected_fingerprint"],
                "deleted_requests_succeeded": deleted[bucket],
            }
        except Exception as exc:
            readback[bucket] = {"readback": "NOT_VERIFIED", "error_type": type(exc).__name__}
    verified = (
        not errors and
        all(v.get("remaining_source") == 0 and v.get("protected_unchanged") is True
            for v in readback.values())
    )
    result = {
        "operation": "ONE_TIME_BOUNDED_CLOUDBUILD_SOURCE_DELETE",
        "status": "PASS" if verified else "PARTIAL",
        "readback": readback,
        "errors": errors,
        "deleted_total": sum(deleted.values()),
        "scope": "Two explicit GCS buckets only, source/ objects only; never backups",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return verified


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--execute", action="store_true", required=True)
    a = parser.parse_args()
    if a.project != PROJECT or not a.execute:
        raise SystemExit("Scoped explicit execution required")
    try:
        if not execute():
            return 2
        return 0
    except Exception as exc:
        print(json.dumps({"operation": "ONE_TIME_BOUNDED_CLOUDBUILD_SOURCE_DELETE",
                          "status": "FAIL", "error_type": type(exc).__name__,
                          "detail": str(exc)[:150]}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
