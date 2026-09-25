# life_assistant — TODO

最後更新：2026-09-25

> 本清單以 GitHub main 與可取得的 runtime / CI evidence 為準。舊 Flutter + SQLite 實作保留為既有資產，但新的 Web / Cloud Phase 1 仍未完成。
>
> **Phase 1 採 scope freeze：先完成並上線目前 Web / Cloud 主線；Life OS 類新功能先做設計，不阻塞 Phase 1。**

## 狀態說明

- `[x]`：目前實作或部署已有足夠 evidence。
- `[ ]`：尚未實作，或雖已實作但仍缺必要 runtime / integration evidence。
- 外部整合若只有程式與單元測試，不能因為 code exists 就視為整合完成。

## 2026-09-25 evidence snapshot

- GitHub main head（同步前）：`1da5c1c0044a14406ff94896a04d994fcf48fd82`。
- Firebase Hosting workflow run #62：PASS。
- Cloud Run workflow run #116：PASS。
- Flutter Web / PWA branding 已完成最新一輪部署。
- Google Web Sign-In / Backend session flow 已實作；使用者已完成互動登入驗收。
- Flutter Web → Backend Task CRUD → PostgreSQL 已完成互動 CRUD 驗收。
- Gmail metadata、Calendar read/create、Drive Bridge API 與 Web 驗收 UI 已實作；真實帳號 Gmail / Calendar / Drive 三項整合驗收仍需重新取得 PASS evidence。

## GCP 資源現況

| 資源 | Project | 狀態 |
|------|---------|------|
| Firebase Hosting / Flutter Web | `gen-lang-client-0593591102` | ✅ 已發布 |
| Cloud Run `life-assistant-api` | `gen-lang-client-0593591102` | ✅ 運行中 |
| PostgreSQL | `gen-lang-client-0593591102` / `janus-postgres-dev` VM | ✅ 運行中 |
| Secret Manager `life-assistant-bundle` | `gen-lang-client-0593591102` | ✅ 統一密碼存放 |
| `life-assistant-509213` 專案 | — | 🗑️ 已刪除；歷史文件若提及屬舊狀態 |

Cloud Run URL：`https://life-assistant-api-131494961796.us-central1.run.app`

## P0 — Cloud Foundation

- [x] Flutter Web 可正常 build
- [x] 建立 Web / PWA 基本設定
- [x] Firebase Hosting dev / test 發布
- [x] 建立 FastAPI Backend skeleton
- [x] Cloud Run dev / test 部署
- [x] 建立 PostgreSQL dev / test schema
- [x] 建立 Backend authentication baseline（Google Sign-In + signed session cookie + protected API）
- [ ] 建立完整 permission / authorization baseline（含 mutation risk / policy）
- [ ] 建立統一 Backend error response
- [ ] 建立 Backend execution / activity log baseline
- [x] GitHub Actions CI 包含 Flutter analyze/test/build、Backend test 與 migration SQL validation

## P0 — Core API

- [x] Task CRUD API
- [ ] Project CRUD API
- [ ] Note CRUD / search API
- [ ] Habit API
- [ ] Shopping API
- [ ] Template API
- [ ] Activity / execution log API
- [x] Flutter Web 主線以 Backend API 存取 Task 核心資料
- [x] Web Google integration 透過 Backend API 呼叫，不由瀏覽器直接持有 Google access token
- [ ] 將其他舊原生功能逐步改為 Web / Backend source of truth

## P0 — SQLite → PostgreSQL Migration

- [ ] 定義目前 SQLite 最新 schema → PostgreSQL mapping
- [ ] 建立核心資料 export
- [ ] 建立 dev / test import
- [ ] migration 可重跑且不重複資料
- [ ] 驗證主表筆數與關聯
- [ ] migration failure 不破壞 SQLite 原資料
- [ ] migration result 區分 success / partial success / failure

## P1 — Google Integrations

### 已實作 baseline

- [x] Google Web Sign-In / Backend identity flow
- [x] 增量 Gmail / Calendar / Drive OAuth flow
- [x] Google token encrypted storage + refresh baseline
- [x] Calendar read API implementation
- [x] Calendar create API implementation
- [x] Gmail metadata / snippet API implementation
- [x] Drive `life_assistant/ChatGPT_Bridge` ensure API implementation
- [x] Integrations / Connections Web UI
- [x] Web 驗收 UI：Gmail read、Calendar read、Drive Bridge
- [x] Capability Catalog 第一批：`gmail.list_metadata`、`calendar.list`、`calendar.create`、`drive.bridge.ensure`

### 下一批 / 待驗收

- [ ] 真實帳號 Gmail read runtime PASS
- [ ] 真實帳號 Calendar read runtime PASS
- [ ] 真實帳號 Drive Bridge runtime PASS
- [ ] Calendar update
- [ ] Calendar delete
- [ ] Gmail → task
- [ ] Gmail → calendar
- [ ] Gmail → project（依賴 Backend Project model / Project CRUD API）
- [ ] integration error 有 execution/activity evidence，且不破壞 PostgreSQL 主資料

## P1 — ChatGPT Bridge Backend

> 此區塊保留在 life_assistant；不得移到 omniAgent。

- [ ] 將現有 Bridge contract 對齊 PostgreSQL / Backend 架構
- [x] 保留 Drive Bridge 作 legacy / fallback baseline
- [ ] 定義 Backend Bridge API / MCP entrypoint
- [x] 第一批版本化 Google capability metadata
- [ ] 完整 Capability Catalog / MCP Tool Catalog
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

- [ ] `task.list` MCP/Integration contract
- [ ] `task.create` MCP/Integration contract
- [ ] `task.update` MCP/Integration contract
- [ ] `task.complete` MCP/Integration contract
- [x] `calendar.list` Backend capability baseline
- [x] `calendar.create` Backend capability baseline
- [ ] `calendar.update`
- [ ] `calendar.delete`
- [x] `gmail.list_metadata` Backend capability baseline
- [x] `drive.bridge.ensure` Backend capability baseline
- [ ] `note.search`
- [ ] `note.create`
- [ ] `project.get`
- [ ] `activity.list`
- [x] 第一批 tool name / version / risk / confirmation metadata
- [ ] 完整 schema metadata
- [ ] 完整 permission / risk policy
- [ ] confirmation enforcement

## P1 — UI / UX

- [x] Flutter Web / PWA 可發布
- [x] Tasks Web 主線
- [x] Google Integrations / Connections 頁
- [x] PWA 主畫面 icon / branding baseline
- [ ] Responsive Web layout 完整驗收
- [ ] Desktop browser layout 完整驗收
- [ ] Dashboard Web 主線
- [ ] Calendar Web 主線
- [ ] Projects Web 主線
- [ ] Notes Web 主線
- [ ] Habits Web 主線
- [ ] Shopping Web 主線
- [ ] Activity / execution log Web 主線
- [ ] ChatGPT Bridge / MCP status page
- [ ] Settings Web 主線
- [ ] loading / empty / error / data state consistency
- [ ] accessibility baseline（Web 主線）

## P1 — Attachment / Storage

- [ ] 定義中央 attachment storage/reference 策略
- [ ] 圖片
- [ ] PDF
- [ ] 一般文件
- [ ] 不依賴單一手機絕對路徑作為中央 model

## P1 — Security / Governance

- [x] Google identity authentication baseline
- [x] OAuth state validation baseline
- [x] Google access / refresh token encrypted storage baseline
- [x] Google scopes 採 Gmail readonly / Calendar events / Drive file 最小權限 baseline
- [ ] Backend authorization / minimum permission 完整化
- [ ] 統一 sensitive log filtering（Backend 全域）
- [ ] destructive action policy
- [ ] action audit trail
- [ ] idempotency（Backend 新主線）
- [ ] partial success handling

## P2 — PWA / Operational Polish

- [x] PWA 可加入手機主畫面 baseline
- [x] PWA icon / manifest branding baseline
- [ ] service worker / cache 行為驗收
- [ ] backup / export
- [ ] operational monitoring
- [ ] failure recovery runbook
- [ ] release checklist

## Phase 1 Release Gate

- [ ] `acceptance.md` Phase 1 條件全部通過
- [x] 核心 Task Web / Backend / PostgreSQL flow 已有互動驗收 evidence
- [ ] SQLite migration 有 rollback / failure evidence
- [ ] Google integrations 三項 runtime acceptance 完整
- [ ] Google integrations failure state 可追蹤到 execution/activity evidence
- [ ] Bridge / MCP 不繞過 Backend policy
- [ ] 重要 mutation 有 execution log
- [x] Firebase Hosting / Cloud Run deployment workflow evidence
- [ ] Phase 1 deployment / runtime / integration evidence 完整

## 當前建議執行順序

1. 完成 Gmail / Calendar / Drive 真實帳號 runtime acceptance。
2. 補 Calendar update / delete。
3. 補 Gmail → task / calendar；Gmail → project 等 Project CRUD API 建立後接上。
4. 建立統一 Backend error response + execution / activity log baseline。
5. 實作 SQLite → PostgreSQL 可重跑 migration。
6. 擴充 Project / Note / Habit / Shopping 等 Cloud API。
7. 推進 ChatGPT Bridge Backend / MCP contract 與 Phase 1 Release Gate。

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

## Existing Assets — 舊原生 Flutter + SQLite

以下為既有資產，不應因 Web / Cloud 主線而刪除；但 `[x]` 不代表已遷移成 Backend/PostgreSQL 版本：

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
