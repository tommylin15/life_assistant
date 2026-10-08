#!/usr/bin/env python3
"""Fail-closed Cloud Run revision retention. Never touch jobs, images or other services."""
import argparse
import json
import subprocess
import sys


def gcloud(*args):
    p = subprocess.run(["gcloud", *args], capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


def service_state(project, region, name):
    return gcloud("run", "services", "describe", name, "--project", project,
                  "--region", region, "--format=json")


def revision_list(project, region, name):
    return gcloud("run", "revisions", "list", "--service", name,
                  "--project", project, "--region", region, "--format=json")


def revision_name(item):
    return item.get("metadata", {}).get("name") or item.get("name", "").split("/")[-1]


def revision_created(item):
    return item.get("metadata", {}).get("creationTimestamp") or item.get("createTime", "")


def traffic_snapshot(svc):
    rows = svc.get("status", {}).get("traffic", [])
    return sorted((str(row.get("revisionName", "")), str(row.get("tag", "")),
                   int(row.get("percent", 0) or 0)) for row in rows)


def plan(svc, revisions, keep, explicitly_protected=()):
    if keep < 10:
        raise ValueError("Production retention floor is 10")
    rows = list(revisions)
    if not isinstance(revisions, list) or not rows:
        raise ValueError("Revision inventory is missing")
    names = [revision_name(item) for item in rows]
    if len(set(names)) != len(rows) or not all(names):
        raise ValueError("Duplicate or missing revision names")
    if not all(revision_created(item) for item in rows):
        raise ValueError("Creation timestamp missing: fail closed")
    ordered = sorted(rows, key=lambda r: (revision_created(r), revision_name(r)),
                     reverse=True)
    retained = {revision_name(r) for r in ordered[:keep]}
    protected = set(explicitly_protected)
    status = svc.get("status") or {}
    ready = status.get("latestReadyRevisionName")
    created = status.get("latestCreatedRevisionName")
    if not ready or not created:
        raise ValueError("Latest revision not reported by Cloud Run")
    protected.update([ready, created])
    for rev, tag, percent in traffic_snapshot(svc):
        if not rev:
            raise ValueError("Traffic or tag without revision identity: fail closed")
        if tag or percent:
            protected.add(rev)
    if any(name not in names for name in protected):
        raise ValueError("Protected revision is absent from inventory")
    delete = [revision_name(r) for r in ordered[keep:]
              if revision_name(r) not in protected]
    return {"ordered": [revision_name(r) for r in ordered],
            "protected": sorted(protected),
            "delete": delete,
            "retain": [revision_name(r) for r in ordered
                       if revision_name(r) not in set(delete)],
            "before": len(rows), "keep": keep}


def execute(args):
    svc = service_state(args.project, args.region, args.service)
    revisions = revision_list(args.project, args.region, args.service)
    current = traffic_snapshot(svc)
    active = [rev for rev, _tag, percent in current if percent > 0]
    if not active or any(p > 100 for _, _, p in current):
        raise ValueError("No valid live traffic baseline")
    if args.expected_live_revision not in active:
        raise ValueError("Expected promoted live revision is not receiving traffic")
    if sum(p for _, _, p in current) != 100:
        raise ValueError("Traffic shares do not sum to 100")
    result = plan(svc, revisions, args.keep, args.protect)
    result.update(service=args.service, region=args.region,
                  mode="APPLY" if args.apply else "DRY_RUN",
                  expected_live=args.expected_live_revision)
    if not args.apply:
        return result
    if not args.live_passed:
        raise ValueError("Live gate evidence is mandatory for deletion")
    baseline = (traffic_snapshot(svc), svc.get("status", {}).get("latestReadyRevisionName"),
                svc.get("status", {}).get("latestCreatedRevisionName"))
    deleted = []
    for name in result["delete"]:
        latest = service_state(args.project, args.region, args.service)
        snapshot = (traffic_snapshot(latest),
                    latest.get("status", {}).get("latestReadyRevisionName"),
                    latest.get("status", {}).get("latestCreatedRevisionName"))
        if snapshot != baseline:
            raise ValueError("Concurrent traffic/tag/deployment change: refusing deletion")
        observed = revision_list(args.project, args.region, args.service)
        refreshed = plan(latest, observed, args.keep, args.protect)
        if name not in refreshed["delete"]:
            raise ValueError("Cleanup target no longer eligible: refusing deletion")
        subprocess.run(["gcloud", "run", "revisions", "delete", name, "--project",
                        args.project, "--region", args.region, "--quiet"], check=True)
        deleted.append(name)
    final_service = service_state(args.project, args.region, args.service)
    if traffic_snapshot(final_service) != baseline[0]:
        raise ValueError("Live traffic changed during cleanup")
    remaining = revision_list(args.project, args.region, args.service)
    result.update(deleted=deleted, remaining_count=len(remaining),
                  status="PASS" if len(remaining) <= args.keep else "PARTIAL_PROTECTED")
    if not args.apply:
        raise AssertionError("Unreachable")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--service", required=True)
    p.add_argument("--keep", type=int, default=10)
    p.add_argument("--expected-live-revision", required=True)
    p.add_argument("--protect", action="append", default=[])
    p.add_argument("--apply", action="store_true")
    p.add_argument("--live-passed", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(execute(args), indent=2, sort_keys=True))
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)[:240]}),
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
