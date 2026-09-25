# life_assistant — TODO

最後更新：2026-09-25

> Source of truth：GitHub `main` + CI / deployment / runtime evidence。舊 Flutter + SQLite 保留為 migration source / existing assets；正式主線為 Firebase Hosting → Flutter Web → Cloud Run FastAPI → PostgreSQL。
>
> Phase 1 維持 scope freeze；Phase 2 的 Today / Focus / Routine / Plan / Review 不阻塞 Phase 1。

## 狀態規則

- `[x]`：該層級已有足夠 evidence。
- `[ ]`：尚未完成，或缺該項要求的 runtime / integration evidence。
- Implementation / CI / Deployment PASS 不等於真實帳號 Integration PASS。

## 最新 evidence snapshot

- 最新功能 commit：`0ea1d1fad596bcce4683df82b7d68caa4d7e42be` — `feat: add cloud projects and Gmail conversion`
- CI #154：PASS（Backend import / Alembic validation / tests；Flutter analyze / test / build；deployment script checks）。
- Cloud Run #123：PASS（deploy、service URL、`/health`、`/ready`、未登入 protected API 401）。
- Firebase Hosting #69：PASS（build、deploy、Hosting verify）。
- 文件一致化 commit：`0be77b05c40bcdc2434ff4b94689bab49ef5173a`；CI #153 PASS。
- Google Sign-In：使用者互動驗收 PASS。
- Task CRUD → PostgreSQL：使用者互動驗收 PASS。
- Project CRUD / Gmail → Project：Implementation / CI / Deployment PASS；登入後 runtime / integration 尚未驗收。
- Gmail / Calendar / Drive 真實帳號整合：仍為 NOT VERIFIED。

## P0 — Cloud Foundation

- [x] Flutter Web / PWA build baseline
- [x] Firebase Hosting dev/test deployment
- [x] FastAPI Backend + Cloud Run deployment
- [x] PostgreSQL connectivity / Task persistence
- [x] Google identity authentication baseline
- [x] 統一 Backend error envelope + `X-Request-ID`
- [x] Backend execution / activity log baseline
- [x] CI：Flutter analyze/test/build、Backend tests、Alembic SQL validation
- [ ] 完整 authorization / confirmation enforcement
- [ ] Backend mutation idempotency baseline
- [ ] Backend 全域 sensitive-log filtering 完整驗收

## P0 — Core Cloud API

- [x] Task CRUD
- [x] Project CRUD
- [ ] Note CRUD / search
- [ ] Habit API
- [ ] Shopping API
- [ ] Template API
- [x] Activity / execution log read baseline
- [x] Project delete 防止仍有 Task 關聯時製造 orphan（409）
- [ ] 其他 legacy 原生能力逐步切到 Backend/PostgreSQL source of truth

## P0 — SQLite → PostgreSQL Migration

- [ ] 完成 SQLite schema v3 → PostgreSQL mapping
- [ ] 建立 deterministic export
- [ ] 建立 dev/test import / upsert
- [ ] 重跑不產生重複資料
- [ ] 驗證 row counts / primary keys / relationships / critical timestamps
- [ ] migration failure 不破壞 SQLite 原資料
- [ ] result 明確區分 success / partial success / failure
- [ ] migration runtime evidence

> 目前 Task + Project 已有 Cloud target schema；Note / Habit / Shopping / Template 等 target schema 尚缺，因此完整 migration 仍是 PARTIAL / 尚未可驗收。

## P1 — Google Integrations

### Implementation / deployment PASS

- [x] Incremental Gmail / Calendar / Drive OAuth
- [x] encrypted token storage + refresh baseline
- [x] `gmail.list_metadata`
- [x] `gmail.to_task`
- [x] `gmail.to_calendar`
- [x] `gmail.to_project`
- [x] `calendar.list`
- [x] `calendar.create`
- [x] `calendar.update`
- [x] `calendar.delete`
- [x] `drive.bridge.ensure`
- [x] mutation execution-log baseline
- [x] Drive ensure `partial_success` baseline
- [x] Gmail → Calendar 明確要求 request 提供 start/end + timezone，不由 Backend 猜時間

### Runtime / integration NOT VERIFIED

- [ ] 真實帳號 Gmail metadata read
- [ ] 真實帳號 Gmail → Task
- [ ] 真實帳號 Gmail → Calendar
- [ ] 真實帳號 Gmail → Project
- [ ] 真實帳號 Calendar read/create/update/delete
- [ ] 真實帳號 Drive Bridge ensure
- [ ] 真實 provider failure → execution/activity evidence

## P1 — Project Cloud

- [x] `projects` Cloud model
- [x] Alembic `20260925_0003_projects`
- [x] Project list/create/get/update/delete API
- [x] Project mutation audit
- [x] Gmail → Project capability
- [ ] Flutter Web Projects 主線
- [ ] Authenticated Project CRUD runtime acceptance
- [ ] Gmail → Project true-account integration acceptance

## P1 — MCP / Integration Contract

- [ ] `task.list/create/update/complete` 對外版本化 contract
- [x] `project.get` 對應 Cloud API baseline（尚未整理成完整 MCP schema）
- [x] Google capability catalog baseline
- [x] `activity.list` Backend API baseline
- [ ] 完整 input/output schema metadata
- [ ] permission / risk / confirmation enforcement
- [ ] request_id + action_id idempotency
- [ ] proposed action review / execution / result contract
- [ ] Bridge / MCP failure 不破壞 PostgreSQL 主資料的 integration evidence

## P1 — UI / UX

- [x] Flutter Web / PWA 可發布
- [x] Tasks Web 主線
- [x] Google Integrations / Connections 頁
- [x] PWA icon / manifest branding baseline
- [ ] Projects Web 主線
- [ ] Dashboard Web 主線
- [ ] Calendar Web 主線
- [ ] Notes Web 主線
- [ ] Habits Web 主線
- [ ] Shopping Web 主線
- [ ] Activity / execution log Web 主線
- [ ] ChatGPT Bridge / MCP status page
- [ ] Settings Web 主線
- [ ] responsive / desktop layout 完整驗收
- [ ] loading / empty / error state consistency
- [ ] accessibility baseline

## P1 — Security / Governance

- [x] Google access / refresh token encrypted-storage baseline
- [x] OAuth state validation
- [x] Least-privilege baseline：Gmail readonly / Calendar events / Drive file
- [x] unified error envelope + request id
- [x] Task / Project / Google mutation audit baseline
- [x] external partial-success representation baseline
- [ ] destructive/sensitive action confirmation enforcement
- [ ] Backend minimum-permission policy 完整驗證
- [ ] idempotency for new Cloud mutation path

## P1 — Attachment / Storage

- [ ] 定義中央 attachment storage/reference 策略
- [ ] 圖片 / PDF / 一般文件
- [ ] 不依賴單一手機絕對路徑作中央 model

## P2 — Operational Polish

- [x] PWA 可加入手機主畫面 baseline
- [x] PWA icon / manifest baseline
- [ ] service worker / cache 行為驗收
- [ ] backup / export
- [ ] operational monitoring
- [ ] failure recovery runbook
- [ ] release checklist

## Phase 1 Release Gate

- [ ] `acceptance.md` Phase 1 條件全部通過
- [x] Task Web / Backend / PostgreSQL 互動驗收
- [x] CI / Firebase / Cloud Run deployment evidence
- [x] 目前主要 mutation execution-log implementation baseline
- [ ] Project authenticated runtime acceptance
- [ ] Google integrations 真實帳號 success/failure evidence
- [ ] SQLite migration runtime evidence
- [ ] Bridge / MCP policy + idempotency + integration evidence
- [ ] Phase 1 整體 deployment / runtime / integration evidence 完整

## 當前建議執行順序

1. 在已登入 App session 做 Project CRUD + Gmail/Calendar/Drive 真實帳號 acceptance，並核對 `/activity` execution records。
2. 補 Note / Habit / Shopping / Template Cloud target schema/API，讓完整 SQLite migration 有合法 target。
3. 實作 SQLite → PostgreSQL 可重跑 export/import + verification。
4. 補完整 authorization / confirmation / idempotency policy。
5. 完成 ChatGPT Bridge Backend / MCP contract 與 Phase 1 Release Gate。

## Existing Assets — legacy Flutter + SQLite

既有 SQLite schema v3、Item/Project CRUD、Dashboard、Notes/FTS5、Habits、Shopping、Templates、Attachments、Calendar/Gmail adapters、Drive/Share Bridge、Bridge schema/idempotency/proposed-action UI、Activity log、PIN/biometric/sensitive-log filtering皆保留。這些不代表同名 Cloud Backend 能力已自動完成。

## Out of Scope — omniAgent

life_assistant 不負責：LangGraph Agent、Global Tool Registry、Workflow Registry、通用 Agent Runtime/Worker、跨系統 multi-tool reasoning/orchestration。life_assistant 只提供自己的資料、權限、執行、audit 與 MCP / Integration capabilities。
