# 生活助理 App v0.1 — 開發進度

最後更新：2026-09-25

目前狀態：**Phase 1 主線已進入「Google integration runtime acceptance + migration + Cloud API 擴充 + Release Gate 收斂」。Flutter Web / PWA、Firebase Hosting、Cloud Run、PostgreSQL、Google Sign-In、Task CRUD、Calendar update/delete、Gmail → Task / Calendar、統一 Backend error contract 與 execution/activity log baseline 已實作並部署。真實帳號 Google integration acceptance、SQLite → PostgreSQL migration、Project/Note/Habit/Shopping/Template Cloud API 與 Bridge/MCP Release Gate 尚未完成。**

## 狀態定義

- `Implementation PASS`：目前 main 有對應程式與 contract。
- `Tests PASS`：有自動測試 evidence。
- `CI PASS`：GitHub Actions 對該 commit / workflow 通過。
- `Deployment PASS`：對應版本已成功發布。
- `Runtime PASS`：實際服務與該能力已取得 runtime evidence。
- `Integration PASS`：實際跨系統流程已驗收。
- `NOT VERIFIED`：缺必要證據；不得以程式存在推定完成。

## 2026-09-25 — 最新 evidence

### Commit / CI / deployment

- 功能 / audit baseline commit：`a6c714c488303952b36578ab45e0af7aa2df4c7a`。
- CI workflow run #152：**PASS**。
  - Backend import：PASS
  - Alembic migration validation：PASS
  - Backend unittest：PASS
  - Flutter analyze：PASS
  - Flutter tests：PASS
  - Flutter Web build：PASS
  - built branding verification：PASS
  - deployment script checks：PASS
- Cloud Run workflow run #121：**PASS**。
  - Deploy backend：PASS
  - `/health`：PASS
  - `/ready`：PASS
  - unauthenticated protected API returns 401：PASS
- Firebase Hosting workflow run #67：**PASS**。
  - Flutter Web build：PASS
  - Hosting deploy：PASS
  - Hosting verification：PASS

### Flutter Web → Backend → PostgreSQL

- Web API client 透過 Firebase Hosting / Backend API 存取 Task。
- Task list / create / update / complete / delete API 已實作。
- 使用者於 2026-09-25 完成 Google 登入與 Task CRUD 互動驗收。
- Task 核心 flow：**Implementation PASS / CI PASS / Deployment PASS / Runtime PASS（互動驗收）**。

### Backend authentication / error contract

- Google OAuth login / callback 已實作。
- 使用 `__session` HttpOnly / Secure cookie 維持已驗證 identity session。
- Task 與 Google integration API 以 `current_user` 保護。
- OAuth state validation 已實作。
- Google access / refresh token 使用 encrypted storage，支援 refresh。
- 全域 API error envelope baseline 已實作：`error.code`、`error.message`、`error.request_id`。
- response 會回傳 `X-Request-ID`；server 端未捕捉 exception 不回傳原始敏感 exception text。
- Authentication / error baseline：**Implementation PASS / CI PASS / Deployment PASS**。
- 更細的 mutation authorization / confirmation enforcement：**NOT VERIFIED / 尚未完成**。

## 2026-09-25 — Execution / Activity Log baseline

Backend 已新增 operational `execution_logs` model + Alembic migration，並提供 authenticated `/api/v1/activity` read API baseline。

目前已接 audit 的 mutation：

- Task create / update / complete / delete
- Calendar create / update / delete
- Gmail → Task
- Gmail → Calendar
- Drive Bridge ensure

行為：

- mutation 執行前先建立 `running` execution record；若 audit start 失敗，action 不執行。
- action 成功後記錄 success/result。
- action 失敗時記錄 failure/error category。
- Drive Bridge 若 root 已建立但 bridge 後續失敗，可記錄 `partial_success`。
- 若 action 可能已完成但 audit finalize 失敗，API 使用明確 `audit_finalize_failed` 類型，不包裝成 full success。

狀態：**Implementation PASS / Tests PASS / CI PASS / Deployment PASS**。真實 Google mutation + `/activity` 的 end-to-end runtime acceptance 尚待補，因此不標 `Integration PASS`。

## 2026-09-25 — Google integrations

### 已實作 / 已部署能力

Capability Catalog baseline 現包含：

- `gmail.list_metadata`
- `gmail.to_task`
- `gmail.to_calendar`
- `calendar.list`
- `calendar.create`
- `calendar.update`
- `calendar.delete`
- `drive.bridge.ensure`

Google scope baseline：

- Gmail：`gmail.readonly`
- Calendar：`calendar.events`
- Drive：`drive.file`

目前不包含 Gmail send、全 Drive scope 等高權限能力。

### Calendar

- read：Implementation PASS
- create：Implementation PASS
- update：Implementation PASS
- delete：Implementation PASS
- update 時若改時間，start / end 必須一起提供且含 timezone。
- delete capability metadata 標示 `destructive_external` + `explicit_user`；**真正的 confirmation enforcement policy 尚未完成**。

### Gmail conversion

- Gmail metadata read：Implementation PASS
- Gmail → Task：Implementation PASS
- Gmail → Calendar：Implementation PASS；start/end 必須由 request 明確提供，Backend 不猜測時間。
- Gmail → Project：**Blocked**，因 Cloud Backend 尚無 Project model / Project CRUD API。

### Drive

- `life_assistant/ChatGPT_Bridge` ensure：Implementation PASS
- root/bridge ensure 支援 execution log；root 已建立但後續失敗時可標示 partial success。

### 真實帳號 integration acceptance

截至本次文件同步，以下仍為 **NOT VERIFIED**：

- Gmail metadata 真實帳號 read
- Calendar 真實帳號 read/create/update/delete
- Drive Bridge 真實帳號 ensure
- Gmail → Task 真實帳號 conversion
- Gmail → Calendar 真實帳號 conversion
- 真實 Google API failure → execution/activity record 的 end-to-end evidence

API / tests / deployment PASS 不等同上述 Integration PASS。

## 目前 Cloud Backend model / API 範圍

### 已有

- Task model + Task CRUD
- ExecutionLog operational model + migration
- `/api/v1/activity` baseline
- GoogleConnection / OAuth state model
- Google auth API
- Google integration API
- unified error handlers + request ID middleware baseline
- `/health`
- `/ready` + DB connectivity evidence
- Alembic migrations

### 尚缺主要 Phase 1 Cloud API

- Project CRUD
- Note CRUD / search
- Habit
- Shopping
- Template

## CI / CD 現況

正式部署路徑：

```text
GitHub main
  → GitHub Actions CI
  → tests / build
  → Firebase Hosting + Cloud Run
  → runtime / integration validation
```

CI 已包含：

### Flutter

- branding asset validation
- `flutter pub get`
- `flutter analyze --no-fatal-infos`
- `flutter test`
- Flutter Web build
- built branding verification

### Backend

- dependency install
- FastAPI import check
- Alembic migration SQL validation
- Backend unittest suite

### Deployment script checks

- GCP WIF bootstrap script syntax
- PostgreSQL inspect / diagnostics script syntax
- OAuth secret rotation helper syntax

## SQLite / legacy native assets

舊原生 Flutter + SQLite 版本保留，包含：

- SQLite schema / migrations
- Item / Project CRUD
- Dashboard
- Notes / FTS5
- Habits
- Shopping
- Templates
- Attachments
- Calendar / Gmail adapters
- Drive / Share Bridge
- Bridge schema / idempotency / proposed-action UI
- Activity log
- App lock / PIN / biometric / sensitive log filtering

這些是 migration source / existing assets，不代表相同能力已完成 Cloud Backend / PostgreSQL 版本。

## 已知尚未完成

- Google Gmail / Calendar / Drive 真實帳號 runtime / integration acceptance 尚未完整取得 evidence。
- Google mutation audit 雖已實作與部署，但真實帳號 end-to-end audit acceptance 尚未完成。
- Project CRUD Cloud API 尚未實作，並阻塞 Gmail → Project。
- SQLite → PostgreSQL migration 尚未有 runtime evidence。
- Project / Note / Habit / Shopping / Template Cloud API 尚未完成。
- Backend destructive / sensitive confirmation enforcement 尚未完成。
- Backend idempotency contract 尚未建立於新 Cloud mutation 主線。
- ChatGPT Bridge Backend / MCP 尚未達 Phase 1 Release Gate。
- Phase 1 整體狀態仍為 **PARTIAL**。

## 下一步：Phase 1 收斂順序

1. 取得 Gmail / Calendar / Drive 真實帳號 runtime acceptance；同步驗收 Calendar create/update/delete、Gmail → Task / Calendar 與 `/activity` audit record。
2. 實作 SQLite → PostgreSQL mapping、可重跑 export/import、row count / relationship verification 與 failure evidence。
3. 建立 Project Cloud model / CRUD，接 Gmail → Project。
4. 擴充 Note / Habit / Shopping / Template Cloud API。
5. 補完整 permission / confirmation / idempotency policy。
6. 推進 ChatGPT Bridge Backend / MCP contract、policy、idempotency、audit integration。
7. 重新跑 Phase 1 acceptance / deployment / runtime / integration evidence。

Android / iOS 正式打包、release signing 與上架目前不是 Phase 1 主交付路線。

## 歷史摘要

### 2026-09-25

- Google login + Task CRUD 互動驗收 PASS。
- Calendar update/delete、Gmail → Task、Gmail → Calendar implementation 完成。
- 統一 Backend error contract + request ID 完成。
- ExecutionLog / Activity API baseline 完成，Task / Google mutations 接入 audit。
- CI #152、Cloud Run #121、Firebase Hosting #67 PASS。

### 2026-09-24

- Phase 1 採 scope freeze。
- 正式主線確立為 Firebase Hosting → Flutter Web / PWA → Cloud Run FastAPI → PostgreSQL。
- Today / Focus / Routine Library / Global Capture 等功能移到 Phase 2，不阻塞第一次平台上線。

### 2026-09-22

- Flutter Web/PWA 基礎建立。
- FastAPI Backend / Task CRUD 建立。
- PostgreSQL dev/test schema 與 Cloud Run connectivity 建立。
- GitHub Actions CI baseline 建立。

### 2026-09-21 與更早

- 原生 Flutter + SQLite 功能、Google adapters、Drive Bridge、folder sync、security baseline、Notes/FTS5、Habits、Shopping、Templates 等既有資產完成多輪實作與測試。
- 這些成果保留，但新 Web / Cloud 主線需逐項遷移與重新驗證。
