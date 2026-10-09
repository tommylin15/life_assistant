#!/usr/bin/env python3
"""Fail-closed Firebase Hosting release and Cloud Run pin verifier.

The Hosting REST version config (not local firebase.json) is authoritative.
This module never deploys or changes GCP resources.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

STAGE_SITE = "life-assistant-v3-stage-tl15"
PROD_SITE = "gen-lang-client-0593591102"
SERVICE = "life-assistant-api"
REGION = "us-central1"
PATHS = frozenset({"/api/**", "/auth/**"})
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
REV_PATTERN = re.compile(r"^life-assistant-api-[a-zA-Z0-9-]+$")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def release_version(releases: dict, site: str, channel: str) -> str:
    require(isinstance(releases, dict), "Invalid releases response")
    rows = releases.get("releases", [])
    require(isinstance(rows, list) and len(rows) > 0, "No prior released version")
    rows = sorted(rows, key=lambda item: item.get("releaseTime", ""), reverse=True)
    top = rows[0]
    name = top.get("name", "")
    require(
        name.startswith(f"sites/{site}/channels/{channel}/releases/")
        or (channel == "live" and name.startswith(f"sites/{site}/releases/")),
        "Release is from a different site/channel",
    )
    version = top.get("version", {}).get("name", "")
    require(version.startswith(f"sites/{site}/versions/"), "Release version site mismatch")
    return version


def pinned_routes(version: dict, cloud_run: dict, expected_revision: str | None = None) -> dict:
    require(isinstance(version, dict), "Invalid Hosting version")
    require(version.get("name", "").startswith(f"sites/{STAGE_SITE}/versions/"),
            "Hosting version is not in the staging site")
    require(version.get("status") == "FINALIZED", "Hosting version is not finalized")
    if expected_revision is not None:
        require(bool(REV_PATTERN.fullmatch(expected_revision)), "Invalid candidate revision")
    status = cloud_run.get("status", {})
    traffic = status.get("traffic", [])
    require(isinstance(traffic, list) and traffic, "Cloud Run traffic is unavailable")
    tags = {}
    for item in traffic:
        tag, rev = item.get("tag"), item.get("revisionName")
        if tag:
            require(rev and tag not in tags, "Ambiguous Cloud Run tag")
            tags[tag] = rev
    routes = {}
    for rewrite in version.get("config", {}).get("rewrites", []):
        path = rewrite.get("glob")
        if path not in PATHS:
            continue
        require(path not in routes, "Duplicate critical rewrite")
        run = rewrite.get("run", {})
        require(run.get("serviceId") == SERVICE and run.get("region", REGION) == REGION,
                "Critical rewrite targets an unexpected service or region")
        tag = run.get("tag")
        require(isinstance(tag, str) and tag in tags, "Pinned revision tag not found")
        revision = tags[tag]
        if expected_revision is not None:
            require(revision == expected_revision, "Rewrite tag does not map to candidate")
        routes[path] = {"tag": tag, "revision": revision}
    require(set(routes) == PATHS, "Missing /api/** or /auth/** rewrite")
    require(routes["/api/**"]["revision"] == routes["/auth/**"]["revision"],
            "API/auth rewrites target different revisions")
    return routes


def protected_traffic(cloud_run: dict) -> list:
    traffic = cloud_run.get("status", {}).get("traffic", [])
    require(isinstance(traffic, list), "Invalid production Cloud Run traffic")
    result = sorted((i.get("revisionName"), i.get("tag", ""), int(i.get("percent", 0) or 0))
                    for i in traffic)
    require(result and sum(row[2] for row in result) == 100,
            "Production Cloud Run traffic sum not 100")
    return result


def verify_snapshot(
    preview_releases: dict, preview_version: dict, stage_releases: dict,
    stage_version: dict, cloud_run: dict, expected_sha: str, candidate_revision: str,
    preview_visible_sha: str, stage_visible_sha: str,
) -> dict:
    require(bool(SHA_PATTERN.fullmatch(expected_sha)), "Expected full source SHA")
    preview_id = release_version(preview_releases, STAGE_SITE, f"v3-{expected_sha[:10]}")
    require(preview_version.get("name") == preview_id, "Preview version readback mismatch")
    require(preview_visible_sha.strip() == expected_sha, "Preview public SHA mismatch")
    candidate_routes = pinned_routes(preview_version, cloud_run, candidate_revision)
    old_id = release_version(stage_releases, STAGE_SITE, "live")
    require(stage_version.get("name") == old_id, "Prior staging live version mismatch")
    old_routes = pinned_routes(stage_version, cloud_run)
    require(bool(SHA_PATTERN.fullmatch(stage_visible_sha.strip())),
            "Previous staging live SHA is not a full SHA")
    require(old_id != preview_id, "Already live: do not overwrite without readback")
    return {
        "status": "PASS",
        "preview_version": preview_id,
        "previous_live_version": old_id,
        "previous_live_sha": stage_visible_sha.strip(),
        "candidate_routes": candidate_routes,
        "previous_routes": old_routes,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-releases", type=Path, required=True)
    parser.add_argument("--preview-version", type=Path, required=True)
    parser.add_argument("--stage-releases", type=Path, required=True)
    parser.add_argument("--stage-version", type=Path, required=True)
    parser.add_argument("--cloud-run", type=Path, required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--preview-sha", required=True)
    parser.add_argument("--stage-sha", required=True)
    args = parser.parse_args()
    def load(file: Path) -> dict:
        return json.loads(file.read_text(encoding="utf-8"))
    try:
        evidence = verify_snapshot(
            load(args.preview_releases), load(args.preview_version),
            load(args.stage_releases), load(args.stage_version),
            load(args.cloud_run), args.sha, args.revision, args.preview_sha, args.stage_sha,
        )
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)[:160]}))
        raise SystemExit(1) from None
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
