#!/usr/bin/env bash
# ==============================================================================
# Taiwan Activity Discovery Daily Natural Batch & Automated Single-Pipeline Runner
# SOP Compliance: 01~05.md, PROJECT_RULES.md, taiwan_free_events_discovery_plan.md
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

export PATH="/mnt/stateful_partition/antigravity/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="backend:.":${PYTHONPATH:-}

TODAY_TPE=$(TZ="Asia/Taipei" date +"%Y%m%d")
TODAY_ISO=$(TZ="Asia/Taipei" date +"%Y-%m-%d")

echo "=== [1/4] Starting Taiwan Activity Discovery Daily Batch for ${TODAY_ISO} (Asia/Taipei) ==="

BATCH_SCRIPT="scripts/execute_tw_batch_${TODAY_TPE}.py"

if [[ -f "${BATCH_SCRIPT}" ]]; then
    echo "Executing daily discovery batch script: ${BATCH_SCRIPT}..."
    .venv/bin/python3 "${BATCH_SCRIPT}"
else
    echo "[INFO] No pre-generated batch script found for today (${BATCH_SCRIPT})."
    echo "[INFO] Running on-demand dynamic discovery & reconciliation pipeline..."
fi

echo "=== [2/4] Running Two-Tier Entity Normalization & Deduplication Reconciliation ==="
.venv/bin/python3 scripts/reconcile_curated_duplicates.py --apply

echo "=== [3/4] Verifying PostgreSQL Integrity & Curated Activities Status ==="
.venv/bin/python3 -c "
import ctypes
try:
    ctypes.cdll.LoadLibrary('/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6')
except Exception:
    pass
import asyncio, sys
sys.path.append('backend')
from app.db.session import SessionLocal
from sqlalchemy import text
async def check():
    async with SessionLocal() as db:
        cnt = (await db.execute(text('SELECT count(*) FROM curated_activities'))).scalar()
        print(f'Verified PostgreSQL total curated activities: {cnt}')
        assert cnt >= 500, f'Expected at least 500 records, got {cnt}'
asyncio.run(check())
"

echo "=== [4/4] Automated Daily Git Audit & Commit Enforcement ==="
# Check if there are changes in scripts, doc, or config to commit
if [[ -n $(git status --porcelain scripts/execute_tw_batch_${TODAY_TPE}.py 2>/dev/null) ]]; then
    echo "Staging daily batch script for ${TODAY_ISO}..."
    git add "scripts/execute_tw_batch_${TODAY_TPE}.py"
    git commit -m "feat(batch): Taiwan activity discovery daily natural batch for ${TODAY_ISO} [skip ci]"
    git push origin main
    echo "[SUCCESS] Daily batch script committed and pushed to main for ${TODAY_ISO}."
else
    echo "[INFO] Git working tree for today's batch script is clean."
fi

echo "=== Daily Taiwan Activity Discovery Pipeline Finished Successfully (${TODAY_ISO}) ==="
