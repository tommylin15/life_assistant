"""Resolve a numeric Secret Manager bundle revision without reading its payload.

Staging selects the most recent ENABLED version. Production LINE promotions use
a prior successful staging run's proof; legacy deployments preserve the serving
revision's already pinned version. No Secret Manager values are logged.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

BUNDLE = "life-assistant-bundle"
VERSION_RE = re.compile(r"[1-9][0-9]*")
SHA_RE = re.compile(r"[0-9a-f]{40}")


def latest_enabled(versions):
    if not isinstance(versions, list):
        raise ValueError("Invalid Secret Manager versions response")
    ids = []
    for item in versions:
        if item.get("state") != "ENABLED":
            continue
        name = str(item.get("name", "")).rsplit("/", 1)[-1]
        if VERSION_RE.fullmatch(name):
            ids.append(int(name))
    if not ids:
        raise ValueError("No ENABLED numeric bundle version")
    return str(max(ids))


def serving_version(service, revisions):
    """Find a common bundle version among all revisions serving positive traffic."""
    serving = [x["revisionName"] for x in service.get("status", {}).get("traffic", [])
               if int(x.get("percent") or 0) > 0 and x.get("revisionName")]
    if not serving:
        raise ValueError("No explicit live serving revisions")
    values = set()
    for name in serving:
        doc = revisions[name]
        containers = doc.get("spec", {}).get("containers", [])
        if len(containers) != 1:
            raise ValueError("Unexpected live revision container count")
        refs = [item.get("valueFrom", {}).get("secretKeyRef", {})
                for item in containers[0].get("env", [])
                if item.get("name") == "LIFE_ASSISTANT_BUNDLE"]
        if len(refs) != 1 or refs[0].get("name") != BUNDLE:
            raise ValueError("Live revision bundle reference is missing or different")
        values.add(str(refs[0].get("key", "")))
    if len(values) != 1:
        raise ValueError("Live revisions use inconsistent bundle versions")
    value = values.pop()
    if value == "latest":
        return None  # One-time normalization of a legacy unpinned reference.
    if not VERSION_RE.fullmatch(value):
        raise ValueError("Unexpected bundle version in live revision")
    return value


def receipt_version(receipt, release_sha, project):
    if not SHA_RE.fullmatch(release_sha or ""):
        raise ValueError("Invalid release SHA")
    if (not isinstance(receipt, dict)
            or receipt.get("release_sha") != release_sha
            or receipt.get("project") != project
            or receipt.get("secret") != BUNDLE
            or receipt.get("stage_origin") != "https://life-assistant-v3-stage-tl15.web.app"
            or not VERSION_RE.fullmatch(str(receipt.get("version", "")))):
        raise ValueError("Staging LINE proof mismatch")
    return str(receipt["version"])


class SecretMetadataError(ValueError):
    pass


def gcloud_json(*args):
    operation = ("versions_list" if args[:3] == ("secrets", "versions", "list")
                 else "versions_metadata" if args[:3] == ("secrets", "versions", "describe")
                 else "cloud_run_metadata")
    try:
        result = subprocess.run(["gcloud", *args, "--format=json"],
                                check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        # gcloud may include request metadata in stderr. Do not emit raw stderr
        # and never access/print the Secret payload to debug metadata failures.
        error = ((exc.stderr or b"").decode("utf-8", "replace")
                 if isinstance(exc.stderr, bytes) else str(exc.stderr or "")).lower()
        if any(s in error for s in ("permission_denied", "permission denied",
                                    "does not have permission", "403", "not authorized")):
            category = "PERMISSION_DENIED"
        elif any(s in error for s in ("api has not been used", "api is disabled",
                                      "service disabled")):
            category = "API_DISABLED"
        elif any(s in error for s in ("not found", "404")):
            category = "NOT_FOUND"
        elif any(s in error for s in ("unauthenticated", "invalid credentials", "401")):
            category = "UNAUTHENTICATED"
        elif any(s in error for s in ("unrecognized arguments", "invalid choice")):
            category = "INVALID_COMMAND"
        else:
            category = "OTHER"
        raise SecretMetadataError(f"operation={operation} category={category}") from None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise SecretMetadataError(f"operation={operation} category=INVALID_JSON") from None


def resolve(mode, project, region, service, release_sha="", receipt=None):
    if mode == "staged":
        version = receipt_version(receipt, release_sha, project)
    elif mode == "preserve-live":
        live = gcloud_json("run", "services", "describe", service,
                           "--project=" + project, "--region=" + region)
        revisions = {}
        for part in live.get("status", {}).get("traffic", []):
            if int(part.get("percent") or 0) > 0 and part.get("revisionName"):
                name = part["revisionName"]
                revisions[name] = gcloud_json("run", "revisions", "describe", name,
                                               "--project=" + project, "--region=" + region)
        version = serving_version(live, revisions)
    elif mode == "latest":
        version = None
    else:
        raise ValueError("Unsupported resolve mode")

    versions = gcloud_json("secrets", "versions", "list", BUNDLE,
                           "--project=" + project)
    enabled = {str(int(str(v.get("name", "")).rsplit("/", 1)[-1]))
               for v in versions if v.get("state") == "ENABLED"
               and VERSION_RE.fullmatch(str(v.get("name", "")).rsplit("/", 1)[-1])}
    if version is None:
        return latest_enabled(versions)
    if version not in enabled:
        raise ValueError("Pinned bundle version is not ENABLED")
    return version


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=("latest", "preserve-live", "staged", "write-proof"))
    ap.add_argument("--project", required=True)
    ap.add_argument("--region", default="us-central1")
    ap.add_argument("--service", default="life-assistant-api")
    ap.add_argument("--release-sha", default="")
    ap.add_argument("--receipt", type=Path)
    ap.add_argument("--version")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.mode == "write-proof":
        if not SHA_RE.fullmatch(args.release_sha) or not VERSION_RE.fullmatch(args.version or "") or not args.output:
            ap.error("Invalid stage proof identity")
        doc = {
            "release_sha": args.release_sha,
            "project": args.project,
            "secret": BUNDLE,
            "version": args.version,
            "stage_origin": "https://life-assistant-v3-stage-tl15.web.app",
        }
        args.output.write_text(json.dumps(doc, sort_keys=True) + "\n")
        print("line_stage_bundle_proof=PREPARED version=" + args.version)
        return
    if args.mode == "staged" and args.receipt is None:
        ap.error("Staged promotion requires a previous stage proof")
    proof = json.loads(args.receipt.read_text()) if args.receipt else None
    version = resolve(args.mode, args.project, args.region, args.service,
                      args.release_sha, proof)
    print(version)


if __name__ == "__main__":
    try:
        main()
    except SecretMetadataError as exc:
        raise SystemExit("bundle_resolution=FAIL " + str(exc)) from None
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit("bundle_resolution=FAIL category=" + type(exc).__name__) from None
