#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="gen-lang-client-0593591102"
DEPLOY_SA="life-assistant-github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "ERROR: gcloud is required." >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "ERROR: no active gcloud account. Run this from authenticated Google Cloud Shell." >&2
  exit 1
fi

echo "Using gcloud account: ${ACTIVE_ACCOUNT}"
echo "Granting Firebase Hosting Admin to: ${DEPLOY_SA}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/firebasehosting.admin" \
  --condition=None \
  --quiet

echo "Verifying binding..."
gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten='bindings[].members' \
  --filter="bindings.role:roles/firebasehosting.admin AND bindings.members:serviceAccount:${DEPLOY_SA}" \
  --format='table(bindings.role,bindings.members)'

echo "Firebase Hosting IAM bootstrap complete."
