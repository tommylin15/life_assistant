#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0593591102}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
SERVICE="${CLOUD_RUN_SERVICE:-life-assistant-api}"
VM="${POSTGRES_VM:-janus-postgres-dev}"
SECRET="${LIFE_ASSISTANT_SECRET:-life-assistant-bundle}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

require_cmd gcloud
require_cmd python3

echo "project=${PROJECT_ID}"
echo "region=${REGION}"
echo "zone=${ZONE}"

VM_IP="$(gcloud compute instances describe "$VM" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --format='value(networkInterfaces[0].networkIP)')"
echo "postgres_vm=${VM}"
echo "postgres_private_ip=${VM_IP:-missing}"

echo "cloud_run_networking:"
gcloud run services describe "$SERVICE" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format=json \
| python3 -c '
import json, sys
payload = json.load(sys.stdin)
annotations = (((payload.get("spec") or {}).get("template") or {}).get("metadata") or {}).get("annotations") or {}
matched = {k: v for k, v in annotations.items() if "network" in k.lower() or "vpc" in k.lower()}
if not matched:
    print("  network_annotations=none")
else:
    for key in sorted(matched):
        print(f"  {key}={matched[key]}")
'

echo "life_assistant_bundle:"
gcloud secrets versions access latest \
  --project="$PROJECT_ID" \
  --secret="$SECRET" \
| python3 -c '
import json, sys
from urllib.parse import urlparse
raw = sys.stdin.read()
try:
    bundle = json.loads(raw)
except json.JSONDecodeError:
    print("  format=invalid-json")
    raise SystemExit(0)
if not isinstance(bundle, dict):
    print("  format=non-object")
    raise SystemExit(0)
print("  keys=" + ",".join(sorted(str(k) for k in bundle)))
value = ""
for name in ("DATABASE_URL", "database_url"):
    candidate = bundle.get(name)
    if candidate:
        value = str(candidate).strip()
        break
if not value:
    print("  database_url=missing")
else:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    target = "local" if host in {"", "localhost", "127.0.0.1", "::1"} else "remote"
    database_name = parsed.path.lstrip("/") or "missing"
    print("  database_url=" + target)
    print("  database_name=" + database_name)
    print("  database_user_present=" + str(bool(parsed.username)))
'

echo "postgres_catalog:"
gcloud compute ssh "$VM" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --tunnel-through-iap \
  --quiet \
  --command="sudo docker exec --user postgres janus-postgres psql -U postgres -d postgres -Atqc \"SELECT 'database=' || datname FROM pg_database WHERE datname LIKE 'life_assistant%'; SELECT 'role=' || rolname FROM pg_roles WHERE rolname LIKE 'life_assistant%';\"" \
  || echo "  ERROR: unable to inspect PostgreSQL catalog" >&2

echo "postgres_hba:"
gcloud compute ssh "$VM" \
  --project="$PROJECT_ID" \
  --zone="$ZONE" \
  --tunnel-through-iap \
  --quiet \
  --command="sudo docker exec janus-postgres sh -c \"grep -n -E 'life_assistant|0\\.0\\.0\\.0/0' /opt/janus/pg_hba.conf || true\"" \
  || echo "  ERROR: unable to inspect PostgreSQL HBA" >&2

echo "inspection_complete=true"
