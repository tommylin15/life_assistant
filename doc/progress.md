# 生活助理 App v0.1 — 開發進度

最後更新：2026-09-25

目前狀態：**Phase 1 = PARTIAL。Web / Cloud 主線、Task CRUD、Project CRUD、Google integration 第二批、統一 error contract、execution/activity log baseline 均已進 main 並通過 CI / deployment；真實帳號 Google integration acceptance、Project 登入後 runtime CRUD、完整 SQLite → PostgreSQL migration、其餘 Cloud domain API 與 Bridge/MCP Release Gate 尚未完成。**

## 狀態定義

- `Implementation PASS`：main 有對應 code / contract。
- `Tests PASS`：自動測試通過。
- `CI PASS`：GitHub Actions 對該 commit 通過。
- `Deployment PASS`：對應版本已成功發布。
- `Runtime PASS`：實際服務 / 功能已取得 runtime evidence。
- `Integration PASS`：實際跨系統流程驗收通過。
- `NOT VERIFIED`：缺必要 evidence，不得由 code 存在推定完成。

## 最新主線 evidence

### 2026-09-25 Project Cloud + Gmail → Project

Commit：`0ea1d1fad596bcce4683df82b7d68caa4d7e42be`

已實作：

- PostgreSQL `projects` Cloud model
- Project list / create / get / update / delete API
- Project create/update/delete execution audit
- Project delete 若仍有 Task 關聯則回 409，避免 orphan
- Alembic revision `20260925_0003_projects`
- Gmail → Project conversion endpoint
- `gmail.to_project` capability metadata
- Project / Gmail-to-project contract tests

Evidence：

- CI #154：**PASS**
- Cloud Run #123：**PASS**
  - backend deploy PASS
  - service URL resolution PASS
  - `/health` PASS
  - `/ready` PASS
  - unauthenticated protected API 401 PASS
- Firebase Hosting #69：**PASS**
  - Web build PASS
  - deploy PASS
  - Hosting verify PASS

判定：

- Project CRUD：**Implementation PASS / Tests PASS / CI PASS / Deployment PASS / Runtime NOT VERIFIED**
- Gmail → Project：**Implementation PASS / Tests PASS / CI PASS / Deployment PASS / Integration NOT VERIFIED**
- Alembic `0003`：**Implementation PASS / CI validation PASS**；目前部署流程仍以 startup additive `Base.metadata.create_all` 作 transitional safety net，沒有 evidence 證明 production 是以 `alembic upgrade` 套用，故不得標示 production Alembic apply PASS。

## 2026-09-25 Error / Audit baseline

Commit：`a6c714c488303952b36578ab45e0af7aa2df4c7a`

已實作：

- `error.code / error.message / error.request_id`
- `X-Request-ID`
- safe unhandled-error response
- `execution_logs` operational table + migration
- `/api/v1/activity`
- Task mutation audit
- Calendar create/update/delete audit
- Gmail → Task / Calendar audit
- Drive Bridge ensure audit
- `partial_success` baseline
- fail-closed audit start；audit finalize failure 不包裝成 full success

Evidence：CI #152、Cloud Run #121、Firebase #67 均 PASS。

判定：**Implementation / Tests / CI / Deployment PASS；真實 external mutation → activity end-to-end Runtime/Integration NOT VERIFIED。**

## 2026-09-25 Google integration 第二批

Commit：`2c20aad24224b0c1541d0ad16752178389cff044`，後續由 `a6c714c` 與 `0ea1d1f` 擴充。

目前 capability baseline：

- `gmail.list_metadata`
- `gmail.to_task`
- `gmail.to_calendar`
- `gmail.to_project`
- `calendar.list`
- `calendar.create`
- `calendar.update`
- `calendar.delete`
- `drive.bridge.ensure`

Scope baseline：

- Gmail：`gmail.readonly`
- Calendar：`calendar.events`
- Drive：`drive.file`

安全語意：

- Gmail → Calendar 必須明確提供 start/end + timezone。
- Calendar delete metadata = `destructive_external` / `explicit_user`。
- metadata 不等於 enforcement；完整 confirmation policy 仍未完成。

真實帳號 acceptance 仍 **NOT VERIFIED**：

- Gmail read
- Gmail → Task / Calendar / Project
- Calendar read/create/update/delete
- Drive Bridge ensure
- provider failure → execution record

## Core Web / Cloud baseline

已完成：

- Firebase Hosting → Flutter Web/PWA
- Cloud Run FastAPI
- PostgreSQL connectivity
- Google Sign-In / Backend session
- Task CRUD
- Project CRUD implementation
- Backend error contract
- execution/activity baseline
- CI/CD deployment chain

使用者已互動驗收：

- Google 登入：PASS
- Task CRUD：PASS

尚未互動驗收：

- Project CRUD
- Google integrations 真實帳號第二批

## Cloud Backend model / API 範圍

### 已有

- Task model / CRUD
- Project model / CRUD
- GoogleConnection / OAuth state
- ExecutionLog
- Google auth / integration API
- `/api/v1/activity`
- `/health`
- `/ready`
- Alembic revisions `0001` Google integrations、`0002` execution logs、`0003` projects

### 尚缺主要 domain Cloud API

- Note CRUD / search
- Habit
- Shopping
- Template
- Checklist / tags 完整 Cloud model
- attachment central storage model

## SQLite → PostgreSQL migration

Legacy SQLite schema version：3。

現況：

- SQLite source 保留：PASS
- Task target schema：存在
- Project target schema：存在
- Note / Habit / Shopping / Template 等 target schema：尚缺
- 完整 export/import：未實作
- idempotent upsert：未驗證
- row count / relationship validation：未實作
- runtime migration evidence：NOT VERIFIED

因此完整 migration 仍為 **PARTIAL / 未完成**；目前不應硬做只搬部分 domain 卻宣稱 migration 完成。

## 文件一致性

文件一致化 commit：`0be77b05c40bcdc2434ff4b94689bab49ef5173a`，CI #153 PASS。

本次 Project Cloud 完成後，`todo.md / progress.md / acceptance.md / data_model.md` 再次依最新 evidence 回寫，避免「Project Cloud 缺口」舊敘述殘留。

## 已知尚未完成

- Project authenticated runtime CRUD evidence
- Gmail / Calendar / Drive 真實帳號 integration acceptance
- external failure → execution/activity runtime evidence
- Note / Habit / Shopping / Template Cloud API
- 完整 SQLite → PostgreSQL migration
- Backend confirmation / permission / idempotency enforcement
- ChatGPT Bridge Backend / MCP Release Gate
- responsive / desktop Web 完整 UX acceptance

## 下一步

1. 在已登入 App session 驗收 Project CRUD + Gmail/Calendar/Drive 真實帳號流程，並核對 `/activity`。
2. 補 Note / Habit / Shopping / Template Cloud target schema/API。
3. 建立完整可重跑 SQLite → PostgreSQL export/import + verification。
4. 完成 authorization / confirmation / idempotency policy。
5. 收斂 ChatGPT Bridge Backend / MCP contract 與 Phase 1 acceptance。

Android / iOS 正式打包與上架不是 Phase 1 主交付路線。
