#!/usr/bin/env bash
set -uo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 JOB_NAME COMMAND [ARG ...]" >&2
  exit 64
fi

JOB_NAME="$1"
shift

HEARTBEAT_SECONDS="${RUN_JOB_HEARTBEAT_SECONDS:-30}"
MAX_WAIT_SECONDS="${RUN_JOB_MAX_WAIT_SECONDS:-660}"

start_epoch="$(date +%s)"
set +e
timeout --signal=TERM --kill-after=15s "$MAX_WAIT_SECONDS" "$@" &
COMMAND_PID=$!

(
  while kill -0 "$COMMAND_PID" 2>/dev/null; do
    now="$(date +%s)"
    elapsed=$((now - start_epoch))
    echo "cloud_run_job_wait=HEARTBEAT job=$JOB_NAME elapsed_seconds=$elapsed max_wait_seconds=$MAX_WAIT_SECONDS"
    sleep "$HEARTBEAT_SECONDS"
  done
) &
HEARTBEAT_PID=$!

wait "$COMMAND_PID"
COMMAND_EXIT=$?
kill "$HEARTBEAT_PID" 2>/dev/null || true
wait "$HEARTBEAT_PID" 2>/dev/null || true
set -e

if [ "$COMMAND_EXIT" -eq 0 ]; then
  echo "cloud_run_job_wait=PASS job=$JOB_NAME"
  exit 0
fi

if [ "$COMMAND_EXIT" -eq 124 ] || [ "$COMMAND_EXIT" -eq 137 ]; then
  echo "::error::cloud_run_job_wait=TIMEOUT job=$JOB_NAME max_wait_seconds=$MAX_WAIT_SECONDS"
else
  echo "::error::cloud_run_job_wait=FAIL job=$JOB_NAME command_exit=$COMMAND_EXIT"
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
    # Cloud Run task exit code is in the Executions API and needs no
    # Cloud Logging Viewer. Distinguish owner absence from a broken verifier
    # only for this particular canary module; do not infer all job exit 20s.
    if [[ " $* " == *"scripts.verify_staging_google_e2e"* ]]; then
      case "$TASK_EXIT" in
        20)
          echo "::error::staging_oauth_e2e=NOT_VERIFIED reason=missing_owner_callback_session (Cloud Run task exit=20)"
          echo "staging_oauth_e2e=NOT_VERIFIED reason=missing_owner_callback_session" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
          ;;
        21)
          echo "::error::staging_oauth_e2e=FAIL reason=verifier_runtime_error (Cloud Run task exit=21)"
          echo "staging_oauth_e2e=FAIL reason=verifier_runtime_error" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
          ;;
        *)
          echo "::error::staging_oauth_e2e=NOT_VERIFIED reason=unclassified_job_failure exit=${TASK_EXIT:-unknown}"
          ;;
      esac
    fi
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
