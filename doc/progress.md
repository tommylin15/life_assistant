# 生活助理 App v0.1 — 開發進度

最後更新：2026-09-25

目前狀態：**Phase 1 主線已從「基礎建置」進入「Google integrations / Cloud API 擴充與 Release Gate 收斂」。Flutter Web / PWA、Firebase Hosting、Cloud Run、PostgreSQL、Google Sign-In 與 Task CRUD 主線已建立；Google Gmail / Calendar / Drive 第一批能力已實作，但外部整合仍需 runtime acceptance。SQLite → PostgreSQL migration、execution log、完整 error contract、Project/Note/Habit/Shopping Cloud API 與 Bridge/MCP Release Gate 尚未完成。**

## 狀態定義

- `Implementation PASS`：目前 main 有對應程式與 contract。
- `Tests PASS`：有自動測試 evidence。
- `CI PASS`：GitHub Actions 對該 commit / workflow 通過。
- `Deployment PASS`：對應版本已成功發布。
- `Runtime PASS`：實際服務可使用。
- `Integration PASS`：實際跨系統流程已驗收。
- `NOT VERIFIED`：缺必要證據；不得以程式存在推定完成。

## 2026-09-25 — Current Cloud / Web evidence

### Deployment

- Firebase Hosting：**PASS**。最新已知成功 evidence 為 workflow `Deploy Firebase Hosting` run #62，對應 main commit `1da5c1c0044a14406ff94896a04d994fcf48fd82`。
- Cloud Run：**PASS**。最新已知成功 evidence 為 workflow `Deploy Cloud Run` run #116，對應同一 commit。
- Cloud Run `life-assistant-api` 與 PostgreSQL runtime 已存在於 `gen-lang-client-0593591102`。
- PWA icon / manifest / branding 已完成最新修正並發布。

### Flutter Web → Backend → PostgreSQL

- Web API client 會透過 Firebase Hosting rewrite / `/api/v1` 呼叫 Backend。
- Task list / create / update / complete / delete API 已實作。
- 使用者於 2026-09-25 完成 Google 登入與 Task CRUD 互動驗收。
- 因此目前 Task 核心 flow：**Implementation PASS / Deployment PASS / Runtime PASS（互動驗收）**。

### Backend authentication

- Google OAuth login / callback 已實作。
- 使用 `__session` HttpOnly / Secure cookie 維持已驗證 Google identity session。
- Task 與 Google integration API 以 `current_user` 保護。
- OAuth state validation 已實作。
- Google access / refresh token 以 encrypted storage 保存，支援 refresh。
- Authentication baseline：**Implementation PASS**。
- 更細的 mutation authorization / risk / confirmation policy：**NOT VERIFIED / 尚未完成**。

## 2026-09-25 — Google integrations 第一批

### 已實作

Backend 已有：

- `gmail.list_metadata`
- `calendar.list`
- `calendar.create`
- `drive.bridge.ensure`

Web Integrations 頁已提供：

- Gmail 授權 / 重新授權
- Calendar 授權 / 重新授權
- Drive 授權 / 重新授權
- Gmail metadata read 驗收
- Calendar read 驗收
- Drive `life_assistant/ChatGPT_Bridge` ensure 驗收
- capability / risk / confirmation metadata 顯示

Google scope baseline：

- Gmail：`gmail.readonly`
- Calendar：`calendar.events`
- Drive：`drive.file`

目前不包含 Gmail send、全 Drive scope 等高權限能力。

### Tests

Backend `test_google_integrations.py` 已覆蓋：

- least-privilege scope
- incremental OAuth authorization URL
- encrypted token round-trip
- 第一批 capability catalog
- Calendar create timezone validation

CI backend job會執行 `python -m unittest discover -s tests -v`。

### 尚待 runtime acceptance

截至本次文件同步，不把以下項目標成 Integration PASS：

- Gmail metadata 真實帳號 read
- Calendar 真實帳號 read
- Drive Bridge 真實帳號 ensure

雖然 API / UI 已部署，仍需在已授權帳號上取得三項 PASS evidence。

## 2026-09-25 — 實作差異與依賴

### Calendar

目前 Cloud Backend：

- read：已實作
- create：已實作
- update：尚未實作
- delete：尚未實作

因此下一個 Cloud integration 批次應先補 `calendar.update` / `calendar.delete`。

### Gmail conversion

目前 Gmail metadata read 已實作，但 Cloud Backend 尚未有正式 conversion endpoints。

建議下一批：

1. Gmail → Task
2. Gmail → Calendar（由 request 明確提供 start/end，不由 LLM 或 Backend 猜時間）
3. Gmail → Project

其中 Gmail → Project **目前被 Project Backend 缺口阻塞**：repository 的 Cloud Backend 目前只有 Task model，尚無 Project model / Project CRUD API。不得把舊 SQLite Project CRUD 當成新的 Cloud Backend Project CRUD 已完成。

## 目前 Cloud Backend model / API 範圍

### 已有

- Task model + Task CRUD
- GoogleConnection / OAuth state model
- Google auth API
- Google integration API
- `/health`
- `/ready` + DB connectivity evidence
- Alembic Google integration migration

### 尚缺主要 Phase 1 Cloud API

- Project CRUD
- Note CRUD / search
- Habit
- Shopping
- Template
- Activity / execution log

## CI / CD 現況

`.github/workflows/ci.yml` 已包含：

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

正式部署路徑維持：

```text
GitHub main
  → GitHub Actions
  → tests / build
  → Firebase Hosting + Cloud Run
  → runtime / integration validation
```

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

這些是 migration source / existing assets，不代表相同能力已經完成 Cloud Backend / PostgreSQL 版本。

## 已知尚未完成

- Google Gmail / Calendar / Drive 三項 runtime acceptance 尚未完整取得 evidence。
- Calendar update / delete 尚未實作。
- Gmail → Task / Calendar / Project Cloud conversion 尚未實作。
- Project CRUD Cloud API 尚未實作，並阻塞 Gmail → Project。
- Backend 統一 error response 尚未完成。
- Backend execution / activity log baseline 尚未完成。
- SQLite → PostgreSQL migration 尚未有 runtime evidence。
- Project / Note / Habit / Shopping / Template Cloud API 尚未完成。
- ChatGPT Bridge Backend / MCP 尚未達 Phase 1 Release Gate。
- Phase 1 整體狀態仍為 **PARTIAL**。

## 下一步：Phase 1 收斂順序

1. 取得 Gmail / Calendar / Drive 真實帳號 runtime acceptance evidence。
2. 實作 Calendar update / delete + tests + capability metadata。
3. 實作 Gmail → Task / Calendar；Gmail → Project 等 Project CRUD API 後接上。
4. 建立統一 Backend error response + execution / activity log baseline。
5. 實作 SQLite → PostgreSQL 可重跑、可驗證 migration。
6. 擴充 Project / Note / Habit / Shopping / Template Cloud API。
7. 推進 ChatGPT Bridge Backend / MCP contract、policy、idempotency、audit。
8. 重新跑 Phase 1 acceptance / deployment / runtime / integration evidence。

Android / iOS 正式打包、release signing 與上架目前不是 Phase 1 主交付路線。

## 歷史摘要

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
