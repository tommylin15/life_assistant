#!/usr/bin/env bash
# Promote one VERIFIED, immutable staging Preview Hosting version to the
# SEPARATE staging live site. Never updates production Hosting or traffic.
# Fail closed on any missing baseline, pin evidence, or owner Google OAuth.
set -Eeuo pipefail

: "${RELEASE_SHA:?}"
: "${CANDIDATE_REVISION:?}"
: "${STAGING_HOSTING_SITE:?}"
: "${PREVIEW_URL:?}"
: "${GCP_PROJECT_ID:?}"
: "${GCP_REGION:?}"
: "${CLOUD_RUN_SERVICE:?}"
: "${CORE_ACCEPTANCE_JOB:?}"

if [[ ! "${RELEASE_SHA}" =~ ^[a-f0-9]{40}$ ]] ||
   [[ ! "${CANDIDATE_REVISION}" =~ ^life-assistant-api-[A-Za-z0-9-]+$ ]] ||
   [[ "${STAGING_HOSTING_SITE}" != "life-assistant-v3-stage-tl15" ]] ||
   [[ "${GCP_PROJECT_ID}" != "gen-lang-client-0593591102" ]]; then
  echo "staging_preflight=FAIL invalid release identity/site" >&2
  exit 1
fi

STAGE_URL="https://${STAGING_HOSTING_SITE}.web.app"
BASE="https://firebasehosting.googleapis.com/v1beta1/sites/${STAGING_HOSTING_SITE}"
CHANNEL="v3-${RELEASE_SHA:0:10}"
WORK="$(mktemp -d)"
TOKEN="$(gcloud auth print-access-token)"
ATTEMPTED=0
BASELINE=""
PREVIEW_VERSION=""
PHASE="preflight"

hosting_get() {
  curl --fail --silent --show-error --retry 2 \
    -H "Authorization: Bearer ${TOKEN}" "$1" > "$2"
}
hosting_post() {
  local version="$1"
  curl --fail --silent --show-error \
    -X POST -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    --data '{"message":"Verified life_assistant V3 staging release"}' \
    "${BASE}/releases?versionName=${version}" > "$2"
}
release_version() {
  python - "$1" "$2" <<'PY'
import json,sys
sys.path.insert(0, ".github/scripts")
from v3_staging_gate import release_version
print(release_version(json.load(open(sys.argv[1])), "life-assistant-v3-stage-tl15", sys.argv[2]))
PY
}
version_get() {
  local version="$1"
  [[ "$version" == "sites/${STAGING_HOSTING_SITE}/versions/"* ]]
  hosting_get "https://firebasehosting.googleapis.com/v1beta1/${version}" "$2"
}
snapshot_cloud() {
  gcloud run services describe "${CLOUD_RUN_SERVICE}" \
    --project "${GCP_PROJECT_ID}" --region "${GCP_REGION}" \
    --format=json > "$1"
}
live_snapshot() {
  hosting_get "${BASE}/releases?pageSize=20" "$1"
}
verify_live() {
  local expected="$1" expected_sha="$2" expected_revision="$3"
  live_snapshot "${WORK}/stage-after-releases.json" || return 1
  local current
  current="$(release_version "${WORK}/stage-after-releases.json" live)" || return 1
  if [[ "$current" != "$expected" ]]; then
    echo "staging_live_readback=FAIL layer=hosting_version" >&2
    return 1
  fi
  version_get "$current" "${WORK}/stage-after-version.json" || return 1
  snapshot_cloud "${WORK}/cloud-after.json" || return 1
  local visible
  visible="$(curl --fail --silent --show-error -H 'Cache-Control: no-cache' "${STAGE_URL}/release.txt")" || return 1
  if [[ "$visible" != "$expected_sha" ]]; then
    echo "staging_live_readback=RETRY layer=static_sha" >&2
    return 1
  fi
  echo "staging_live_readback=PASS layer=hosting_version_and_static_sha"
  python - "${WORK}/stage-after-version.json" "${WORK}/cloud-after.json" "${expected_revision}" <<'PY' || { echo "staging_live_readback=FAIL layer=pinned_routes" >&2; return 1; }
import json,sys
sys.path.insert(0, ".github/scripts")
from v3_staging_gate import pinned_routes
version=json.load(open(sys.argv[1]))
cloud=json.load(open(sys.argv[2]))
routes=pinned_routes(version, cloud, sys.argv[3] if sys.argv[3] else None)
assert set(routes)=={"/api/**","/auth/**"}
PY
  local api_http
  api_http="$(curl -sS -o /dev/null -w '%{http_code}' "${STAGE_URL}/api/v1/tasks" || true)"
  if [[ "$api_http" != 401 ]]; then
    echo "staging_live_readback=FAIL layer=api_401 status=$api_http" >&2
    return 1
  fi
  echo "staging_live_readback=PASS layer=pins_and_api_401"
}
# Firebase live REST version may update before the CDN serves the new SHA.
# Retry boundedly without relaxing exact SHA, pinned rewrite or API auth gates.
verify_live_bounded() {
  local n
  for ((n=1;n<=24;n++)); do
    if verify_live "$@"; then
      echo "staging_live_ready=PASS attempt=$n"
      return 0
    fi
    echo "staging_live_ready=RETRY attempt=$n" >&2
    if ((n<24)); then sleep 5; fi
  done
  echo "staging_live_ready=FAIL bounded_24_attempts" >&2
  return 1
}
restore_stage() {
  live_snapshot "${WORK}/rollback-before.json" || return 1
  local current
  current="$(release_version "${WORK}/rollback-before.json" live)" || return 1
  if [[ "$current" == "$BASELINE" ]]; then
    echo "staging_rollback=NOT_NEEDED previous_version_unchanged"
    return 0
  fi
  if [[ "$current" != "$PREVIEW_VERSION" ]]; then
    echo "staging_rollback=FAIL concurrent_or_unknown_live_version" >&2
    return 1
  fi
  hosting_post "$BASELINE" "${WORK}/rollback-response.json" || return 1
  local previous_sha
  previous_sha="$(cat "${WORK}/prior-live-sha")"
  verify_live_bounded "$BASELINE" "$previous_sha" "" || return 1
  echo "staging_rollback=PASS restored_version=${BASELINE}"
}
cleanup() {
  local status=$?
  trap - EXIT
  if ((status != 0)); then
    echo "staging_release=FAIL phase=${PHASE}" >&2
  fi
  if ((status != 0)) && ((ATTEMPTED == 1)); then
    if ! restore_stage; then
      echo "staging_rollback=FAIL manual_review_required" >&2
    fi
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT

# Read-only snapshot before making any staging live change. A missing baseline,
# unpinned old version or missing original SHA is a hard stop.
hosting_get "${BASE}/channels/${CHANNEL}/releases?pageSize=20" "${WORK}/preview-releases.json"
live_snapshot "${WORK}/stage-before-releases.json"
PREVIEW_VERSION="$(release_version "${WORK}/preview-releases.json" "$CHANNEL")"
BASELINE="$(release_version "${WORK}/stage-before-releases.json" live)"
version_get "$PREVIEW_VERSION" "${WORK}/preview-version.json"
version_get "$BASELINE" "${WORK}/stage-before-version.json"
snapshot_cloud "${WORK}/cloud-before.json"
curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
  "${PREVIEW_URL}/release.txt" > "${WORK}/preview-sha"
curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
  "${STAGE_URL}/release.txt" > "${WORK}/prior-live-sha"

python .github/scripts/v3_staging_gate.py \
  --preview-releases "${WORK}/preview-releases.json" \
  --preview-version "${WORK}/preview-version.json" \
  --stage-releases "${WORK}/stage-before-releases.json" \
  --stage-version "${WORK}/stage-before-version.json" \
  --cloud-run "${WORK}/cloud-before.json" \
  --sha "$RELEASE_SHA" --revision "$CANDIDATE_REVISION" \
  --preview-sha "$(cat "${WORK}/preview-sha")" \
  --stage-sha "$(cat "${WORK}/prior-live-sha")" \
  > "${WORK}/preflight.json"
echo "staging_preflight=PASS preview_version=${PREVIEW_VERSION} previous_version=${BASELINE}"
if [[ "${1:-}" == "--preflight-only" ]]; then
  exit 0
fi
if [[ "${1:-}" != "" ]]; then
  echo "staging=FAIL unknown option" >&2
  exit 1
fi

# Capture BEFORE live mutation: only a genuine owner OAuth callback/session pair
# on THIS exact candidate revision, recorded after this timestamp, may approve it.
CANARY_START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ATTEMPTED=1
PHASE="staging_version_publish"
hosting_post "$PREVIEW_VERSION" "${WORK}/staging-release.json"
python - "${WORK}/staging-release.json" "$PREVIEW_VERSION" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
assert data.get("version",{}).get("name")==sys.argv[2], "staging release version mismatch"
PY
PHASE="staging_live_readback"
verify_live_bounded "$PREVIEW_VERSION" "$RELEASE_SHA" "$CANDIDATE_REVISION"
PHASE="staging_google_redirect"
curl -sS -D "${WORK}/stage-oauth-headers" -o /dev/null "${STAGE_URL}/auth/staging/login"
if ! grep -Eiq '^location: https://accounts[.]google[.]com/o/oauth2/' "${WORK}/stage-oauth-headers"; then
  echo "staging_google_redirect=FAIL not_google" >&2
  exit 1
fi
if ! grep -Fq 'redirect_uri=https%3A%2F%2Flife-assistant-v3-stage-tl15.web.app%2Fauth%2Fcallback' \
  "${WORK}/stage-oauth-headers"; then
  echo "staging_google_redirect=FAIL wrong_callback" >&2
  exit 1
fi
echo "staging_google_redirect=PASS fixed_staging_callback"
PHASE="owner_google_auth"
echo "staging_oauth_canary=ACTIVE url=${STAGE_URL}/auth/staging/login" | tee -a "$GITHUB_STEP_SUMMARY"

# This job reads only authenticated owner callback + session evidence. No fake
# login and no bypass if the owner cannot complete Google OAuth on staging.
.github/scripts/run_cloud_run_job_with_diagnostics.sh "$CORE_ACCEPTANCE_JOB" \
  gcloud run jobs execute "$CORE_ACCEPTANCE_JOB" \
  --project "$GCP_PROJECT_ID" --region "$GCP_REGION" \
  --args="-m,scripts.verify_staging_google_e2e,$CANDIDATE_REVISION,$CANARY_START_UTC" \
  --task-timeout 10m --wait --quiet

PHASE="production_traffic_unchanged"
# No production traffic changed during staged live testing.
snapshot_cloud "${WORK}/cloud-final.json"
python - "${WORK}/cloud-before.json" "${WORK}/cloud-final.json" <<'PY'
import json,sys
sys.path.insert(0, ".github/scripts")
from v3_staging_gate import protected_traffic
before=protected_traffic(json.load(open(sys.argv[1])))
after=protected_traffic(json.load(open(sys.argv[2])))
assert before==after, "production Cloud Run traffic changed during staging"
PY

echo "staging_live=PASS sha=$RELEASE_SHA version=$PREVIEW_VERSION oauth=PASS traffic_unchanged=true"
echo "staging_live=PASS sha=$RELEASE_SHA version=$PREVIEW_VERSION" >> "$GITHUB_STEP_SUMMARY"
