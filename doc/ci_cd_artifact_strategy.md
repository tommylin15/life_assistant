# Life Assistant CI/CD Artifact Strategy

最後更新：2026-09-28

## 目的

Cloud Run release pipeline 採「一次 build、多個 runtime 共用同一個 immutable image digest」，避免 migration job、API service 與 acceptance jobs 各自重複 build Docker image。

## Release image

每次通過 CI、進入 Cloud Run deployment 時：

1. `backend/` 只執行一次 Cloud Build。
2. image package 固定為 `life-assistant-backend`，tag 使用 release commit SHA。
3. deployment 取得 build digest，後續 runtime 一律使用 `IMAGE@sha256:...`，不以 mutable tag 作 runtime identity。
4. `life-assistant-db-migrate`、`life-assistant-api`、cloud-domain acceptance、idempotency acceptance、Google failure acceptance、SQLite backfill acceptance 與 SQLite backfill failure acceptance 全部使用同一 digest。
5. workflow 不再以 `--source backend` 分別觸發 migration / service build。

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
- acceptance job shared digest：PASS（已執行的 cloud-domain acceptance 使用相同 digest）

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
