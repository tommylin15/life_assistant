# Life Assistant CI/CD Artifact Strategy

最後更新：2026-10-07

## 目的

Cloud Run release pipeline 採「一次 build、多個 runtime 共用同一個 immutable image digest」，避免 migration job、API service 與 acceptance runner 各自重複 build Docker image；runtime acceptance 則以固定少量 Cloud Run Job runner 搭配 execution-level overrides 執行，避免每一種 acceptance case 都永久佔用一個 Cloud Run Job 資源。

## Release image

每次通過 CI、進入 Cloud Run deployment 時：

1. `backend/` 只執行一次 Cloud Build。
2. image package 固定為 `life-assistant-backend`，tag 使用 release commit SHA。
3. deployment 取得 build digest，後續 runtime 一律使用 `IMAGE@sha256:...`，不以 mutable tag 作 runtime identity。
4. `life-assistant-db-migrate`、`life-assistant-api`、`life-assistant-core-acceptance` 與 `life-assistant-postdeploy-acceptance` 使用同一個 release image digest。
5. core acceptance 與 post-deploy acceptance 的個別案例不再各自 `deploy` 一個永久 Job；固定 runner 建立/更新一次後，以 `gcloud run jobs execute --args ...` 覆寫當次 execution 的 module arguments。
6. workflow 不再以 `--source backend` 分別觸發 migration / service build。

## Cloud Run Job topology

正常 CI/CD 管理的固定 Cloud Run Job 資源：

- `life-assistant-db-migrate`：資料庫 migration。
- `life-assistant-core-acceptance`：Cloud domain、Checklist、idempotency、Google failure、SQLite backfill success/failure 的共用 runner。
- `life-assistant-postdeploy-acceptance`：Notes、Project↔Drive、Drive AI enrichment 的共用 runner。

設計原則：

- acceptance case 仍保留各自獨立 Cloud Run execution、task exit code 與 logs，可繼續由 `.github/scripts/run_cloud_run_job_with_diagnostics.sh` 收集失敗證據。
- core runner 與 post-deploy runner 分開，避免 Deploy Cloud Run 與後續 acceptance workflow 互相改寫同一個 Job image/config。
- post-deploy acceptance 合併為單一 workflow 並序列執行，避免多個 workflow 同時更新同一 runner。
- 正常 deployment workflow 不執行 `gcloud run jobs delete`。舊的 feature-specific acceptance Jobs 只有在新 topology 有足夠 runtime replacement evidence 後，才可列為 legacy cleanup candidates；實際刪除 production Cloud Run 資源仍需依治理規則取得明確確認。

## Artifact retention

Artifact Registry repository 沿用 `cloud-run-source-deploy`。

`.github/artifact-registry-cleanup-policy.json` 只匹配 life_assistant package prefix：

- `life-assistant-backend`
- `life-assistant-api`（舊 `--source` deployment 遺留）
- `life-assistant-db-migrate`（舊 `--source` deployment 遺留）

保留規則：

- `life-assistant-backend` 保留最新 1 個 version。
- 舊 `life-assistant-api` / `life-assistant-db-migrate` image versions 不保留。
- cleanup step 使用 `always() && steps.backend_image.outcome == 'success'`，因此只要本次 release image build 成功，即使後續 runtime acceptance 失敗，仍會套用 retention policy。
- Artifact Registry cleanup 是非同步背景處理；policy 成功套用與舊 version 實際被刪除是兩個不同驗證點。Google Artifact Registry 文件指出 cleanup policy 由背景工作週期執行，變更通常應在約 1 天內生效，因此實體 version 數量必須另行驗證。

## Least-privilege IAM

套用 repository cleanup policy 需要 `artifactregistry.repositories.update`。

專案已建立 custom role：

`projects/gen-lang-client-0593591102/roles/lifeAssistantArtifactCleanup`

此 role 僅包含：

- `artifactregistry.repositories.update`

2026-09-28 已將此 role 綁定給既有 GitHub deployer：

`serviceAccount:life-assistant-github-deployer@gen-lang-client-0593591102.iam.gserviceaccount.com`

binding 範圍限定在 Artifact Registry repository `cloud-run-source-deploy`，未授予 Owner / Editor / Artifact Registry Admin。

## 2026-09-28 Runtime Evidence

> 本節保留當日歷史 runtime evidence；其中 acceptance Job 名稱反映當時尚未 consolidation 的 topology。

Release commit `3a6b39a8f39f9395f291e70c9eaf7a9c0280f3b2`，Deploy Cloud Run run `36384575614` attempt 2 / job `108836281621`：

- CI #293：PASS。
- Deploy Cloud Run：PARTIAL / overall FAIL，失敗來源仍是既有 authenticated cloud-domain acceptance；shared-image 與 cleanup contract 分開判定。
- Artifact Registry repository check：PASS。
- `Build backend image once`：PASS；Cloud Build ID `96b7d78f-9b88-4d63-80e6-bc01b266d6df`。
- release image digest：`sha256:34f4b194d863c080099bba4b3778ec08d4f03997abbee5e83bc75bdec4958baa`。
- migration 使用上述 digest：PASS；execution `life-assistant-db-migrate-d4fsf`。
- `life-assistant-api` 使用上述 digest 部署：PASS；revision `life-assistant-api-00080-6v7`，100% traffic。
- `/health`：PASS。
- `/ready`：PASS。
- unauthenticated API 401 protection gate：PASS。
- authenticated cloud-domain acceptance 也使用上述同一 digest，但 acceptance script FAIL；execution `life-assistant-cloud-domain-acceptance-ttqfj`。此 failure 與 shared-image / Artifact Registry cleanup contract 無直接關係。
- `Keep only the latest life_assistant image`：PASS。
- cleanup command 成功更新 repository，並回報 `Dry run is disabled`。
- active cleanup policy 已確認包含：
  - `Delete`：匹配 `life-assistant-backend`、`life-assistant-api`、`life-assistant-db-migrate`。
  - `Keep`：`life-assistant-backend` 的 `mostRecentVersions.keepCount = 1`。
- cleanup IAM authorization：PASS；先前缺少的 `artifactregistry.repositories.update` 已由 repository-scope custom role 補足。
- old image physical deletion：NOT VERIFIED；cleanup 為 Artifact Registry 非同步背景處理，目前沒有足夠 runtime inventory 證據證明舊 versions 已全部刪完。

## 完成判定

### Shared image CI/CD

- implementation：PASS
- CI：PASS
- one-build runtime：PASS
- migration shared digest：PASS
- API shared digest / health / readiness：PASS
- acceptance job shared digest：PASS（2026-09-28 已執行的 cloud-domain acceptance 使用相同 digest）

### Latest-only retention

- cleanup policy implementation：PASS
- cleanup step execution：PASS（即使 acceptance failure 仍有執行）
- cleanup IAM authorization：PASS
- cleanup policy application：PASS
- cleanup dry-run disabled：PASS
- `keepCount = 1` policy active：PASS
- old image physical deletion / current version count = 1：NOT VERIFIED

因此截至 2026-09-28，本項整體狀態仍為 **PARTIAL**，不是因為 CI/CD 設計或 cleanup policy 失敗，而是 Artifact Registry 的實體清理是非同步背景作業，尚缺「目前實際只剩最新 1 個 version」的 inventory evidence。

完成前只剩：

1. 等 Artifact Registry cleanup background job 生效。
2. 重新列出 `life-assistant-backend` versions，確認實際僅剩最新 1 個 version；若仍在 processing，維持 NOT VERIFIED，不得假設已完成。

另外，Deploy Cloud Run 目前仍有獨立的 authenticated cloud-domain acceptance failure，應另案依實際 failing assertion / exception 排查，不應混入本次 Docker image retention 完成判定。

## 2026-10-02 Cloud Run Job consolidation

本節記錄新的 Job topology 設計與 implementation intent；在對應 main commit 經 CI、deployment 與 runtime acceptance 驗證前，不把它視為 production 完成狀態。

預期固定資源由原本多個 feature-specific acceptance Jobs 收斂為：

- `life-assistant-db-migrate`
- `life-assistant-core-acceptance`
- `life-assistant-postdeploy-acceptance`

既有 feature-specific acceptance Jobs 不由本次 workflow 自動刪除。它們在新的 shared runners 完成 replacement runtime verification 後，可另列 legacy cleanup candidates；production resource deletion 仍需明確確認。


## 2026-10-06 Stuck CI / Deploy recovery hardening

本節把 `recovering-stuck-ci-deploys` 的診斷原則落到目前 GitHub Actions / Cloud Run pipeline。核心不是「卡住就重跑」，而是先判斷：

- `queued`：runner scheduling，尚未執行程式；不應因排隊直接 patch/redeploy。
- `in_progress` + Cloud Run blocking wait：silent-but-bounded；應看 Cloud Run execution 是否仍 RUNNING，並由 heartbeat 提供進度。
- 超過 hard bound 或 Cloud Run terminal failure：真正 timeout/failure；先收 diagnostics，再 fail。
- downstream workflow 未啟動 / 被 skipped / cancelled：workflow-chain / concurrency 問題，與 Cloud Run task 本身不同。

Production hardening：

- `.github/scripts/run_cloud_run_job_with_diagnostics.sh`
  - `RUN_JOB_HEARTBEAT_SECONDS` 預設 30 秒。
  - `RUN_JOB_MAX_WAIT_SECONDS` 預設 660 秒。
  - command 由 `timeout --signal=TERM --kill-after=15s` 包住。
  - 等待中輸出 `cloud_run_job_wait=HEARTBEAT`。
  - 正常完成輸出 `cloud_run_job_wait=PASS`。
  - timeout 輸出 `cloud_run_job_wait=TIMEOUT`，其他錯誤輸出 `cloud_run_job_wait=FAIL`，之後收集 Cloud Run execution/task diagnostics。
- `.github/workflows/deploy-cloud-run.yml`
  - deploy job outer bound：`timeout-minutes: 90`。
- workflow-run concurrency isolation：
  - Deploy Cloud Run / Firebase / Notes UI / Post-deploy / Drive Knowledge 的 concurrency group 帶入 upstream `workflow_run.conclusion`。
  - 目的：ineligible/skipped upstream run 不再與 valid success run 共用完全相同 group，避免錯誤 cancellation chain。

TDD / runtime evidence：

- RED contract commit：`f1014a57efa2063a20cc198fa39708dcb2fc7116`；CI #543 如預期只在 heartbeat / outer-timeout 新要求失敗。
- bounded wait implementation：`3bd8787487c4322d26d3c617aa58f4dc60a2251b`。
- deploy outer timeout：`bd47bd44164f364d266236502fe9a7b93873093e`；CI #545 PASS。
- concurrency RED：`caf63a7d759f8d881f46bdf17d7ff5250918dadf`；CI #546 FAIL。
- concurrency GREEN / production release：`8c1527ecc93709cf49eada00257183483b706eb6`；CI #547 PASS。
- Deploy Cloud Run #419 / run `37399118811`：PASS；多個 core acceptance execution 實際每 30 秒輸出 heartbeat，最後輸出 PASS。
- Firebase #365、Notes UI #130、Post-deploy #84：PASS。
- 後續 exact release `42faaff7eea3cff1550284c2effabfa5095bb497`：CI #549、Cloud Run #421、Firebase #367、Notes UI #132、Post-deploy #86 PASS；Drive Knowledge #42 仍 FAIL，但原因仍是 Task 9 external config / fixture gates。Picker app id contract 已 PASS、Picker 只剩 developer key，因此這不是 silent-wait hardening failure。

完成判定：
- implementation：PASS
- tests / CI：PASS
- deployment：PASS
- runtime heartbeat / bounded-wait evidence：PASS
- workflow-chain concurrency isolation：PASS
- Task 9 Drive Knowledge final acceptance 在上述 checkpoint 為**另案 PARTIAL / FAIL**，不可包裝為此 CI/CD hardening 的失敗，也不可反向把 CI/CD hardening PASS 說成 Task 9 DONE。

後續 Task 9 closure：release `2d08118a13c71c6fec97e8bfba0857b861eefd1e` 的 Drive Knowledge #47 / run `37568734572` final mandatory gate 已 PASS；Picker、三個 live AI provider 與真實 Drive fixture 都有獨立 PASS evidence。Task 9 現為 DONE；完整證據見 `acceptance.md`，不改變上述 CI/CD hardening 的歷史範圍。
