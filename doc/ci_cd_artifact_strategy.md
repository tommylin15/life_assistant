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
- cleanup step 使用 `always() && steps.backend_image.outcome == 'success'`，因此只要本次 release image build 成功，即使後續 runtime acceptance 失敗，仍會嘗試套用 retention policy。
- Artifact Registry cleanup 是非同步背景處理；policy 成功套用與舊 version 實際被刪除是兩個不同驗證點。

## Least-privilege IAM

套用 repository cleanup policy 需要 `artifactregistry.repositories.update`。

專案已建立 custom role：

`projects/gen-lang-client-0593591102/roles/lifeAssistantArtifactCleanup`

此 role 僅包含：

- `artifactregistry.repositories.update`

不得為了 cleanup 改授 Owner / Editor / Artifact Registry Admin。正式 binding 應只授予既有 GitHub deployer，且優先綁在 `cloud-run-source-deploy` repository scope。

## 2026-09-28 Runtime Evidence

Release commit `3a6b39a8f39f9395f291e70c9eaf7a9c0280f3b2`：

- CI #293：PASS。
- Deploy Cloud Run #246：PARTIAL / overall FAIL（既有 cloud-domain acceptance failure）。
- Artifact Registry repository check：PASS。
- `Build backend image once`：PASS；Cloud Build ID `d539e3de-1b63-4b53-aeb7-c88318731275`。
- release image digest：`sha256:bfe871ebe554060291010a4d8d96a8014c4c5e40d273fdfc463403474ed4f700`。
- migration 使用上述 digest：PASS；execution `life-assistant-db-migrate-pxwps`。
- `life-assistant-api` 使用上述 digest部署：PASS；revision `life-assistant-api-00079-v26`，100% traffic。
- `/health`：PASS。
- `/ready`：PASS。
- unauthenticated API 401 protection gate：PASS。
- authenticated cloud-domain acceptance：FAIL，execution `life-assistant-cloud-domain-acceptance-k2rck`，task exit code 1；此 failure 與 shared-image build contract 分離。
- cleanup step：有執行，但 FAIL；runtime 明確回報缺少 `artifactregistry.repositories.update`。
- custom role `lifeAssistantArtifactCleanup`：已建立，僅含上述單一 permission；role binding 尚未完成。

## 完成判定

### Shared image CI/CD

- implementation：PASS
- CI：PASS
- one-build runtime：PASS
- migration shared digest：PASS
- API shared digest / health / readiness：PASS

### Latest-only retention

- cleanup policy implementation：PASS
- cleanup step execution：PASS（已證明 acceptance failure 時仍會執行）
- cleanup IAM authorization：FAIL（role 已建立但未 binding）
- cleanup policy application：FAIL
- old image physical deletion：NOT VERIFIED

因此截至 2026-09-28，本項整體狀態為 **PARTIAL**，不得標記 DONE。完成前仍需：

1. 將 `lifeAssistantArtifactCleanup` 綁給既有 GitHub deployer，優先限定 `cloud-run-source-deploy` repository。
2. 重新執行 Deploy Cloud Run，確認 `Keep only the latest life_assistant image` PASS。
3. 在 Artifact Registry cleanup 非同步處理後核對 `life-assistant-backend` 僅剩最新 1 個 version；若平台仍在 processing，標記 NOT VERIFIED，不得假設已刪除。
