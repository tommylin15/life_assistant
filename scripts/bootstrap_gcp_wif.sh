#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="gen-lang-client-0593591102"
REGION="us-central1"
CLOUD_RUN_SERVICE="life-assistant-api"
SECRET_NAME="life-assistant-bundle"

POOL_ID="github-actions"
PROVIDER_ID="life-assistant-main"
DEPLOY_SA_NAME="life-assistant-github-deployer"
DEPLOY_SA="${DEPLOY_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

GITHUB_REPO="tommylin15/life_assistant"
GITHUB_OWNER_ID="12059503"
GITHUB_REPO_ID="1378198937"
GITHUB_BRANCH_REF="refs/heads/main"
GITHUB_ENVIRONMENT="dev-test"

ATTRIBUTE_MAPPING="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.repository_owner_id=assertion.repository_owner_id,attribute.ref=assertion.ref"
ATTRIBUTE_CONDITION="assertion.repository_owner_id == '${GITHUB_OWNER_ID}' && assertion.repository_id == '${GITHUB_REPO_ID}' && assertion.ref == '${GITHUB_BRANCH_REF}'"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 1
  }
}

require_cmd gcloud

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n 1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "ERROR: no active gcloud account. Run this from authenticated Google Cloud Shell." >&2
  exit 1
fi

echo "Using gcloud account: ${ACTIVE_ACCOUNT}"
echo "Target project: ${PROJECT_ID}"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
if [[ -z "${PROJECT_NUMBER}" ]]; then
  echo "ERROR: unable to resolve project number for ${PROJECT_ID}" >&2
  exit 1
fi

# Workload Identity Federation prerequisites documented by Google Cloud.
gcloud services enable \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  --project="${PROJECT_ID}" \
  --quiet

if ! gcloud iam service-accounts describe "${DEPLOY_SA}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${DEPLOY_SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="life_assistant GitHub Actions deployer"
fi

if ! gcloud iam workload-identity-pools describe "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions"
fi

POOL_NAME="$(gcloud iam workload-identity-pools describe "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format='value(name)')"

if gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers update-oidc "${PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="life_assistant main" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="${ATTRIBUTE_MAPPING}" \
    --attribute-condition="${ATTRIBUTE_CONDITION}"
else
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="life_assistant main" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="${ATTRIBUTE_MAPPING}" \
    --attribute-condition="${ATTRIBUTE_CONDITION}"
fi

WIF_MEMBER="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository_id/${GITHUB_REPO_ID}"

gcloud iam service-accounts add-iam-policy-binding "${DEPLOY_SA}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="${WIF_MEMBER}" \
  --quiet

# Minimum deployer roles for `gcloud run deploy --source`.
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/run.sourceDeveloper" \
  --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/serviceusage.serviceUsageConsumer" \
  --quiet

# Reuse the service identity already attached to Cloud Run. Fall back to the
# Compute Engine default service account only if the service has no explicit SA.
RUNTIME_SA="$(gcloud run services describe "${CLOUD_RUN_SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(spec.template.spec.serviceAccountName)' 2>/dev/null || true)"

if [[ -z "${RUNTIME_SA}" ]]; then
  RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "Cloud Run runtime service account: ${RUNTIME_SA}"

gcloud iam service-accounts add-iam-policy-binding "${RUNTIME_SA}" \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet

# Cloud Run source deploy uses a Cloud Build service account. Prefer the
# project-reported default and fall back to Compute Engine default SA.
BUILD_SA="$(gcloud builds get-default-service-account \
  --project="${PROJECT_ID}" 2>/dev/null || true)"
if [[ -z "${BUILD_SA}" ]]; then
  BUILD_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "Cloud Build service account: ${BUILD_SA}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${BUILD_SA}" \
  --role="roles/run.builder" \
  --quiet

# Cloud Run validates that its runtime identity can access referenced secrets.
if gcloud secrets describe "${SECRET_NAME}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
    --project="${PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet
else
  echo "WARNING: Secret ${SECRET_NAME} was not found; secretAccessor was not changed." >&2
fi

WIF_PROVIDER="$(gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --format='value(name)')"

# Do not create or export long-lived service-account keys. Report any existing
# user-managed keys so they can be reviewed separately rather than deleting them.
USER_KEY_COUNT="$(gcloud iam service-accounts keys list \
  --iam-account="${DEPLOY_SA}" \
  --project="${PROJECT_ID}" \
  --filter='keyType=USER_MANAGED' \
  --format='value(name)' | wc -l | tr -d ' ')"
if [[ "${USER_KEY_COUNT}" != "0" ]]; then
  echo "WARNING: deploy SA has ${USER_KEY_COUNT} user-managed key(s); this script did not delete them." >&2
fi

echo
echo "WIF bootstrap complete."
echo "GCP_WORKLOAD_IDENTITY_PROVIDER=${WIF_PROVIDER}"
echo "GCP_DEPLOY_SERVICE_ACCOUNT=${DEPLOY_SA}"
echo

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is authenticated; writing environment secrets to ${GITHUB_REPO}/${GITHUB_ENVIRONMENT}."
  printf '%s' "${WIF_PROVIDER}" | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER \
    --repo "${GITHUB_REPO}" --env "${GITHUB_ENVIRONMENT}"
  printf '%s' "${DEPLOY_SA}" | gh secret set GCP_DEPLOY_SERVICE_ACCOUNT \
    --repo "${GITHUB_REPO}" --env "${GITHUB_ENVIRONMENT}"
  echo "GitHub environment secrets updated."
else
  echo "GitHub CLI is not authenticated. Set the two values printed above as"
  echo "environment secrets under GitHub environment: ${GITHUB_ENVIRONMENT}"
fi
