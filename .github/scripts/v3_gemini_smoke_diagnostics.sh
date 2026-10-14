#!/usr/bin/env bash
# Scoped, read-only diagnostics for synthetic Life->Gemini smoke failures.
# Never echo unfiltered Cloud Logging entries or application payloads.
set -uo pipefail
JOB="${1:-}"
if [[ "$JOB" != "life-assistant-core-acceptance" ]]; then
  echo "gemini_smoke_diagnostics=NOT_VERIFIED unexpected_job"
  exit 0
fi
EXECUTION="$(gcloud run jobs executions list --job "$JOB"   --project "$GCP_PROJECT_ID" --region "$GCP_REGION"   --sort-by='~metadata.creationTimestamp' --limit=1   --format='value(metadata.name)' 2>/dev/null || true)"
if [[ ! "$EXECUTION" =~ ^life-assistant-core-acceptance-[a-z0-9]+$ ]]; then
  echo "gemini_smoke_diagnostics=NOT_VERIFIED execution_lookup"
  exit 0
fi
echo "gemini_smoke_execution=$EXECUTION"
TASK="$(gcloud run jobs executions tasks list --execution "$EXECUTION"   --project "$GCP_PROJECT_ID" --region "$GCP_REGION" --limit=1   --format='value(metadata.name)' 2>/dev/null || true)"
if [[ -n "$TASK" ]]; then
  EXIT="$(gcloud run jobs executions tasks describe "$TASK"     --project "$GCP_PROJECT_ID" --region "$GCP_REGION"     --format='value(status.lastAttemptResult.exitCode)' 2>/dev/null || true)"
  if [[ "$EXIT" =~ ^[0-9]+$ ]]; then
    echo "gemini_smoke_task_exit=$EXIT"
  fi
fi
RAW="$(gcloud logging read   'resource.type="cloud_run_job" AND resource.labels.job_name="life-assistant-core-acceptance" AND textPayload:"life_gateway_signed_smoke"'   --project "$GCP_PROJECT_ID" --freshness=8m --limit=30 --order=desc   --format='value(textPayload)' 2>/dev/null || true)"
CODE="$(printf '%s\n' "$RAW" | grep -Eo 'life_gateway_signed_smoke=(FAIL|PASS)( reason=[a-z_]+)?' | head -n 1 || true)"
if [[ -n "$CODE" ]]; then
  echo "$CODE"
else
  echo "gemini_smoke_diagnostics=NOT_VERIFIED sanitized_reason_unavailable"
fi
