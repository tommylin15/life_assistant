#!/usr/bin/env bash
set -uo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 JOB_NAME COMMAND [ARG ...]" >&2
  exit 64
fi

JOB_NAME="$1"
shift

set +e
"$@"
COMMAND_EXIT=$?
set -e

if [ "$COMMAND_EXIT" -eq 0 ]; then
  exit 0
fi

echo "::error::Cloud Run job $JOB_NAME failed with exit code $COMMAND_EXIT; collecting diagnostics."

EXECUTION="$(gcloud run jobs executions list \
  --job "$JOB_NAME" \
  --project "$GCP_PROJECT_ID" \
  --region "$GCP_REGION" \
  --sort-by='~metadata.creationTimestamp' \
  --limit=1 \
  --format='value(metadata.name)' || true)"

echo "Latest $JOB_NAME execution: ${EXECUTION:-unknown}"
if [ -n "$EXECUTION" ]; then
  gcloud run jobs executions describe "$EXECUTION" \
    --project "$GCP_PROJECT_ID" \
    --region "$GCP_REGION" \
    --format='yaml(status.conditions,status.completionTime,status.failedCount,status.succeededCount)' || true

  TASK="$(gcloud run jobs executions tasks list \
    --execution "$EXECUTION" \
    --project "$GCP_PROJECT_ID" \
    --region "$GCP_REGION" \
    --limit=1 \
    --format='value(metadata.name)' || true)"
  echo "Latest $JOB_NAME task: ${TASK:-unknown}"

  if [ -n "$TASK" ]; then
    TASK_EXIT="$(gcloud run jobs executions tasks describe "$TASK" \
      --project "$GCP_PROJECT_ID" \
      --region "$GCP_REGION" \
      --format='value(status.lastAttemptResult.exitCode)' || true)"
    echo "$JOB_NAME task exit code: ${TASK_EXIT:-unknown}"
    gcloud run jobs executions tasks describe "$TASK" \
      --project "$GCP_PROJECT_ID" \
      --region "$GCP_REGION" \
      --format='yaml(status.lastAttemptResult,status.conditions)' || true
  fi
fi

gcloud logging read \
  "resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"$JOB_NAME\"" \
  --project "$GCP_PROJECT_ID" \
  --freshness=30m \
  --limit=200 \
  --order=asc \
  --format='value(timestamp,severity,textPayload,jsonPayload.message)' || true

exit "$COMMAND_EXIT"
