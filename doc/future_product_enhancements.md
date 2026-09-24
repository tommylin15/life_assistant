# life_assistant — Future Product Enhancements

最後更新：2026-09-24
狀態：**候選強化方向；不屬於目前 Phase 1 上線阻塞項目**

## 1. 目的

本文件整理對外部 Life OS / Personal Knowledge System 設計的研究結果，包含 Compass 專案中值得吸收的產品與 workflow 概念。

核心原則：

> **先完成目前 Web / Cloud 主線並上線，再以真實使用資料決定產品強化順序。**

這些強化項目可以先完成規格、UX、資料需求與 API contract 設計，但在 Phase 1 Release Gate 通過前，不應擴張為阻塞主線的新 implementation scope。

## 2. 不變的架構邊界

研究 Compass 不代表 life_assistant 改成 Obsidian-first、Markdown-first 或 local-only 架構。

life_assistant 維持：

- Flutter Web / PWA 作為主要 UI。
- FastAPI / Cloud Run 作為 Backend。
- PostgreSQL 作為 operational source of truth。
- Google / Gmail / Calendar / Drive integrations 由 life_assistant Backend 控制。
- ChatGPT Bridge Backend / MCP / Capability Catalog 屬於 life_assistant。
- schema validation、permission、confirmation、idempotency、execution log 仍由 life_assistant 負責。
- AI reasoning、Global Tool Registry、Workflow Registry、Agent Runtime、Agent Worker、跨系統 orchestration 仍由 omniAgent 負責。

## 3. 建議吸收的產品能力

### P0 — Situation-oriented navigation

未來主導航可逐步從純資料類型導向：

- Tasks
- Calendar
- Projects
- Notes

提升為生活情境導向：

- Today
- Focus
- Plan
- Review
- Projects

資料型功能仍保留為底層 domain / secondary navigation，不因主導航改變而移除。

### P0 — Today Cockpit

建立一個真正的每日工作台，聚合：

- 今日待辦與逾期事項。
- 下一個重要行程。
- 今日習慣與例行事項。
- 需要回覆 / 等待中的項目。
- Gmail / Calendar 中需要注意的訊號。
- 使用者固定的 Daily Questions / Check-in。

Today 的目標不是顯示所有資料，而是降低注意力負擔。

### P0 — Attention Model / Focus

建立可解釋、非 AI 依賴的注意力模型，例如：

1. overdue
2. due today
3. scheduled today
4. high priority
5. waiting / blocked
6. upcoming
7. other

同一項目應盡量只落在一個主要分類，避免 Dashboard 重複計數造成錯覺。

未來 AI 可以在此模型上補充排序或建議，但 deterministic rule 仍應可獨立運作。

### P0 — Routine Library

建立使用者可理解的生活 routine / prompt templates，例如：

- Morning Start
- What Matters Today
- End-of-day Review
- Weekly Review
- Meeting Prep
- Project Kickoff
- Inbox / Gmail Triage
- Calendar Prep
- Habit Check
- Exercise Reminder

Routine Library 屬於產品層的「可重用生活流程定義」。

若 routine 需要跨系統 AI planning / reasoning / retry / resume，實際 orchestration 由 omniAgent 執行；life_assistant 只保存自身需要的設定、狀態與 execution evidence。

### P0 — Global Capture

提供單一快速入口，將文字或語音快速分類為：

- Task
- Event
- Note
- Shopping item
- Project
- Person / follow-up（若未來啟用 People domain）

Phase 1 既有 quick input 可作為未來 Global Capture 的基礎，不需為了 Phase 2 預先重寫。

### P1 — Plan

建立跨尺度規劃視圖：

- Today
- This week
- Project horizon
- Monthly / quarterly review link

Plan 主要負責「安排與承諾」，不是另一套 source of truth。

### P1 — Review

建立基於實際紀錄的 Review：

- completed tasks
- habit records
- project progress
- activity / execution evidence
- selected self-reported metrics

缺值應維持缺值，不得由系統自行推論成完成、失敗或分數。

### P1 — Contextual AI entry points

AI 不只存在獨立 Chat 頁面；未來可在情境頁提供明確入口：

- Today：幫我整理今天真正重要的事。
- Focus：幫我找出卡住原因。
- Project：幫我整理下一步。
- Review：幫我從紀錄找模式。
- Gmail：幫我整理需處理信件。

AI 建議不等於已執行；有實際 mutation 時仍必須通過 life_assistant Backend policy / confirmation / execution gate。

### P2 — People / Relationship context

可評估新增 People domain，用於：

- follow-up
- discussion queue
- meeting context
- project participants

此項不列入近期 Phase 2 第一批，除非實際使用證明需求明確。

### P2 — Portable Markdown views / export

可提供 Markdown export、read model 或 portable snapshot，強化資料可攜性與 AI 可讀性。

但 Markdown 不取代 PostgreSQL operational source of truth。

## 4. 明確不照搬的 Compass 設計

以下不建議直接移植：

- 不改成 Obsidian 作核心 runtime。
- 不將 Markdown / frontmatter 改成主要 operational database。
- 不讓 AI client 直接繞過 Backend 寫資料。
- 不以 client-side approval prompt 取代 server-side permission / policy。
- 不因 Life OS UI 強化而將 omniAgent orchestration 責任搬回 life_assistant。
- 不為了視覺完整度在沒有 data evidence 時生成推測性分數或狀態。

## 5. 導入節奏

### Phase 1 — Platform Release

先完成目前已核准主線：

- Flutter Web / PWA。
- FastAPI Backend。
- PostgreSQL。
- SQLite → PostgreSQL migration。
- Google integrations。
- ChatGPT Bridge Backend / MCP baseline。
- logging / security / observability。
- Firebase Hosting + Cloud Run dev/test / release validation。

Phase 1 成功條件以 `acceptance.md` 為準。

### Phase 1.5 — Real-use Validation

Phase 1 上線後，以實際使用週期收集：

- 首頁實際最常使用資訊。
- 每天被忽略或重複顯示的資訊。
- 哪些提醒真正有用。
- 哪些 routine 使用頻率高。
- Gmail / Calendar / Task 之間最常見的轉換流程。
- 哪些操作仍需要手動跨頁完成。

此階段優先修 bug、資料一致性與 friction，不急著一次加入所有新模組。

### Phase 2 — Product Intelligence / Life OS UX

建議第一批順序：

1. Today Cockpit
2. Attention Model / Focus
3. Routine Library
4. Global Capture
5. Plan
6. Review
7. Contextual AI entry points

People、進階視覺化與 portable knowledge views 排在後續。

## 6. Scope Freeze 規則

Phase 1 期間：

- 可新增 Phase 2 文件、mockup、UX flow、schema proposal、API contract proposal。
- 不應因 Phase 2 候選功能改動 Phase 1 Release Gate，除非發現目前架構存在不可逆或高風險缺陷。
- 若 Phase 2 需求只需要未來 schema 可擴充，優先保留 extensibility，不提前實作完整功能。
- 新功能不得以「順便一起做」方式混入 Phase 1，除非明確記錄 scope change 與理由。

## 7. Phase 2 驗收原則

每個強化功能至少需證明：

- 使用真實 source data，不捏造狀態。
- missing / partial data 明確呈現。
- mutation 經 Backend validation / permission / audit。
- 不破壞既有 API contract 或提供 migration / versioning。
- 對 Today / Focus 等摘要的分類規則可說明、可測試。
- AI 輸出與實際 execution result 清楚分離。
- 功能有實際使用情境，不只因參考專案存在就加入。

## 8. 決策摘要

目前正式策略：

> **凍結 Phase 1 功能範圍，持續完成設計研究；先完成平台換軌並上線，再依真實使用證據導入 Life OS 強化功能。**

這份文件是未來產品強化基準，不代表其中項目已實作或已排入當前 sprint。
