#!/usr/bin/env python3
"""Life Cloud Run API: retire stale 0%-traffic V2/V3 tags and revisions to exactly ten.

Mutates only life-assistant-api revisions in one fixed project and region.
Must be invoked after a successful same-main-SHA V3 release, under its concurrency lock.
Never deletes services, jobs, snapshots, GHCR digests, databases or other projects.
"""
import argparse
import json
import re
import subprocess
import sys
from types import SimpleNamespace

from v3_revision_retention import execute as retention_execute
from v3_revision_retention import plan as retention_plan
from v3_revision_retention import revision_list, service_state, traffic_snapshot

PROJECT = "gen-lang-client-0593591102"
REGION = "us-central1"
SERVICE = "life-assistant-api"
ALLOWED_OLD_TAG = re.compile(r"(?:v3-[a-f0-9]{10}|v2-candidate)\Z")
KEEP = 10


def serving(svc):
    traffic = traffic_snapshot(svc)
    serving_rows = [(rev, pct) for rev, _tag, pct in traffic if pct > 0]
    if len(serving_rows) != 1 or serving_rows[0][1] != 100:
        raise ValueError("Only a single explicitly pinned live revision with 100% traffic is supported")
    return serving_rows[0][0]


def select(svc, revisions):
    """Pure, fail-closed candidate selection. Never treats a tag as proof of current usage."""
    existing = retention_plan(svc, revisions, KEEP)
    if existing["before"] < KEEP:
        raise ValueError("Fewer than ten revisions: do not delete")
    keep = set(existing["ordered"][:KEEP])
    live = serving(svc)
    if live not in keep:
        raise ValueError("Live revision is outside newest ten")
    status = svc.get("status") or {}
    if any(status.get(k) not in keep
           for k in ("latestCreatedRevisionName", "latestReadyRevisionName")):
        raise ValueError("Latest created/ready revision would be removed")
    all_names = set(existing["ordered"])
    tags_to_detach = []
    seen = set()
    for name, tag, pct in traffic_snapshot(svc):
        if name not in all_names:
            raise ValueError("Traffic refers to revision not in inventory")
        if name in keep:
            continue
        if pct:
            raise ValueError("Never remove tags from a serving revision")
        if tag:
            if not ALLOWED_OLD_TAG.fullmatch(tag):
                raise ValueError("Unknown old tag type; manual review required")
            if tag in seen:
                raise ValueError("Duplicate old tag")
            seen.add(tag)
            tags_to_detach.append(tag)
    old = [name for name in existing["ordered"] if name not in keep]
    return {"live": live, "newest": existing["ordered"][:KEEP],
            "old": old, "tags": sorted(tags_to_detach),
            "before": existing["before"],
            "serving": [(n, p) for n, _tag, p in traffic_snapshot(svc) if p]}


def verify_baseline(original, project=PROJECT, region=REGION):
    observed = service_state(project, region, SERVICE)
    if serving(observed) != original["live"]:
        raise ValueError("Production live revision changed during retirement")
    positive = [(name, pct) for name, _tag, pct in traffic_snapshot(observed) if pct]
    if positive != original["serving"]:
        raise ValueError("Production traffic weights changed")
    # A concurrent release may still point to a revision inside the latest
    # ten; membership is not enough. Require the exact pre-cleanup identities.
    if observed.get("status", {}).get("latestReadyRevisionName") != original["latest_ready"]:
        raise ValueError("Concurrent ready revision changed")
    if observed.get("status", {}).get("latestCreatedRevisionName") != original["latest_created"]:
        raise ValueError("Concurrent created revision changed")
    current_tags = {(n, t) for n, t, _p in traffic_snapshot(observed) if t and n in original["newest"]}
    original_tags = original["preserved_tags"]
    if current_tags != original_tags:
        raise ValueError("A preserved live or staging tag changed")
    return observed


def apply(project, region):
    if (project, region) != (PROJECT, REGION):
        raise ValueError("Outside fixed Life project/region")
    svc = service_state(project, region, SERVICE)
    revisions = revision_list(project, region, SERVICE)
    snapshot = select(svc, revisions)
    snapshot["preserved_tags"] = {
        (n, t) for n, t, _p in traffic_snapshot(svc) if t and n in snapshot["newest"]
    }
    snapshot["latest_ready"] = svc["status"]["latestReadyRevisionName"]
    snapshot["latest_created"] = svc["status"]["latestCreatedRevisionName"]
    print(json.dumps({"stage": "PLAN", "before": snapshot["before"],
                      "keep": KEEP, "to_delete": len(snapshot["old"]),
                      "detach_old_tags": len(snapshot["tags"]),
                      "live": snapshot["live"], "newest": snapshot["newest"]}), flush=True)
    verify_baseline(snapshot, project, region)
    # Tags on historical 0%-traffic candidates are legacy preview endpoints.
    # Use ONLY --remove-tags; it changes no traffic assignments or container images.
    for i in range(0, len(snapshot["tags"]), 10):
        tags = snapshot["tags"][i:i + 10]
        verify_baseline(snapshot, project, region)
        subprocess.run(["gcloud", "run", "services", "update-traffic", SERVICE,
                        "--project", project, "--region", region,
                        "--remove-tags=" + ",".join(tags),
                        "--quiet"], capture_output=True, text=True, timeout=180, check=True)
        observed = verify_baseline(snapshot, project, region)
        remaining_tags = {t for _n, t, _p in traffic_snapshot(observed) if t}
        if any(t in remaining_tags for t in tags):
            raise ValueError("Old candidate tag still referenced after detach")
        print(json.dumps({"stage": "DETACH_TAGS", "detached_count": min(i+10, len(snapshot["tags"]))}),
              flush=True)
    current = verify_baseline(snapshot, project, region)
    planned = retention_plan(current, revision_list(project, region, SERVICE), KEEP)
    if set(planned["delete"]) != set(snapshot["old"]):
        raise ValueError("Post-detach deletion plan differs from audited inventory")
    # Existing retention engine rechecks traffic/tags/ready revision before EVERY delete.
    result = retention_execute(SimpleNamespace(
        project=project, region=region, service=SERVICE, keep=KEEP,
        expected_live_revision=snapshot["live"], protect=[], apply=True, live_passed=True))
    verify_baseline(snapshot, project, region)
    if result.get("remaining_count") != KEEP or result.get("status") != "PASS":
        raise ValueError("Post-deletion readback does not show exactly ten revisions")
    final_names = {r["metadata"]["name"] for r in revision_list(project, region, SERVICE)}
    if final_names != set(snapshot["newest"]):
        raise ValueError("Unexpected final revision identities")
    print(json.dumps({
        "stage": "DONE", "status": "PASS", "before": snapshot["before"],
        "deleted": len(result.get("deleted", [])), "remaining": KEEP,
        "live_unchanged": True, "jobs_deleted": 0, "services_deleted": 0,
        "region": region, "service": SERVICE
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        raise SystemExit("Refusing mutation without explicit --apply")
    try:
        apply(args.project, args.region)
    except (RuntimeError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__,
                          "reason": str(exc)[:160]}), file=sys.stderr)
        sys.exit(1)
