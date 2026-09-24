#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0593591102}"
ZONE="${GCP_ZONE:-us-central1-a}"
VM="${POSTGRES_VM:-janus-postgres-dev}"
DB_NAME="${DATABASE_NAME:-life_assistant}"
DB_USER="${DATABASE_USER:-life_assistant_user}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

require_cmd gcloud
require_cmd python3
require_cmd base64

# This script is intentionally read-only. It never changes PostgreSQL, Secret
# Manager, IAM, or Cloud Run. Secret payloads are never printed. Candidate
# values exist only in process memory long enough to attempt SELECT 1.
mapfile -t SECRET_NAMES < <(
  gcloud secrets list \
    --project="$PROJECT_ID" \
    --format='value(name)' \
  | grep -Ei 'life[-_]?assistant|lifeassistant' \
  | sort -u \
  || true
)

echo "project=${PROJECT_ID}"
echo "postgres_vm=${VM}"
echo "database=${DB_NAME}"
echo "database_user=${DB_USER}"
echo "candidate_secret_count=${#SECRET_NAMES[@]}"

if ((${#SECRET_NAMES[@]} == 0)); then
  echo "matching_auth_secret=none"
  echo "diagnosis_complete=true"
  exit 0
fi

matches=()

for secret_name in "${SECRET_NAMES[@]}"; do
  if ! raw="$(gcloud secrets versions access latest \
    --project="$PROJECT_ID" \
    --secret="$secret_name" 2>/dev/null)"; then
    echo "secret=${secret_name} format=unreadable auth=SKIP"
    continue
  fi

  # Extract at most one plausible database password without ever displaying it.
  # Supported shapes: opaque single-line password, JSON object password key,
  # dotenv password key, or a PostgreSQL DSN containing a password.
  mapfile -t parsed < <(
    printf '%s' "$raw" | python3 -c '
import base64
import json
import sys
from urllib.parse import unquote, urlsplit

raw = sys.stdin.read().strip()
fmt = "unknown"
password = None
keys = ("DATABASE_PASSWORD", "database_password", "POSTGRES_PASSWORD", "postgres_password")

try:
    obj = json.loads(raw)
except json.JSONDecodeError:
    obj = None

if isinstance(obj, dict):
    fmt = "json-object"
    for key in keys:
        value = obj.get(key)
        if isinstance(value, str) and value:
            password = value
            break
elif raw.startswith(("postgresql://", "postgresql+asyncpg://")):
    fmt = "database-url"
    password = urlsplit(raw).password
    if password is not None:
        password = unquote(password)
elif "\n" in raw or "=" in raw:
    fmt = "dotenv-or-multiline"
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.removeprefix("export ").split("=", 1)
        if key.strip() in keys:
            candidate = value.strip()
            if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in (chr(34), chr(39)):
                candidate = candidate[1:-1]
            if candidate:
                password = candidate
                break
else:
    fmt = "opaque"
    password = raw or None

if password is not None and ("\n" in password or "\r" in password):
    password = None

print(fmt)
print(base64.b64encode(password.encode("utf-8")).decode("ascii") if password else "")
'
  )

  format="${parsed[0]:-unknown}"
  password_b64="${parsed[1]:-}"

  if [[ -z "$password_b64" ]]; then
    echo "secret=${secret_name} format=${format} auth=SKIP"
    continue
  fi

  if {
    printf '%s' "$password_b64" | base64 -d
    printf '\n'
  } | gcloud compute ssh "$VM" \
      --project="$PROJECT_ID" \
      --zone="$ZONE" \
      --tunnel-through-iap \
      --quiet \
      --command="sudo docker exec -i janus-postgres bash -ceu 'IFS= read -r PGPASSWORD; export PGPASSWORD; psql -U \"$DB_USER\" -d \"$DB_NAME\" -Atqc \"SELECT 1\" >/dev/null'" \
      >/dev/null 2>&1; then
    echo "secret=${secret_name} format=${format} auth=PASS"
    matches+=("$secret_name")
  else
    echo "secret=${secret_name} format=${format} auth=FAIL"
  fi

done

if ((${#matches[@]} == 1)); then
  echo "matching_auth_secret=${matches[0]}"
elif ((${#matches[@]} == 0)); then
  echo "matching_auth_secret=none"
else
  echo "matching_auth_secret=multiple"
fi

echo "diagnosis_complete=true"
