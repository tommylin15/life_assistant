#!/usr/bin/env python3
"""Read-only bounded retired free-events Cloud Scheduler inspection.

Does not delete, pause, run or update Cloud Scheduler or Cloud Run resources.
A Cloud Run Job's mere existence is not evidence that the job is scheduled.
"""
from __future__ import annotations

import argparse
import json
import subprocess


def assess(items: list[dict]) -> dict:
    observed = []
    for job in items:
        name = str(job.get("name") or "").rsplit("/", 1)[-1]
        target = str((job.get("httpTarget") or {}).get("uri") or "")
        topic = str((job.get("pubsubTarget") or {}).get("topicName") or "")
        if "life-assistant-free-events" not in name and (
            "life-assistant-free-events" not in target and
            "life-assistant-free-events" not in topic
        ):
            continue
        state = str(job.get("state") or "UNKNOWN").upper()
        observed.append({
            "job": name,
            "state": state,
            "safe_in_region": state in ("PAUSED", "DISABLED"),
        })
    observed.sort(key=lambda item: item["job"])
    ambiguous = any(o["state"] not in ("ENABLED", "PAUSED", "DISABLED") for o in observed)
    active = any(o["state"] == "ENABLED" for o in observed)
    status = "FAIL" if active else ("NOT_VERIFIED" if ambiguous else "PASS")
    return {
        "status": status,
        "matching_scheduler_jobs": observed,
        "source_job_safe_in_checked_region": status == "PASS",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args()
    command = [
        "gcloud", "scheduler", "jobs", "list",
        "--project", args.project, "--location", args.region,
        "--format=json",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    output = {
        "mode": "READ_ONLY",
        "region": args.region,
        "scope": "Cloud Scheduler jobs in this region only; external and other-region triggers not assessed",
    }
    if result.returncode:
        output["status"] = "NOT_VERIFIED"
        output["reason"] = "scheduler_permission_or_api_unavailable"
        output["matching_scheduler_jobs"] = []
    else:
        try:
            jobs = json.loads(result.stdout)
            if not isinstance(jobs, list):
                raise ValueError("unexpected Scheduler response")
            output.update(assess(jobs))
        except (ValueError, TypeError):
            output["status"] = "NOT_VERIFIED"
            output["reason"] = "invalid_scheduler_response"
            output["matching_scheduler_jobs"] = []
    print(json.dumps(output, sort_keys=True))
    if output["status"] == "FAIL":
        raise SystemExit(2)
    # A missing IAM permission stays clearly NOT_VERIFIED in the run summary,
    # not a false negative; never trigger an unrelated production outage.


if __name__ == "__main__":
    main()
