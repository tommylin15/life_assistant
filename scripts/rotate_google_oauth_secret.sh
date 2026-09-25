#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0593591102}"
SECRET_NAME="${LIFE_ASSISTANT_SECRET_NAME:-life-assistant-bundle}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

require_cmd gcloud
require_cmd python3

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "$ACTIVE_ACCOUNT" ]]; then
  echo "ERROR: no active gcloud account. Run this from authenticated Google Cloud Shell." >&2
  exit 1
fi

if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "ERROR: Secret Manager secret not found: $SECRET_NAME" >&2
  exit 1
fi

TMPDIR_ROTATE="$(mktemp -d)"
chmod 700 "$TMPDIR_ROTATE"
trap 'rm -rf "$TMPDIR_ROTATE"' EXIT
CURRENT_FILE="$TMPDIR_ROTATE/current"
NEW_SECRET_FILE="$TMPDIR_ROTATE/new-oauth-secret"
UPDATED_FILE="$TMPDIR_ROTATE/updated"
chmod 600 "$CURRENT_FILE" "$NEW_SECRET_FILE" "$UPDATED_FILE"

CURRENT_VERSION="$(gcloud secrets versions list "$SECRET_NAME" \
  --project="$PROJECT_ID" \
  --filter='state=ENABLED' \
  --sort-by='~createTime' \
  --limit=1 \
  --format='value(name)')"

if [[ -z "$CURRENT_VERSION" ]]; then
  echo "ERROR: no enabled version found for $SECRET_NAME" >&2
  exit 1
fi

gcloud secrets versions access latest \
  --project="$PROJECT_ID" \
  --secret="$SECRET_NAME" \
  >"$CURRENT_FILE"

printf 'New Google OAuth client secret (input hidden): ' >&2
IFS= read -r -s NEW_OAUTH_SECRET
printf '\n' >&2
if [[ -z "$NEW_OAUTH_SECRET" ]]; then
  echo "ERROR: client secret must not be empty." >&2
  exit 1
fi
printf '%s' "$NEW_OAUTH_SECRET" >"$NEW_SECRET_FILE"
unset NEW_OAUTH_SECRET

python3 - "$CURRENT_FILE" "$NEW_SECRET_FILE" "$UPDATED_FILE" <<'PY'
import json
import re
import sys
from pathlib import Path

current_path, secret_path, output_path = map(Path, sys.argv[1:])
raw = current_path.read_text(encoding="utf-8")
new_secret = secret_path.read_text(encoding="utf-8")
if not new_secret or "\n" in new_secret or "\r" in new_secret:
    raise SystemExit("ERROR: OAuth client secret is empty or contains a newline.")


def norm(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(".", "_")

# Preferred production shape: JSON object. Preserve every unrelated value and
# replace exactly one GOOGLE_CLIENT_SECRET field, or add the top-level field if
# the bundle does not yet contain one.
try:
    obj = json.loads(raw)
except json.JSONDecodeError:
    obj = None

if isinstance(obj, dict):
    matches = []

    def walk(value, path=()):
        if not isinstance(value, dict):
            return
        for key, item in value.items():
            child = path + (key,)
            if isinstance(key, str) and norm(key) == "google_client_secret":
                matches.append((value, key, child))
            if isinstance(item, dict):
                walk(item, child)

    walk(obj)
    if len(matches) > 1:
        paths = [".".join(path) for _, _, path in matches]
        raise SystemExit(
            "ERROR: multiple GOOGLE_CLIENT_SECRET fields found; refusing ambiguous rotation: "
            + ", ".join(paths)
        )
    if matches:
        parent, key, _ = matches[0]
        parent[key] = new_secret
    else:
        obj["GOOGLE_CLIENT_SECRET"] = new_secret
    output_path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print("bundle_format=json-object")
    print("oauth_secret_update=prepared")
    raise SystemExit(0)

# Also support a conventional dotenv / multiline bundle without exposing any
# payload values. Preserve all unrelated lines exactly.
pattern = re.compile(
    r"^(\s*(?:export\s+)?GOOGLE_CLIENT_SECRET\s*=).*$",
    re.IGNORECASE | re.MULTILINE,
)
matches = list(pattern.finditer(raw))
if len(matches) > 1:
    raise SystemExit("ERROR: multiple GOOGLE_CLIENT_SECRET dotenv entries found; refusing ambiguous rotation.")
if matches or "\n" in raw:
    encoded = json.dumps(new_secret)
    if matches:
        updated = pattern.sub(lambda match: match.group(1) + encoded, raw, count=1)
    else:
        suffix = "" if not raw or raw.endswith("\n") else "\n"
        updated = raw + suffix + "GOOGLE_CLIENT_SECRET=" + encoded + "\n"
    output_path.write_text(updated, encoding="utf-8")
    print("bundle_format=dotenv-or-multiline")
    print("oauth_secret_update=prepared")
    raise SystemExit(0)

raise SystemExit(
    "ERROR: unsupported life-assistant-bundle format. No Secret Manager version was changed."
)
PY

NEW_VERSION_RESOURCE="$(gcloud secrets versions add "$SECRET_NAME" \
  --project="$PROJECT_ID" \
  --data-file="$UPDATED_FILE" \
  --format='value(name)')"

if [[ -z "$NEW_VERSION_RESOURCE" ]]; then
  echo "ERROR: Secret Manager did not return a new version resource." >&2
  exit 1
fi

NEW_VERSION="${NEW_VERSION_RESOURCE##*/}"

echo "project=$PROJECT_ID"
echo "secret=$SECRET_NAME"
echo "previous_enabled_latest_version=$CURRENT_VERSION"
echo "new_version=$NEW_VERSION"
echo "oauth_secret_rotation=PASS"
echo "old_secret_version_retained=true"
echo "Next: redeploy life-assistant-api so the new secret is loaded, then retry Google login."
