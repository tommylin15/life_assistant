#!/usr/bin/env bash
set -euo pipefail

# Deployment script for Taiwan Activity Proxy Cloud Function in asia-east1
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0593591102}"
REGION="${GCP_REGION:-asia-east1}"
FUNCTION_NAME="tw-activity-proxy"
INVOKER_SA="postgres-vm@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Deploying ${FUNCTION_NAME} to ${REGION} in project ${PROJECT_ID}..."

gcloud functions deploy "${FUNCTION_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --gen2 \
  --runtime=python311 \
  --entry-point=proxy_request \
  --source="$(dirname "$0")" \
  --trigger-http \
  --no-allow-unauthenticated \
  --timeout=120s \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=5

echo "Granting invoker role to VM service account: ${INVOKER_SA}..."
gcloud functions add-invoker-policy-binding "${FUNCTION_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --member="serviceAccount:${INVOKER_SA}"

echo "Deployment completed successfully."
