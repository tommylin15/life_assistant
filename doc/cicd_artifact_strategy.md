# Life Assistant CI/CD Artifact Strategy

最後更新：2026-09-28

## 目的

Cloud Run release pipeline 採「一次 build、多個 runtime 共用同一個 immutable image digest」，避免 migration job、API service 與 acceptance jobs 各自重複 build Docker image。

## Release image

每次通過 CI、進入 Cloud Run deployment 時：

1. 以 `backend/` 只執行一次 Cloud Build。
2. image package 固定為 `life-assistant-backend`，tag 使用 release commit SHA。
3. 取得 build 產生的 digest，後續 deployment 一律使用 `IMAGE@sha256:...`，不以 mutable tag 作 runtime identity。
4. `life-assistant-db-migrate`、`life-assistant-api`、cloud-domain acceptance、idempotency acceptance、Google failure acceptance、SQLite backfill acceptance 與 SQLite backfill failure acceptance 全部使用同一 digest。

## Artifact retention

Artifact Registry repository 沿用 `cloud-run-source-deploy`，但 cleanup policy 僅匹配 life_assistant package prefix：

- `life-assistant-backend`
- `life-assistant-api`（舊 `--source` deployment 遺留）
- `life-assistant-db-migrate`（舊 `--source` deployment 遺留）

保留規則：

- `life-assistant-backend` 只保留最新 1 個 version。
- 舊 `life-assistant-api` / `life-assistant-db-migrate` image versions 不保留；在新 shared image release 完整通過 runtime acceptance 後才套用 cleanup policy。
- Artifact Registry cleanup 是非同步背景處理；policy 生效後實際刪除可能延後完成。

## Rollback 影響

Artifact Registry 不保留前一版 container image，因此不提供「重新部署舊 image」的 artifact-level rollback。Cloud Run 已存在的舊 revisions 仍是 runtime rollback 的第一選擇；若需要長期 artifact rollback，必須另行調整 retention count，而不能把目前 `keepCount=1` 描述成具備多版本 rollback 能力。

## 完成判定

此策略只有在下列 evidence 都成立時才算 runtime DONE：

- CI PASS。
- Cloud Build 只產生一個 release backend image。
- migration 使用該 digest 並 PASS。
- Cloud Run service 使用該 digest 並通過 health/readiness/auth checks。
- 所有 runtime acceptance jobs 使用該 digest並 PASS。
- Artifact Registry cleanup policy 成功套用。

若只有 workflow / policy 已 commit，則 implementation 可標 PASS，但 deployment/runtime 仍為 NOT VERIFIED。
