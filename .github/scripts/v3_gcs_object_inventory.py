#!/usr/bin/env python3
"""Read-only GCS metadata inventory for two pre-identified legacy Cloud Build buckets.

NEVER mutates/deletes objects. Names and contents are not printed. Every item is
classified as a CANDIDATE only, because other project triggers may share buckets.
"""
import argparse
from collections import Counter
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

CANDIDATE_BUCKETS = (
    "gen-lang-client-0593591102-cloudbuild-regional",
    "gen-lang-client-0593591102_cloudbuild",
)


def list_objects(bucket: str) -> list[dict]:
    if bucket not in CANDIDATE_BUCKETS:
        raise ValueError("bucket not in bounded CI/CD candidate inventory")
    token = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True).stdout.strip()
    if not token:
        raise ValueError("GCP identity token not available")
    cursor = ""
    entries = []
    for _ in range(100):
        params = {"maxResults": "1000", "fields":
                  "items(name,generation,size,updated),nextPageToken"}
        if cursor:
            params["pageToken"] = cursor
        url = ("https://storage.googleapis.com/storage/v1/b/"
               + urllib.parse.quote(bucket, safe="")
               + "/o?" + urllib.parse.urlencode(params))
        req = urllib.request.Request(
            url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=35) as response:
            data = json.load(response)
        if not isinstance(data.get("items", []), list):
            raise ValueError("unrecognized GCS objects response")
        entries.extend(data.get("items", []))
        cursor = data.get("nextPageToken", "")
        if not cursor:
            return entries
    raise ValueError("inventory pagination capped: NOT VERIFIED")


def metadata_summary(bucket: str, entries: list[dict]) -> dict:
    bytes_total = 0
    categories = Counter()
    for o in entries:
        name = o.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("incomplete object metadata")
        bytes_total += int(o["size"])
        prefix = name.split("/", 1)[0]
        if prefix in ("source", "logs", "artifacts", "build", "builds"):
            categories["POSSIBLE_CLOUD_BUILD"] += 1
        else:
            categories["UNCLASSIFIED_PROTECTED"] += 1
    return {"bucket": bucket, "readback": "PASS",
            "objects": len(entries), "bytes": bytes_total,
            "categories": dict(sorted(categories.items())),
            "deletion_eligible": False,
            "reason": "Other Cloud Build triggers exist; object ownership and downstream dependencies NOT VERIFIED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    opts = parser.parse_args()
    if opts.project != "gen-lang-client-0593591102":
        raise SystemExit("Wrong project")
    result = {"mode": "READ_ONLY", "project": opts.project, "buckets": []}
    failed = False
    for bucket in CANDIDATE_BUCKETS:
        try:
            result["buckets"].append(metadata_summary(bucket, list_objects(bucket)))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                result["buckets"].append({
                    "bucket": bucket, "readback": "PASS",
                    "bucket_deleted": True, "objects": 0, "bytes": 0,
                    "categories": {}, "deletion_eligible": False,
                    "reason": "Verified legacy CI/CD bucket absent (404)",
                })
            else:
                failed = True
                result["buckets"].append({
                    "bucket": bucket, "readback": "NOT_VERIFIED",
                    "reason": "HTTPError: failed GCS inventory (not 404)",
                    "deletion_eligible": False,
                })
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
            failed = True
            result["buckets"].append({
                "bucket": bucket, "readback": "NOT_VERIFIED",
                "reason": f"{type(exc).__name__}: object-level access or inventory failed",
                "deletion_eligible": False})
    print(json.dumps(result, indent=2, sort_keys=True))
    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
