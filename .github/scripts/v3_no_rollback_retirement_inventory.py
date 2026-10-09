#!/usr/bin/env python3
"""Current-CI/CD-only retirement candidate report. READ ONLY; no deletions.

User policy: old Cloud Run revisions / rollback builds do not need retention.
Protect presently serving Cloud Run revisions, configured Cloud Run Jobs, and
the newest AR Docker digest of each package. Never infer that GCS backup,
application or unknown objects are disposable from bucket names alone.
"""
import argparse
from collections import defaultdict
from datetime import datetime
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import v3_ar_docker_inventory as ar

PROJECT = "gen-lang-client-0593591102"
REGION = "us-central1"
GCS_BUCKETS = [
    "gen-lang-client-0593591102-cloudbuild-regional",
    "gen-lang-client-0593591102_cloudbuild",
    "run-sources-gen-lang-client-0593591102-us-central1",
]
SAFE_CI_PREFIXES = {"source", "sources", "logs", "build", "builds", "artifacts"}
PROTECTED_TERMS = ("backup", "database", "postgres", "pg_dump", "snapshot", "ledger",
                   "private", "users", "secrets", "credential", "storage", "uploads")
SHA = re.compile(r"@sha256:[0-9a-f]{64}$", re.I)


def gcloud_describe(category, name):
    p = subprocess.run(
        ["gcloud", "run", category, "describe", name, "--project", PROJECT,
         "--region", REGION, "--format=json"],
        capture_output=True, text=True, timeout=70, check=False)
    if p.returncode:
        raise RuntimeError("Could not read active Cloud Run " + category + " configuration")
    return json.loads(p.stdout)


def current_cloud_run_references():
    services = ar.call("run", "services", "list", "--project", PROJECT, "--region", REGION)
    jobs = ar.call("run", "jobs", "list", "--project", PROJECT, "--region", REGION)
    active_refs = set()
    current_revisions = []
    failures = []

    for service in services:
        name = service.get("metadata", {}).get("name") or service.get("name", "").split("/")[-1]
        try:
            detail = gcloud_describe("services", name)
            active_refs.update(ar.region_docker_image(detail))
            traffic = detail.get("status", {}).get("traffic", [])
            targets = {
                t["revisionName"] for t in traffic
                if t.get("revisionName") and int(t.get("percent") or 0) > 0
            }
            latest = detail.get("status", {}).get("latestReadyRevisionName")
            if latest:
                targets.add(latest)
            if not targets:
                failures.append("service:" + name + ":no_live_revision")
            for revision in sorted(targets):
                rev = gcloud_describe("revisions", revision)
                active_refs.update(ar.region_docker_image(rev))
                current_revisions.append({"service": name, "revision": revision})
        except (ValueError, RuntimeError, subprocess.TimeoutExpired, TypeError):
            failures.append("service:" + name + ":readback_failed")

    for job in jobs:
        name = job.get("metadata", {}).get("name") or job.get("name", "").split("/")[-1]
        try:
            active_refs.update(ar.region_docker_image(gcloud_describe("jobs", name)))
        except (ValueError, RuntimeError, subprocess.TimeoutExpired, TypeError):
            failures.append("job:" + name + ":readback_failed")
    return active_refs, current_revisions, {"services": len(services), "jobs": len(jobs)}, failures


def current_docker_retirement(active_refs):
    repos = ar.call("artifacts", "repositories", "list",
                    "--project", PROJECT, "--location", "all")
    results = []
    failures = []
    for repo in sorted(repos, key=lambda r: r.get("name", "")):
        name = repo.get("name", "").split("/")[-1]
        loc_match = re.fullmatch(
            r"projects/[^/]+/locations/([^/]+)/repositories/([^/]+)", repo.get("name", ""))
        if not loc_match:
            failures.append("unrecognized_ar_repository")
            continue
        location, _ = loc_match.groups()
        if repo.get("format", "").upper() != "DOCKER":
            results.append({"repository": name, "type": repo.get("format"), "status": "NOT_DOCKER"})
            continue
        try:
            rows = ar.docker_images(repo["name"])
            images = []
            for row in rows:
                uri = row.get("uri")
                if not isinstance(uri, str) or not SHA.search(uri):
                    failures.append(name + ":bad_docker_uri")
                    continue
                tags = row.get("tags") or []
                if not isinstance(tags, list):
                    failures.append(name + ":bad_tags")
                    continue
                basename = uri.split("@", 1)[0]
                # Image path within repository is one CI/CD version group.
                path = basename.split("/" + name + "/", 1)
                if len(path) != 2 or not path[1]:
                    failures.append(name + ":bad_package")
                    continue
                images.append({
                    "uri": uri,
                    "image": path[1],
                    "created": row.get("uploadTime") or row.get("createTime") or "",
                    "updated": row.get("updateTime") or "",
                    "tags": tags,
                    "bytes": int(row.get("imageSizeBytes") or 0),
                    "active": ar.referenced(uri, active_refs, tags),
                })
            groups = defaultdict(list)
            for image in images:
                groups[image["image"]].append(image)
            packages = []
            for package, versions in sorted(groups.items()):
                newest = max(versions, key=lambda i: (i["created"], i["updated"], i["uri"]))
                keep = []
                old = []
                for version in versions:
                    why = []
                    if version["active"]:
                        why.append("CURRENT_CLOUD_RUN_OR_JOB")
                    if version["uri"] == newest["uri"]:
                        why.append("LATEST_CI_CD_DIGEST")
                    if why:
                        keep.append({"uri": version["uri"], "tags": version["tags"],
                                     "reason": "+".join(why), "bytes": version["bytes"]})
                    else:
                        old.append({"uri": version["uri"], "tags": version["tags"],
                                    "bytes": version["bytes"],
                                    "classification": "OLD_VERSION_DELETE_CANDIDATE"})
                packages.append({
                    "image": package, "total": len(versions), "keep": keep,
                    "old_delete_candidates": old,
                    "candidate_bytes": sum(i["bytes"] for i in old),
                })
            results.append({
                "repository": name, "type": "DOCKER", "location": location,
                "total": sum(p["total"] for p in packages),
                "keep": sum(len(p["keep"]) for p in packages),
                "old_delete_candidates": sum(len(p["old_delete_candidates"]) for p in packages),
                "candidate_bytes": sum(p["candidate_bytes"] for p in packages),
                "packages": packages,
            })
        except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired):
            failures.append(name + ":docker_inventory_failed")
            results.append({"repository": name, "status": "NOT_VERIFIED"})
    return results, failures


def gcs_token():
    p = subprocess.run(["gcloud", "auth", "print-access-token"], check=True,
                       capture_output=True, text=True, timeout=30)
    if not p.stdout.strip():
        raise RuntimeError("No GCS read token")
    return p.stdout.strip()


def list_gcs_objects(bucket, token):
    if bucket not in GCS_BUCKETS:
        raise ValueError("Refusing unbounded bucket")
    results = []
    cursor = ""
    for _ in range(100):
        params = {"maxResults": "1000", "fields": "items(name,generation,size,updated),nextPageToken"}
        if cursor:
            params["pageToken"] = cursor
        url = ("https://storage.googleapis.com/storage/v1/b/"
               + urllib.parse.quote(bucket, safe="") + "/o?"
               + urllib.parse.urlencode(params))
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.load(resp)
        items = data.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Malformed GCS response")
        results.extend(items)
        cursor = data.get("nextPageToken", "")
        if not cursor:
            return results
    raise RuntimeError("GCS listing truncated")


def gcs_candidates():
    token = gcs_token()
    reports = []
    failures = []
    for bucket in GCS_BUCKETS:
        try:
            rows = list_gcs_objects(bucket, token)
            groups = defaultdict(lambda: {"candidate_objects": 0, "candidate_bytes": 0,
                                         "protected_objects": 0, "protected_bytes": 0})
            for item in rows:
                key = item.get("name")
                if not isinstance(key, str) or not key:
                    raise RuntimeError("GCS metadata lacks object identifier")
                prefix = key.split("/", 1)[0]
                # Never print arbitrary private object name components.
                lower = key.lower()
                is_root_log = bool(re.fullmatch(
                    r"log-[0-9a-f]{8}-[0-9a-f-]{20,50}(?:[.]txt|[.]log)?", lower))
                if prefix in SAFE_CI_PREFIXES:
                    group_key = prefix
                elif is_root_log:
                    group_key = "<cloud-build-root-log>"
                elif "/" not in key and lower.startswith("log-"):
                    group_key = "<root-log-other>"
                elif "/" not in key and lower.startswith("source-"):
                    group_key = "<root-source-other>"
                elif "/" not in key and lower.endswith((".txt", ".log")):
                    group_key = "<root-text-other>"
                elif "/" not in key:
                    group_key = "<root-unclassified>"
                else:
                    group_key = "<unclassified>"
                g = groups[group_key]
                size = int(item.get("size") or 0)
                protected = any(term in lower for term in PROTECTED_TERMS)
                # Old Cloud Build objects, including UUID-named build logs, are
                # candidates when not protected by data-sensitive name patterns.
                candidate = (not protected and
                             (prefix in SAFE_CI_PREFIXES or is_root_log
                              or bucket.startswith("run-sources-")))
                if candidate:
                    g["candidate_objects"] += 1
                    g["candidate_bytes"] += size
                else:
                    g["protected_objects"] += 1
                    g["protected_bytes"] += size
            reports.append({
                "bucket": bucket, "objects": len(rows),
                "delete_candidates": sum(x["candidate_objects"] for x in groups.values()),
                "candidate_bytes": sum(x["candidate_bytes"] for x in groups.values()),
                "protected": sum(x["protected_objects"] for x in groups.values()),
                "prefixes": [{"prefix": prefix, **d} for prefix, d in sorted(groups.items())],
                "object_names_disclosed": False,
            })
        except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError,
                urllib.error.HTTPError) as exc:
            failures.append(bucket + ":" + type(exc).__name__)
            reports.append({"bucket": bucket, "status": "NOT_VERIFIED"})
    return reports, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    a = parser.parse_args()
    if a.project != PROJECT or a.region != REGION:
        raise SystemExit("Refusing unapproved project / region")
    refs, active_rev, scope, errors = current_cloud_run_references()
    docker, ar_errors = current_docker_retirement(refs)
    gcs, gs_errors = gcs_candidates()
    errors.extend(ar_errors + gs_errors)
    result = {
        "mode": "READ_ONLY",
        "policy": "NO_ROLLBACK_KEEP_LATEST_PER_IMAGE_PACKAGE_AND_CURRENT_RUNTIME",
        "no_deletion_performed": True,
        "project": PROJECT, "region": REGION,
        "scope": {**scope, "retained_live_revisions": active_rev,
                  "current_image_refs": len(refs)},
        "artifact_registry": docker, "gcs": gcs,
        "status": "PASS" if not errors else "NOT_VERIFIED",
        "errors": errors,
        "limits": [
            "Only GCP us-central1 Cloud Run active services and configured jobs are treated as live.",
            "Cloud Run old revisions intentionally ignored under user no-rollback policy.",
            "Artifact Registry latest per package based on upload or creation time.",
            "GCS protected/unknown prefixes, database/backups/application data never candidates.",
            "Cross-region, external VM/GKE, in-progress executions and non-Cloud-Run consumers not verified.",
            "This is a candidate manifest, NOT execution of deletion.",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
