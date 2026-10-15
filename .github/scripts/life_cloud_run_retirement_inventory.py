#!/usr/bin/env python3
"""Bounded, read-only Life Cloud Run retirement inventory; never outputs env/secret values."""
import argparse
import json
import subprocess
import sys

PROJECT = "gen-lang-client-0593591102"
REGION = "us-central1"


def run(*args):
    p = subprocess.run(["gcloud", *args, "--format=json"], capture_output=True, text=True, timeout=90)
    if p.returncode:
        raise RuntimeError("GCP query failed for " + " ".join(args[:4]) + ": " + str(p.returncode))
    value = json.loads(p.stdout)
    return value


def short_name(obj):
    return (obj.get("metadata", {}).get("name")
            or obj.get("name", "").split("/")[-1])


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--project", required=True)
    a.add_argument("--region", required=True)
    o = a.parse_args()
    if (o.project, o.region) != (PROJECT, REGION):
        raise RuntimeError("Refusing project or region outside Life release scope")
    base = ("--project", PROJECT, "--region", REGION)
    services = run("run", "services", "list", *base)
    jobs = run("run", "jobs", "list", *base)
    if not isinstance(services, list) or not isinstance(jobs, list):
        raise RuntimeError("Invalid service/job inventory")
    service_names = sorted(short_name(s) for s in services)
    job_names = sorted(short_name(j) for j in jobs)
    life_services = sorted(n for n in service_names if n.startswith("life-assistant-"))
    life_jobs = sorted(n for n in job_names if n.startswith("life-assistant-"))
    if "life-assistant-api" not in life_services:
        raise RuntimeError("Expected production Life API service missing")
    api = run("run", "services", "describe", "life-assistant-api", *base)
    revisions = run("run", "revisions", "list", "--service", "life-assistant-api", *base)
    if not isinstance(revisions, list) or not revisions:
        raise RuntimeError("Invalid revision inventory")
    rows = []
    for item in revisions:
        name = short_name(item)
        ts = item.get("metadata", {}).get("creationTimestamp") or item.get("createTime")
        if not name or not ts:
            raise RuntimeError("Revision name or creation timestamp missing")
        rows.append({"name": name, "created": ts})
    rows.sort(key=lambda r: (r["created"], r["name"]), reverse=True)
    traffic = [{"revision": t.get("revisionName", ""),
                "tag": t.get("tag") or "", "percent": int(t.get("percent") or 0)}
               for t in api.get("status", {}).get("traffic", [])]
    if sum(t["percent"] for t in traffic) != 100 or any(not t["revision"] for t in traffic):
        raise RuntimeError("Invalid production traffic baseline")
    latest = api.get("status", {}).get("latestReadyRevisionName")
    live = [t["revision"] for t in traffic if t["percent"] > 0]
    tags = [t for t in traffic if t["tag"]]
    try:
        sched = run("scheduler", "jobs", "list", "--location", REGION, "--project", PROJECT)
        if not isinstance(sched, list):
            raise RuntimeError("Invalid scheduler inventory")
        schedule = [{"name": short_name(s), "state": s.get("state","UNKNOWN")}
                    for s in sched if "life" in short_name(s).lower()]
        scheduler_status = "PASS"
    except (RuntimeError, subprocess.TimeoutExpired):
        schedule = []
        scheduler_status = "NOT_VERIFIED"
    executions = {}
    for name in life_jobs:
        try:
            v = run("run", "jobs", "executions", "list", "--job", name, "--limit", "3", *base)
            if not isinstance(v, list):
                raise RuntimeError("Invalid job executions")
            executions[name] = [{"name": short_name(e), "created":
                                 e.get("metadata", {}).get("creationTimestamp", "")
                                 or e.get("createTime", "")}
                                for e in v]
        except (RuntimeError, subprocess.TimeoutExpired):
            executions[name] = "NOT_VERIFIED"
    print(json.dumps({
        "mode": "READ_ONLY", "project": PROJECT, "region": REGION,
        "all_services": service_names, "life_services": life_services,
        "all_job_count": len(job_names), "life_jobs": life_jobs,
        "latest_ready_revision": latest, "live_revisions": live,
        "traffic": traffic, "tagged_revision_count": len(set(t["revision"] for t in tags)),
        "revision_count": len(rows),
        "newest_10": [r["name"] for r in rows[:10]],
        "older_revisions": rows[10:],
        "schedule": schedule, "scheduler_status": scheduler_status,
        "recent_job_executions": executions,
        "no_delete": True
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "FAIL", "type": type(exc).__name__,
                          "message": str(exc)[:160]}), file=sys.stderr)
        sys.exit(1)
