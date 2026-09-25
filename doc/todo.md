# life_assistant — TODO

最後更新：2026-09-25

> 本清單以 GitHub `main` 與可取得的 runtime / CI evidence 為準。舊 Flutter + SQLite 實作保留為 migration source / existing assets；新的正式主線為 Firebase Hosting → Flutter Web → Cloud Run FastAPI → PostgreSQL。
>
> **Phase 1 採 scope freeze：先完成目前 Web / Cloud 主線與 Release Gate；Life OS 類新功能先做設計，不阻塞 Phase 1。**

## 狀態說明

- `[x]`：目前實作、測試、部署或相對應層級已有足夠 evidence。
- `[ ]`：尚未實作，或雖已實作但仍缺該項目要求的 runtime / integration evidence。
- 外部整合若只有程式與自動測試，不能因此宣告真實帳號 Integration PASS。

## 2026-09-25 evidence snapshot

- 功能 / audit baseline commit：`a6c714c488303952b36578ab45e0af7aa2df4c7a`。
- CI workflow run #152：PASS（Backend tests + Alembic validation + Flutter analyze/test/build + deployment script checks）。
- Cloud Run workflow run #121：PASS；`/health`、`/ready`、未登入 API 401 保護檢查 PASS。
- Firebase Hosting workflow run #67：PASS；Web build / deploy / Hosting verify PASS。
- Google Web Sign-In / Backend session flow：使用者互動登入驗收 PASS。
- Flutter Web → Backend Task CRUD → PostgreSQL：使用者互動 CRUD 驗收 PASS。
- Calendar update/delete、Gmail → Task、Gmail → Calendar：Implementation / CI / Deployment PASS；真實帳號 runtime integration 尚未重新驗收。
- Backend 統一 error envelope、request id、execution/activity log baseline 與 `/activity` API：Implementation / CI / Deployment PASS；真實 mutation 的 audit runtime 驗收仍待補。
- Gmail metadata、Calendar read/create、Drive Bridge API：已實作與部署；真實帳號 Gmail / Calendar / Drive integration acceptance 仍為 NOT VERIFIED。

## GCP 資源現況

| 資源 | Project | 狀態 |
|------|---------|------|
| Firebase Hosting / Flutter Web | `gen-lang-client-0593591102` | ✅ 已發布 |
| Cloud Run `life-assistant-api` | `gen-lang-client-0593591102` | ✅ 運行中 |
| PostgreSQL | `gen-lang-client-0593591102` / `janus-postgres-dev` VM | ✅ 運行中 |
| Secret Manager `life-assistant-bundle` | `gen-lang-client-0593591102` | ✅ 使用中 |
| `life-assistant-509213` 專案 | — | 🗑️ 已刪除；歷史文件若提及屬舊狀態 |

Cloud Run URL：`https://life-assistant-api-131494961796.us-central1.run.app`

## P0 — Cloud Foundation

- [x] Flutter Web 可正常 build
- [x] Web / PWA 基本設定
- [x] Firebase Hosting dev / test 發布
- [x] FastAPI Backend skeleton
- [x] Cloud Run dev / test 部署
- [x] PostgreSQL dev / test schema
- [x] Backend authentication baseline（Google Sign-In + signed session cookie + protected API）
- [ ] 完整 permission / authorization baseline（含 mutation risk / confirmation enforcement）
- [x] 統一 Backend error response baseline
- [x] Backend execution / activity log baseline
- [x] GitHub Actions CI：Flutter analyze/test/build、Backend test、migration SQL validation

## P0 — Core API

- [x] Task CRUD API
- [ ] Project CRUD API
- [ ] Note CRUD / search API
- [ ] Habit API
- [ ] Shopping API
- [ ] Template API
- [x] Activity / execution log API baseline
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
- [x] Calendar update API implementation
- [x] Calendar delete API implementation
- [x] Gmail metadata / snippet API implementation
- [x] Gmail → Task implementation
- [x] Gmail → Calendar implementation（start/end 由 request 明確提供，不由 Backend 猜測）
- [x] Drive `life_assistant/ChatGPT_Bridge` ensure API implementation
- [x] Integrations / Connections Web UI
- [x] Web 驗收 UI：Gmail read、Calendar read、Drive Bridge
- [x] Capability Catalog baseline：`gmail.list_metadata`、`gmail.to_task`、`gmail.to_calendar`、`calendar.list/create/update/delete`、`drive.bridge.ensure`
- [x] Google mutation execution-log baseline
- [x] Drive ensure partial-success 狀態 baseline

### 待 runtime / integration 驗收

- [ ] 真實帳號 Gmail read runtime PASS
- [ ] 真實帳號 Calendar read runtime PASS
- [ ] 真實帳號 Calendar create/update/delete runtime PASS
- [ ] 真實帳號 Drive Bridge runtime PASS
- [ ] 真實帳號 Gmail → Task runtime PASS
- [ ] 真實帳號 Gmail → Calendar runtime PASS
- [ ] Gmail → Project（依賴 Backend Project model / Project CRUD API）
- [ ] 真實 Google API failure 可追蹤到 execution/activity evidence 的 runtime PASS

## P1 — ChatGPT Bridge Backend

> 此區塊保留在 life_assistant；不得移到 omniAgent。

- [ ] 將現有 Bridge contract 對齊 PostgreSQL / Backend 架構
- [x] 保留 Drive Bridge 作 legacy / fallback baseline
- [ ] 定義 Backend Bridge API / MCP entrypoint
- [x] 第一批版本化 Google capability metadata
- [ ] 完整 Capability Catalog / MCP Tool Catalog
- [ ] schema validation
- [ ] request_id + action_id idempotency
- [ ] permission / risk / confirmation policy enforcement
- [ ] proposed action review flow
- [ ] action execution contract
- [ ] action result contract
- [x] Backend Activity / execution log baseline
- [x] partial success 表示 baseline
- [ ] Bridge / MCP failure 不破壞 PostgreSQL 主資料的 integration evidence

## P1 — MCP / Integration API

- [ ] `task.list` MCP/Integration contract
- [ ] `task.create` MCP/Integration contract
- [ ] `task.update` MCP/Integration contract
- [ ] `task.complete` MCP/Integration contract
- [x] `calendar.list` Backend capability baseline
- [x] `calendar.create` Backend capability baseline
- [x] `calendar.update` Backend capability baseline
- [x] `calendar.delete` Backend capability baseline
- [x] `gmail.list_metadata` Backend capability baseline
- [x] `gmail.to_task` Backend capability baseline
- [x] `gmail.to_calendar` Backend capability baseline
- [x] `drive.bridge.ensure` Backend capability baseline
- [ ] `note.search`
- [ ] `note.create`
- [ ] `project.get`
- [x] `activity.list` Backend API baseline
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
- [x] 統一 Backend error envelope + `request_id` baseline
- [x] 目前 Task / Google mutation audit trail baseline
- [x] 外部 action partial-success 表示 baseline（Drive ensure）
- [ ] Backend authorization / minimum permission 完整化
- [ ] 統一 sensitive log filtering（Backend 全域）
- [ ] destructive action confirmation / policy enforcement
- [ ] action idempotency（Backend 新主線）

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
- [ ] Google integrations 真實帳號 runtime acceptance 完整
- [ ] Google integrations failure state 真實 runtime 可追蹤到 execution/activity evidence
- [ ] Bridge / MCP 不繞過 Backend policy
- [x] 目前已實作的重要 mutation 有 execution log baseline
- [x] Firebase Hosting / Cloud Run deployment workflow evidence
- [ ] Phase 1 deployment / runtime / integration evidence 完整

## 當前建議執行順序

1. 取得 Gmail / Calendar / Drive 真實帳號 runtime acceptance；一併驗收 Calendar create/update/delete、Gmail → Task / Calendar 與 audit record。
2. 實作 SQLite → PostgreSQL 可重跑 migration + mapping / verification。
3. 建立 Project Cloud model / CRUD，解除 Gmail → Project 阻塞。
4. 擴充 Note / Habit / Shopping / Template Cloud API。
5. 補完整 Backend permission / confirmation / idempotency policy。
6. 推進 ChatGPT Bridge Backend / MCP contract 與 Phase 1 Release Gate。

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
