#!/usr/bin/env python3
"""Read-only GCP Artifact Registry Docker image and Cloud Run reference inventory.

NEVER deletes images, tags, repositories, Cloud Run resources, or data.
An image not found in the Cloud Run reference set is NOT approved for deletion:
other regions, rollbacks, GCE, GKE, VM jobs, and external consumers may rely on it.
"""
import argparse
import json
import re
import subprocess
import sys

PROJECT = "gen-lang-client-0593591102"
REGION = "us-central1"
SHA = re.compile(r"sha256:[0-9a-f]{64}", re.I)


def call(*args, timeout=180):
    cmd = ["gcloud", *args, "--format=json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"gcloud read-only command failed: {' '.join(args[:4])} ({result.returncode})")
    try:
        parsed = json.loads(result.stdout)
    except ValueError as exc:
        raise RuntimeError("GCP returned non-JSON output") from exc
    if not isinstance(parsed, list):
        raise RuntimeError("GCP read-only list returned an unexpected type")
    return parsed


def region_docker_image(entry):
    """Return just safe image references, never print Cloud Run manifests/secrets."""
    result = set()
    if isinstance(entry, dict):
        for key, value in entry.items():
            if key in ("image", "imageDigest", "imageUri") and isinstance(value, str):
                result.add(value)
            elif isinstance(value, (dict, list)):
                result.update(region_docker_image(value))
    elif isinstance(entry, list):
        for value in entry:
            result.update(region_docker_image(value))
    return result


def image_key(uri):
    if not isinstance(uri, str):
        return ""
    if "@" in uri:
        return uri.split("@", 1)[0]
    return uri.rsplit(":", 1)[0] if ":" in uri.rsplit("/", 1)[-1] else uri


def referenced(image_uri, refs, tags):
    digest = SHA.search(image_uri)
    base = image_key(image_uri)
    all_refs = [x for x in refs if isinstance(x, str)]
    if any(image_uri == r for r in all_refs):
        return True
    if digest and any(image_key(r) == base and digest.group().lower() in r.lower() for r in all_refs):
        return True
    return any(image_key(r) == base and r.rsplit(":", 1)[-1] in tags
               for r in all_refs if "@" not in r and ":" in r.rsplit("/", 1)[-1])


def inventory(project, region):
    if project != PROJECT or region != REGION:
        raise ValueError("Refusing unapproved project or Cloud Run region")
    repos = call("artifacts", "repositories", "list", "--project", project, "--location", "all")
    services = call("run", "services", "list", "--project", project, "--region", region)
    revisions = call("run", "revisions", "list", "--project", project, "--region", region,
                     "--limit=10000")
    jobs = call("run", "jobs", "list", "--project", project, "--region", region)
    if len(revisions) >= 10000:
        raise RuntimeError("Cloud Run revisions truncated: reference audit incomplete")

    # List responses may omit container image details; describe every live job
    # and service, and every revision that does not expose its image directly.
    refs = set()
    failures = []
    sources = {"services": len(services), "revisions": len(revisions), "jobs": len(jobs)}
    for label, rows in (("services", services), ("revisions", revisions), ("jobs", jobs)):
        for row in rows:
            seen = region_docker_image(row)
            name = (row.get("metadata", {}).get("name")
                    or row.get("name", "").split("/")[-1])
            if label == "jobs" or label == "services" or (label == "revisions" and not seen):
                try:
                    proc = subprocess.run(
                        ["gcloud", "run", label, "describe", name,
                         "--project", project, "--region", region, "--format=json"],
                        capture_output=True, text=True, timeout=90, check=False,
                    )
                    if proc.returncode:
                        raise RuntimeError("Describe was not successful")
                    seen.update(region_docker_image(json.loads(proc.stdout)))
                except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
                    failures.append(f"{label}:{name}")
            refs.update(seen)

    results = []
    for repo in sorted(repos, key=lambda v: v.get("name", "")):
        raw_name = repo.get("name", "")
        match = re.fullmatch(r"projects/[^/]+/locations/([^/]+)/repositories/([^/]+)", raw_name)
        if not match:
            failures.append("unexpected_repository_resource")
            continue
        location, repo_name = match.groups()
        fmt = repo.get("format", "")
        item = {"repository": repo_name, "location": location, "format": fmt,
                "classification": "READ_ONLY_NOT_DELETE_APPROVED"}
        if fmt.upper() == "DOCKER":
            uri = f"{location}-docker.pkg.dev/{project}/{repo_name}"
            try:
                rows = call("artifacts", "docker", "images", "list", uri,
                            "--include-tags", "--limit=10000", timeout=240)
                if len(rows) >= 10000:
                    raise RuntimeError("image list may be truncated")
                images = []
                item["image_row_fields"] = sorted(rows[0]) if rows else []
                for row in rows:
                    image_uri = row.get("uri", "") or row.get("image", "")
                    # gcloud CLI JSON may expose IMAGE and DIGEST separately,
                    # rather than a combined image@sha256:<digest> URI.
                    digest = row.get("digest", "")
                    resource = row.get("name", "")
                    if isinstance(resource, str) and "/dockerImages/" in resource:
                        from urllib.parse import unquote
                        encoded = resource.split("/dockerImages/", 1)[1]
                        suffix = unquote(encoded)
                        if suffix and not suffix.startswith("projects/"):
                            image_uri = uri + "/" + suffix
                    if isinstance(digest, str) and SHA.fullmatch(digest):
                        if isinstance(image_uri, str) and "@sha256:" not in image_uri:
                            image_uri = image_key(image_uri) + "@" + digest
                    if not isinstance(image_uri, str) or "@sha256:" not in image_uri:
                        if f"{repo_name}:image_uri_missing" not in failures:
                            failures.append(f"{repo_name}:image_uri_missing")
                        continue
                    tags = row.get("tags", [])
                    if not isinstance(tags, list):
                        tags = []
                    used = referenced(image_uri, refs, tags)
                    images.append({
                        "uri": image_uri,
                        "tags": tags,
                        "bytes": row.get("imageSizeBytes"),
                        "referenced_in_region_cloud_run": used,
                        "deletion_eligible": False,
                        "reason": ("PROTECTED_CLOUD_RUN_REFERENCE" if used
                                   else "UNREFERENCED_IN_SCOPED_CLOUD_RUN_ONLY"),
                    })
                item.update({
                    "docker_digest_count": len(images),
                    "referenced": sum(i["referenced_in_region_cloud_run"] for i in images),
                    "unreferenced_scope_only": sum(not i["referenced_in_region_cloud_run"]
                                                   for i in images),
                    "images": images,
                })
            except (RuntimeError, subprocess.TimeoutExpired):
                failures.append(f"{repo_name}:docker_images_unavailable")
                item["error"] = "ARTIFACT_REGISTRY_READBACK_NOT_VERIFIED"
        results.append(item)

    return {
        "mode": "READ_ONLY", "project": project,
        "cloud_run_scope": {"region": region, **sources, "image_references": len(refs)},
        "scope_limits": [
            "Other regions and projects not checked",
            "GCE/GKE/VM/non-Cloud-Run image consumers not checked",
            "Rollback and externally referenced image history not fully verified",
            "No image, tag, digest or repository is approved for deletion",
        ],
        "status": "PASS" if not failures else "NOT_VERIFIED",
        "failures": failures,
        "repositories": results,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--region", required=True)
    a = p.parse_args()
    result = inventory(a.project, a.region)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        sys.exit(2)


if __name__ == "__main__":
    main()
