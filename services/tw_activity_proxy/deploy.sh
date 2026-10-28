#!/usr/bin/env bash
set -euo pipefail

# Deployment script for Taiwan Activity Proxy on Cloud Run in asia-east1
PROJECT_ID="${GCP_PROJECT_ID:-gen-lang-client-0593591102}"
REGION="${GCP_REGION:-asia-east1}"
SERVICE_NAME="tw-activity-proxy"
INVOKER_SA="postgres-vm@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Deploying ${SERVICE_NAME} to ${REGION} in project ${PROJECT_ID}..."

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --source="$(dirname "$0")" \
  --no-allow-unauthenticated \
  --timeout=120s \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=5 \
  --quiet

echo "Granting run.invoker role to VM service account: ${INVOKER_SA}..."
gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --member="serviceAccount:${INVOKER_SA}" \
  --role="roles/run.invoker" \
  --quiet || true

URL="$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')"
echo "Deployment completed successfully. Service URL: ${URL}"
