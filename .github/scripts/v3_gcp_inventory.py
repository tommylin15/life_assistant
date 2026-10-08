#!/usr/bin/env python3
"""Read-only metadata inventory: Cloud Run, AR, GCS and Cloud Build. NEVER DELETE."""
import argparse
import json
import subprocess
import sys


def query(*args):
    p = subprocess.run(["gcloud", *args, "--format=json"], capture_output=True, text=True)
    if p.returncode:
        return {"status": "NOT_VERIFIED", "error": p.stderr.strip()[:160],
                "count": None, "items": []}
    try:
        items = json.loads(p.stdout)
    except ValueError:
        return {"status": "NOT_VERIFIED", "error": "malformed CLI JSON",
                "count": None, "items": []}
    if not isinstance(items, list):
        return {"status": "NOT_VERIFIED", "error": "expected list",
                "count": None, "items": []}
    return {"status": "PASS", "count": len(items), "items": items}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--region", required=True)
    args = p.parse_args()
    project, region = args.project, args.region
    checks = {
        "run_services": query("run", "services", "list", "--project", project,
                              "--region", region),
        "run_jobs": query("run", "jobs", "list", "--project", project,
                          "--region", region),
        "ar_repositories": query("artifacts", "repositories", "list",
                                 "--project", project, "--location", "all"),
        "gcs_buckets": query("storage", "buckets", "list",
                            "--project", project),
        "cloud_build_triggers": query("builds", "triggers", "list",
                                      "--project", project, "--region", region)
    }
    summaries = {}
    for key, value in checks.items():
        data = {"status": value["status"], "count": value["count"]}
        if value["status"] != "PASS":
            data["reason"] = "MISSING_PERMISSION_OR_API_UNAVAILABLE"
        elif key == "run_services":
            data["life_assistant_services"] = sorted(
                (o.get("metadata", {}).get("name", "") or
                 o.get("name", "").split("/")[-1])
                for o in value["items"]
                if "life-assistant" in json.dumps(o).lower())
        elif key == "run_jobs":
            data["life_assistant_jobs"] = sorted(
                (o.get("metadata", {}).get("name", "") or
                 o.get("name", "").split("/")[-1])
                for o in value["items"]
                if "life-assistant" in json.dumps(o).lower())
        elif key == "ar_repositories":
            data["repo_names"] = sorted(
                o.get("name", "").split("/")[-1]
                for o in value["items"])
        elif key == "gcs_buckets":
            # Candidate enumeration only, never infer unused from bucket names.
            # Backup, application, personal and shared data are intentionally omitted.
            data["possible_ci_cd_buckets"] = sorted(
                o.get("name", "").removeprefix("gs://")
                for o in value["items"]
                if any(x in o.get("name", "").lower()
                       for x in ("cloudbuild", "build-staging", "cloud-build")))
            data["classification"] = "CANDIDATES_ONLY_NOT_DELETE_APPROVED"
        elif key == "cloud_build_triggers":
            data["triggers"] = sorted(
                ({"name": o.get("name"), "id": o.get("id"),
                  "disabled": o.get("disabled", False)}
                 for o in value["items"]
                 if o.get("name", "").startswith("life-assistant-")),
                key=lambda entry: entry["name"] or "")
        summaries[key] = data
    print(json.dumps({"project": project, "region": region,
                      "mode": "READ_ONLY", "checks": summaries}, indent=2))
    if any(v["status"] != "PASS" for v in summaries.values()):
        sys.exit(2)


if __name__ == "__main__":
    main()
