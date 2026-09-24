# life_assistant — TODO

最後更新：2026-09-24

> 本清單以目前正式架構為準。舊 Flutter + SQLite 實作保留為既有資產，但不代表新的 Web / Cloud Phase 1 已完成。
>
> **Phase 1 採 scope freeze：先完成並上線目前 Web / Cloud 主線；Life OS 類新功能先做設計，不阻塞 Phase 1。**

## GCP 資源現況

| 資源 | Project | 狀態 |
|------|---------|------|
| Cloud Run `life-assistant-api` | `gen-lang-client-0593591102` | ✅ 運行中 |
| PostgreSQL | `gen-lang-client-0593591102` / `janus-postgres-dev` VM | ✅ 運行中 |
| Secret Manager `life-assistant-bundle` | `gen-lang-client-0593591102` | ✅ 統一密碼存放 |
| `life-assistant-509213` 專案 | — | 🗑️ 已刪除 |

Cloud Run URL：`https://life-assistant-api-131494961796.us-central1.run.app`

## P0 — Cloud Foundation

- [x] Flutter Web 可正常 build
- [x] 建立 Web / PWA 基本設定
- [ ] Firebase Hosting dev / test 發布
- [x] 建立 FastAPI Backend skeleton
- [x] Cloud Run dev / test 部署
- [x] 建立 PostgreSQL dev / test schema
- [ ] 建立 Backend auth / permission baseline
- [ ] 建立統一 Backend error response
- [ ] 建立 Backend execution / activity log baseline
- [x] 修正目前 GitHub Actions CI failure

## P0 — Core API

- [x] Task CRUD API
- [ ] Project CRUD API
- [ ] Note CRUD / search API
- [ ] Habit API
- [ ] Shopping API
- [ ] Template API
- [ ] Activity / execution log API
- [ ] Flutter Web 改以 Backend API 存取核心資料
- [ ] 前端不得直接操作 PostgreSQL / SQLite DAO / Google API

## P0 — SQLite → PostgreSQL Migration

- [ ] 定義目前 SQLite 最新 schema → PostgreSQL mapping
- [ ] 建立核心資料 export
- [ ] 建立 dev / test import
- [ ] migration 可重跑且不重複資料
- [ ] 驗證主表筆數與關聯
- [ ] migration failure 不破壞 SQLite 原資料
- [ ] migration result 區分 success / partial success / failure

## P1 — Google Integrations

- [ ] Google Web Sign-In / Backend token flow
- [ ] Calendar read
- [ ] Calendar create
- [ ] Calendar update
- [ ] Calendar delete
- [ ] Gmail metadata / snippet
- [ ] Gmail → task
- [ ] Gmail → calendar
- [ ] Gmail → project
- [ ] integration error 可追蹤且不破壞 PostgreSQL 主資料
- [ ] token / secret 不進一般 log 或 export

## P1 — ChatGPT Bridge Backend

> 此區塊保留在 life_assistant；不得移到 omniAgent。

- [ ] 將現有 Bridge contract 對齊 PostgreSQL / Backend 架構
- [ ] 保留 Drive Bridge 作 legacy / fallback
- [ ] 定義 Backend Bridge API / MCP entrypoint
- [ ] 定義版本化 capability schema
- [ ] 建立 Capability Catalog / MCP Tool Catalog
- [ ] schema validation
- [ ] request_id + action_id idempotency
- [ ] permission / risk / confirmation policy
- [ ] proposed action review flow
- [ ] action execution
- [ ] action result
- [ ] Activity / execution log
- [ ] partial success 表示
- [ ] Bridge / MCP failure 不破壞 PostgreSQL 主資料

## P1 — MCP / Integration API

- [ ] `task.list`
- [ ] `task.create`
- [ ] `task.update`
- [ ] `task.complete`
- [ ] `calendar.list`
- [ ] `calendar.create`
- [ ] `calendar.update`
- [ ] `note.search`
- [ ] `note.create`
- [ ] `project.get`
- [ ] `activity.list`
- [ ] tool schema/version metadata
- [ ] permission/risk metadata
- [ ] confirmation policy metadata

## P1 — UI / UX

- [ ] Responsive Web layout
- [ ] Mobile browser layout
- [ ] Desktop browser layout
- [ ] Dashboard
- [ ] Tasks
- [ ] Calendar
- [ ] Projects
- [ ] Notes
- [ ] Habits
- [ ] Shopping
- [ ] Activity / execution log
- [ ] Integrations / Connections
- [ ] ChatGPT Bridge / MCP status page
- [ ] Settings
- [ ] loading / empty / error / data state consistency
- [ ] accessibility baseline

## P1 — Attachment / Storage

- [ ] 定義中央 attachment storage/reference 策略
- [ ] 圖片
- [ ] PDF
- [ ] 一般文件
- [ ] 不依賴單一手機絕對路徑作為中央 model

## P1 — Security / Governance

- [ ] auth / authorization
- [ ] minimum permission
- [ ] secure secret/token storage
- [ ] sensitive log filtering
- [ ] destructive action policy
- [ ] action audit trail
- [ ] idempotency
- [ ] partial success handling

## P2 — PWA / Operational Polish

- [ ] PWA 可加入手機主畫面
- [ ] service worker / cache baseline
- [ ] backup / export
- [ ] operational monitoring
- [ ] failure recovery runbook
- [ ] release checklist

## Phase 1 Release Gate

- [ ] `acceptance.md` Phase 1 條件通過
- [ ] 核心 Web / Backend / PostgreSQL flow 在 dev/test 可重跑驗證
- [ ] SQLite migration 有 rollback / failure evidence
- [ ] Google integrations failure state 可追蹤
- [ ] Bridge / MCP 不繞過 Backend policy
- [ ] 重要 mutation 有 execution log
- [ ] deployment / runtime evidence 完整

## Phase 1.5 — Real-use Validation

> Phase 1 上線後執行；此階段以修正 friction 與資料一致性為主，不一次展開所有新功能。

- [ ] 記錄首頁真正需要的資訊
- [ ] 找出重複或干擾性提醒
- [ ] 記錄 Gmail / Calendar / Task 最常見轉換流程
- [ ] 記錄常用 routine / prompt
- [ ] 找出需要手動跨頁完成的高摩擦流程
- [ ] 依實際使用結果確認 Phase 2 優先順序

## Phase 2 — Future Product Enhancements

> 詳細規格見 `future_product_enhancements.md`。下列項目目前可做設計，但不應阻塞 Phase 1。

- [ ] Today Cockpit
- [ ] Attention Model / Focus
- [ ] Routine Library
- [ ] Global Capture
- [ ] Plan
- [ ] Review
- [ ] Contextual AI entry points
- [ ] People / relationship context（後續候選）
- [ ] Portable Markdown views / export（後續候選）

## Existing Assets — 已有但需遷移/驗證

以下為舊原生 Flutter + SQLite 版本已存在的資產，不應刪除：

- [x] SQLite schema / migrations
- [x] Item CRUD
- [x] Project CRUD
- [x] Dashboard
- [x] Quick input
- [x] Activity log
- [x] Notes / FTS5
- [x] Habits
- [x] Shopping
- [x] Templates
- [x] Attachments
- [x] Calendar adapter
- [x] Gmail adapter
- [x] Share Bridge
- [x] Drive Bridge
- [x] Bridge JSON schema validator
- [x] request_id + action_id idempotency
- [x] proposed action review UI
- [x] action_results export
- [x] PIN / biometric / sensitive log filtering

## Out of Scope — 由 omniAgent 負責

以下不得新增到 life_assistant WBS / TODO：

- LangGraph Agent
- Global Tool Registry
- Workflow Registry
- Agent Runtime
- Agent Worker
- 跨系統 multi-tool orchestration
- 通用 AI planning / reasoning loop
- 通用 workflow retry / resume orchestration

life_assistant 只提供自己的 MCP / Integration capabilities，並負責實際資料、權限、執行與 audit。
