# life_assistant CI/CD V3 — GitHub Actions + public GHCR + Cloud Run digest

**Decision date:** 2026-10-08  
**State (2026-10-09):** V3 promoted deployment PASS, old Cloud Build triggers 5/5 disabled PASS, scoped obsolete GCS/AR resources removed PASS; subsequent releases and end-to-end integration must be verified per run; Phase 1 overall PARTIAL.  
**Owner:** life_assistant; applies to `tommylin15/life_assistant` main.  
**Authority:** This document and the latest V3 section of `PROJECT_RULES.md` supersede the Cloud Build-led CI/CD V2 target. Earlier V2 runbooks and acceptance records remain historical evidence, not instructions to keep operating Cloud Build in the new path.

## 0. 現行生效狀態／2026-10-09 稽核註記

本檔為 V3 policy 的核准設計，以下是與 2026-10-08 舊「未實作」文字不同的 **已實際驗證**狀態：

- GitHub Actions V3 promoted release [run 37795789924](https://github.com/tommylin15/life_assistant/actions/runs/37795789924)：PASS；GHCR digest `sha256:b06254c2db22489295c2a82928ea19a6352193fd7b0c72f1041040f22bc0d7b1`。
- Cloud Run `life-assistant-api-00183-hax`：Ready/Active/ContainerHealthy/ContainerReady/ResourcesAvailable 都為 `True`；供應映像為 GHCR digest cache，而不是 user-managed AR。
- Cloud Build Triggers 五個 `disabled=true`（包含 life_assistant、Janus、OmniAgent）。觸發器未刪除定義，只停用。
- 兩個 Cloud Build GCS Buckets、`run-sources-*` Bucket 已消失（404）；舊 AR `cloud-run-source-deploy`、`janusai-poc`、`omniagent` 三個 Repository 已消失。GCP readback [run 37867249614](https://github.com/tommylin15/life_assistant/actions/runs/37867249614) **PASS**，AR 4→1 / GCS 8→5。
- **最新 AR 保存政策已由使用者修正：只保留「現役 runtime/CI deployment 確實依賴」的 Docker 映像；不以舊 Cloud Run Revision 回滾、或「最新 Digest」為獨立保存理由。** 這僅適用 user-managed AR 清理，不代表應刪除 GHCR manifest、當前容器依賴或 PostgreSQL 備份。
- `janus-postgres/postgres:16.15` 仍存一個 Digest：Cloud Run 未發現引用，但 VM/資料庫容器依賴 `NOT VERIFIED`，暫時保留；五個 `dev-*` GCS Buckets 也保留。
- 2026-10-09 清理後資產不存在已 `PASS`；原始逐 Digest/逐 object 刪除事件、成本節省、所有區域/VM/in-flight 依賴及最新 Revision 總數未逐項證實者 **不能標 PASS**。
- 規格中涉及遷移前切流順序、Bootstrap 未實作或舊資產尚未刪除的敘述屬 **當時條件與歷史要求**，不是目前實際狀態；目前實作與驗收參照 [`v3_cleanup_and_cutover_inventory.md`](v3_cleanup_and_cutover_inventory.md)。

## 1. Non-negotiable boundaries

- Main release path: `ChatGPT → GitHub main → GitHub Actions → GCP API → GitHub Actions Logs → ChatGPT`.
- GitHub Actions performs the complete test gates, Docker build and **public GHCR** publication. No new workflow invokes or submits Cloud Build builds/triggers or proactively writes to **GCS** or **Artifact Registry**. No new Artifact Registry repository, remote repository, bucket, paid VM, or long-lived GCP service-account key is introduced.
- Cloud Run is deployed only from an **exact GHCR manifest digest** (e.g. `ghcr.io/OWNER/IMAGE@sha256:...`), not a mutable tag; use a **0%-traffic tagged candidate**, prove acceptance, then explicitly promote or restore captured previous traffic assignments.
- Cloud Build remains available **only as a legacy, read-only diagnostic source**, accessed with WIF from a dedicated manual GitHub Actions workflow. Diagnostic readback is not proof of a successful new V3 build.
- Retain Firebase Hosting/Flutter Web, FastAPI/Cloud Run, PostgreSQL/Alembic, existing OAuth/integrations/Cloud Run jobs and owner-isolation gates. Avoid scheduled business-job mutations. Do not modify omniAgent or Janus.
- Any Google-controlled internal import/cache of a public image, or Firebase Hosting managed internal storage, is **not** the same as an explicit workflow write to a user-managed GCS bucket or Artifact Registry repository. Exact GCP billing remains subject to runtime/billing evidence.

## 2. Verified feasibility and preconditions

Google Cloud's Cloud Run service **and job** deployment documentation allows **direct deployment of public images from GitHub Container Registry**; a private GHCR image would require an Artifact Registry remote repository and is therefore disallowed in V3. Verify the **GHCR package** itself is public (a public repository alone does not establish package visibility). Confirm unauthenticated manifest/digest retrieval, region, amd64/OCI support, container `PORT` contract, and the actual service/job deploy readback before declaring PASS.

Reference: https://docs.cloud.google.com/run/docs/deploying  
Reference: https://docs.cloud.google.com/run/docs/create-jobs  
Reference: https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images

Public container metadata and layers are pullable by third parties. Never bake tokens, DB credentials, private fixture files or user data into build context, layers, labels, image, build args, cache, attestations or public workflow output. Perform image vulnerability/secret scanning before publication; publishing requires explicit scan PASS.

## 3. Separated GitHub Actions workflows

### A — Main/PR quality gate (automatic, no deployment)
- `push: main` and relevant PR checks: checkout exact SHA, Python unit/API/integration tests, Alembic offline/preflight and migration contracts, Flutter analyze/test/web build and branding, security/dependency/secret scanning, Dockerfile/build contract, owner/auth boundaries, and required CI contract tests.
- Produce structured job summaries and masked logs. **No** GCP mutation, GHCR publishing, Cloud Run/Firebase deployment or Cloud Build trigger in this stage.
- Missing or failed mandatory gate means FAIL; neither skipped nor cancelled is PASS. Tests may not be weakened to attain a green status.
- The actual required-test matrix and runtime are implementation tasks; nothing in this document certifies those jobs are currently active.

**One-time migration bootstrap exception (user-authorized):** The `.github/workflows/v3-initial-bootstrap.yml` push trigger is limited to edits to that workflow file alone, is gated on all three full-main-SHA CI jobs passing, and issues one exact-SHA dispatch with promotion requested to perform this initial user-authorized rollout. Production still cannot change before mandatory candidate, pinned Preview and integration gates. Subsequent routine releases remain manual exact-SHA; never broaden the bootstrap trigger to every push. The bootstrap dispatch request is not runtime deployment PASS.

### B — Immutable image publication (manual exact-SHA release)
- A `workflow_dispatch` release accepts only a complete 40-character commit SHA verified as current/authorized `main` and with passing required quality checks for that SHA. A stale/SHA-mismatched release fails closed.
- Build backend image **once on GitHub-hosted runner**, tag with full source SHA, use `GITHUB_TOKEN` with minimally scoped `packages: write`, publish to GHCR and resolve the immutable **registry manifest digest** from the push result. Preserve source SHA, image digest, GitHub run/job URL, SBOM/provenance (when implemented), and tool versions as evidence.
- Validate manifest digest format and an unauthenticated pull before proceeding. Never substitute a Docker image ID, local build hash or mutable tag for the remote digest. Guard against multi-architecture manifest/index confusion; Cloud Run consumes the deployed manifest digest.
- Use concurrency controls to serialize promotions; repeated same SHA/digest/phase is idempotent. Recheck `main` and captured live state directly before any mutation.

### C — Candidate stage (manual gated release, 0% traffic)
- Authenticate to GCP with GitHub OIDC/WIF (no downloaded persistent key), with the restricted **deployer** identity, not the diagnostic identity. Record current Cloud Run traffic percentages/revisions, active tags, service/job image digests and runtime configuration before changing anything.
- Validate backward-compatible Alembic migration plan and existing owner/data isolation before running the approved, bounded idempotent migration job. Migrations may touch live DB even if candidate gets 0%; a DB-impacting release must have separate safety approval/gates and recovery plan. No automatic destructive migration or DB downgrade.
- Deploy service revision with exact `ghcr.io/...@sha256:...`, `--no-traffic`, and a unique tagged candidate URL. **0% traffic does not mean inaccessible**: tagged URLs require the same authentication/access protection, no sensitive response exposure, and must be retired when no longer needed.
- Migration runner, API candidate and acceptance runner should use the *same* release digest where the existing topology requires it. Preserve existing runtime service account, VPC, env/secrets and job configs unless an explicit reviewed change is necessary.
- Run candidate health/readiness, 401/authorization, authenticated API, DB persistence, owner isolation, Activity/audit, migration and provider-failure/timeout contracts, with bounded retries and redacted logs. Candidate test failure halts before promotion and preserves current production traffic.

### D — Firebase Preview + release promotion

**2026-10-08 Firebase safety fix:** The Firebase CLI refuses pinning a Preview rewrite when the **same Hosting Site's live channel** has an unpinned rewrite to the same Cloud Run Service (`firebase-tools/src/deploy/hosting/prepare.ts::unsafePins`). This is a deliberate production safety protection, not missing permissions. Never deploy `pinTag: true` to the existing production Hosting live channel while an unpromoted candidate is the latest ready Cloud Run Revision: that could route production Hosting traffic to unverified code. V3 uses a distinct, non-production Hosting Site `life-assistant-v3-stage-tl15` with independent Preview channels, a runner-local `hosting.site` override and `pinTag: true` ONLY for its rewrites. Do not write the staging setting into production `firebase.json`; do not sync Firebase Auth authorized domains during staging. Stage Site creation is isolated and idempotent; unauthorized creation fails the release closed. The production `gen-lang-client-0593591102.web.app/auth/callback` remains unchanged and the staged Preview does not prove a complete interactive Google OAuth authorization round trip. Actual full Google integration must pass separately. Source: https://github.com/firebase/firebase-tools/blob/main/src/deploy/hosting/prepare.ts .


- For backend changes, create an isolated Firebase Hosting Preview targeted at the tagged candidate (pin appropriate backend route/tag); even unchanged Flutter source needs candidate-compatible browser acceptance. Never claim intercepted/mocked API UI tests demonstrate real provider integration.
- Gate desktop/mobile browser flows, auth redirect, manifest/branding, cache, API routing, and real approved integration tests. Preview PASS is not Live PASS.
- Only after all required candidate/Preview gates PASS may an explicitly authorized promotion allocate production Cloud Run traffic to the exact verified revision; record resulting live digest, revision, URL and traffic distribution. Publish verified Firebase Hosting content when relevant, then run live smoke, true-account OAuth/integration, frontend↔backend↔PostgreSQL and scheduled-resource readback gates.
- Release workflows must not alter scheduler cadence or execute unrelated production business jobs.

### E — Rollback and recovery
- Persist the **pre-promotion** immutable revision IDs, traffic percentages, Hosting release ID and SHA in GitHub run evidence before mutation. A failure during promotion requires a readback of actual traffic and Hosting release state before proceeding.
- Restore original Cloud Run traffic split precisely; restore the prior Firebase Hosting release if live web release changed; verify live readiness, 401/authorized behavior and functional/browser integration again. Rollback is an **action requiring confirmation when high-risk**; no destructive DB rollback.
- Block superseded release SHAs, overlapping promotion and ambiguous/partial state. Existing migration/schema changes may require forward-fix rather than reverting DB.
- Do not prune a digest referenced by live/candidate/rollback revisions or Jobs; do not delete existing GCP artifacts or Cloud Run resources as part of this migration.

### F — Post-acceptance Cloud Run revision retention (latest 10)

**Approved retention target:** keep the **10 most recently created Cloud Run revisions** of the existing `life-assistant-api` service, not two. This retention policy has an implemented V3 release workflow, but this documentation change does not authorize immediate revision deletion; actual per-service revision count remains subject to post-deploy readback. Keep one stable Cloud Run service and its stable URL; revision names and traffic assignments can change without modifying Google OAuth redirect URIs.

- **Ordering and timing:** after a release is promoted and the entire required **live** smoke/OAuth/integration/runtime gate set reports PASS, run an idempotent, serialized cleanup step **at the very end** of that successful release workflow. Candidate/Preview-only, failed, cancelled, partially verified and rolled-back executions **must not clean up**. A temporary 11th revision during deployment is expected.
- **Inventory:** fetch the exact project's `us-central1/life-assistant-api` service and revision list; sort revisions by server-reported creation time descending with a deterministic name tie-breaker. Compute the newest ten, review live traffic assignments, active candidate/preview/rollback tags, in-progress deployments and captured prior live traffic. Never list/delete revisions from unrelated services or jobs.
- **Fail-closed protections:** do not delete any revision with nonzero traffic, any revision explicitly retained as the verified rollback baseline, or an in-flight tagged candidate/Preview target. Also preserve any currently pinned live/rollback digest used by Cloud Run Jobs. If these protections imply **more than 10**, leave the extras and report **RETENTION PARTIAL / NOT VERIFIED**, with the exact protected names and reasons; never compromise recovery to force the count. Avoid unexpected tag removal and clean up only expired release-owned candidate tags when safe.
- **Action and readback:** delete only out-of-window, unprotected, 0%-traffic revisions of this exact service, one by one; first re-read service traffic/tags and confirm the workflow still owns the release lock. Record revision names, ages, eligible/deleted/skipped sets and reasons, post-delete service traffic, live digest, and remaining count in a redacted GitHub Actions job summary. Fail and stop on unknown state, API errors, race conditions or mismatched readback; do not turn partial cleanup into a green release-retention claim.
- **Image preservation:** GHCR digest retention is separate from Cloud Run revision cleanup. Never delete images required by the retained revisions, migration/acceptance jobs or recoverable releases; keep at least the image digests corresponding to all retained revisions and protected jobs. No cleanup logic may invoke Cloud Build or write GCS/Artifact Registry.
- **Cost boundary:** revisions with no incoming requests ordinarily scale to zero and incur no Cloud Run execution charge, **except** minimum-instance/traffic-tag/manual-scaling and other live usage configurations that may keep instances running. Revision-level minimum instances **plus** a traffic tag can incur idle instance charges even at 0% traffic. Validate service/revision scaling, tag and billing configuration; image/package storage and requests are accounted for separately. Retaining 10 rather than 2 is for rollback and forensic utility, **not a proven cost saving**.

Official references: https://docs.cloud.google.com/run/docs/managing/revisions and https://docs.cloud.google.com/run/docs/configuring/min-instances .

## 4. WIF least privilege and diagnostic log contract

Two logical permission sets must stay separate:
1. **Diagnostic reader (read only)**: GitHub OIDC/WIF provider restricted by repo, branch/ref and relevant workflow/environment claims. Cloud Build build metadata lookup: narrowly scoped `cloudbuild.builds.get` (and `list` only if discovery is required); read relevant Cloud Logging records only with `logging.logEntries.list` where approved. No `cloudbuild.builds.create`, GCS object read/write, Artifact Registry write, Cloud Run deploy or IAM administration. GCP logs stored only in GCS may not be readable under this no-GCS-read contract; in that case output `NOT AVAILABLE`, never invent failures.
2. **Release deployer**: separate trusted workflow/environment with `id-token: write`, scoped Cloud Run deployment/traffic/job permissions plus `iam.serviceAccounts.actAs` only on reviewed runtime SAs; Firebase deployment permissions via separately scoped principal where applicable. Read-only WIF is **insufficient** for deployment. Do not use project Owner/Editor or broad IAM Policy changes; validate exact roles and bindings against deployed resources.

Diagnostic GitHub Actions `workflow_dispatch` takes a validated historic Cloud Build ID, requests only GCP **metadata** via API, and returns bounded, whitelisted output:
- build ID, status (`SUCCESS`/`FAILURE`/`CANCELLED`/`TIMEOUT`/etc as actually returned), created/finished times;
- failing step ID/name and status **only when returned**, failureInfo/statusDetail if present;
- sanitized and bounded error category/summary, sources masked before GitHub logs. GitHub automatic masking alone is insufficient; never print environment, raw logs, tokens or unredacted arbitrary JSON.
- `NOT FOUND`, `PERMISSION DENIED`, `NOT VERIFIED` and `NO STEP DETAILS` are distinct evidence states. An empty step list must never be labeled PASS.

ChatGPT reads **GitHub Actions run/job logs** through its connected GitHub access. WIF authenticates Actions→GCP, not ChatGPT→GCP; successful workflow run/log readback and GCP permissions must be verified independently. No passive polling/automatic ChatGPT delivery is implied.

## 5. Implementation order and cutover criteria

1. Inventory existing `.github/workflows/`, `cloudbuild.yaml`, Cloud Build 2nd Gen triggers and IAM. Save legacy deployment/rollback evidence; **do not delete** existing GCP assets.
2. Implement Actions main/PR full test gate, GHCR public package/scans/digest publication, and the independent read-only legacy Cloud Build diagnostic workflow. Verify actual WIF trust conditions and permission enforcement.
3. Implement digest-pinned migration/job/candidate, tagged URL acceptance, Firebase Preview, traffic promotion and exact-split rollback with interlocks. Use controlled dry-run and representative failure injection.
4. Once new workflow is verified, **disable old Cloud Build push/manual release triggers** and retire legacy GitHub Actions Cloud Build submit paths, without removing past logs or artifacts. This change requires actual GCP/readback evidence and is **not performed by documentation commit**.
5. Record Actions run, source SHA, public GHCR digest/readback, WIF identity, Cloud Run revision/0% state, candidate and Preview results, promotion/rollback simulations, live runtime/integration, plus absence of new pipeline Cloud Build/GCS/Artifact Registry API writes. Cost comparison must be measured, not assumed.

**Latest verified release status (2026-10-09):** V3 deployment/production-ready service / five disabled legacy triggers / scoped legacy GCS+AR resource removal **PASS** on the run IDs in §0. A new release still requires its own tests/deployment/runtime/integration evidence; neither this documentation commit nor historical PASS closes all product Phase 1 gates. **Overall Phase 1 PARTIAL**. Historical V2 failures remain historical evidence.
