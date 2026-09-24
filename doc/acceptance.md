# 生活助理 App v0.1 — Acceptance Criteria

最後更新：2026-09-24

> 本文件定義 **Phase 1 Platform Release** 的完成條件。Phase 2 的 Today / Focus / Routine Library / Global Capture 等強化功能不屬於目前 Release Gate。

## Phase 1 Web / Cloud 核心

- [ ] Flutter Web 可正常 build。
- [ ] 前端可透過 Firebase Hosting 發布到 dev / test 環境。
- [ ] FastAPI Backend 可部署到 Cloud Run dev / test 環境。
- [ ] Flutter Web 可透過 Backend API 讀取與寫入核心資料。
- [ ] PostgreSQL 可建立 schema 並持久保存資料。
- [ ] 前端不直接連 PostgreSQL。
- [ ] Backend API 錯誤有一致格式與可追蹤 log。
- [ ] 手機與電腦瀏覽器皆可使用主要介面。
- [ ] PWA 可加入手機主畫面（若當期 Flutter Web/PWA 設定支援）。

## SQLite Migration

- [ ] 既有 SQLite 資料不被清空或 drop。
- [ ] 可從目前最新 SQLite schema 匯出核心資料。
- [ ] 可匯入 PostgreSQL dev / test schema。
- [ ] migration 重跑不造成重複資料。
- [ ] 主表筆數與關鍵關聯可驗證。
- [ ] migration 失敗時 SQLite 原資料保持完整。
- [ ] migration result 可區分 success / partial success / failure。
- [ ] 有可重跑的驗證 evidence，而不是只確認 migration script 存在。

## Core Features

- [ ] 使用者可新增 / 修改 / 完成待辦。
- [ ] 待辦可設定日期、優先度、提醒、標籤、專案。
- [ ] Checklist 可使用。
- [ ] 首頁能顯示今日摘要。
- [ ] Phase 1 不需先完成 Today Cockpit / Focus / Plan / Review 主導航重構。

## Calendar

- [ ] Google 登入。
- [ ] 可讀取 Calendar。
- [ ] 可新增。
- [ ] 可修改。
- [ ] 可刪除。
- [ ] Calendar 整合失敗有明確錯誤，且不破壞主資料。
- [ ] 外部失敗不呈現為 full success。

## Gmail

- [ ] 可讀必要 metadata。
- [ ] 可轉待辦。
- [ ] 可轉行程。
- [ ] 可掛到專案。
- [ ] Gmail integration error 可追蹤。

## 專案 / 筆記 / 習慣 / 採買

- [ ] 專案可管理相關資料。
- [ ] 筆記可搜尋。
- [ ] 習慣可重複與記錄完成。
- [ ] 採買可快速新增與勾選。

## 附件

- [ ] 圖片。
- [ ] PDF。
- [ ] 一般文件。
- [ ] 附件 storage reference 不依賴單一手機本機絕對路徑作為中央模型。

## ChatGPT Bridge / MCP Integration

- [ ] ChatGPT Bridge Backend 有明確且版本化的 schema / API contract。
- [ ] Bridge / MCP 可讀取允許分享的 life_assistant context。
- [ ] proposed actions 有 schema 驗證。
- [ ] proposed actions 有適當 confirmation / policy 控制。
- [ ] 重複 request / action 有 idempotency 防重機制。
- [ ] 實際 action 由 life_assistant Backend 執行，不由 ChatGPT / omniAgent 直接寫 PostgreSQL。
- [ ] action result 可回傳並寫入 Activity / execution log。
- [ ] Bridge / MCP Integration 失敗不破壞 PostgreSQL 主資料。
- [ ] 舊 Google Drive Bridge 若保留，需明確標示為相容 / fallback integration。
- [ ] life_assistant 可提供自己的 Capability Catalog / MCP Tool Catalog。

## Project Boundary

- [ ] life_assistant 可在沒有 omniAgent 的情況下獨立完成主要產品流程。
- [ ] LangGraph 不作為 life_assistant 完成條件。
- [ ] Global Tool Registry 不作為 life_assistant 完成條件。
- [ ] Workflow Registry 不作為 life_assistant 完成條件。
- [ ] Agent Runtime / Agent Worker 不作為 life_assistant 完成條件。
- [ ] life_assistant background jobs 不包含 Agent reasoning loop。
- [ ] omniAgent 若呼叫 life_assistant，只透過版本化 MCP / API contract，不依賴內部 DB table 或 private implementation。

## 安全

- [ ] token / secret 不存一般資料表或一般 log。
- [ ] 敏感資訊不進一般 log。
- [ ] Backend authentication / authorization 有明確驗證。
- [ ] destructive / sensitive action 經 life_assistant 最終 permission / policy gate。

## Log / Observability

- [ ] 重要寫入有 Activity / execution log。
- [ ] 外部 API 失敗可追蹤。
- [ ] migration 成功 / 部分成功 / 失敗可區分。
- [ ] AI / Bridge proposed action 與實際 execution result 可區分。
- [ ] partial success 不會被記錄成 full success。
- [ ] runtime / deployment evidence 可追溯到版本或 commit。

## Release Evidence

Phase 1 不可只因文件或程式碼存在就判定完成，至少需有：

- [ ] Flutter Web build evidence。
- [ ] Firebase Hosting dev/test deployment evidence。
- [ ] Cloud Run dev/test deployment evidence。
- [ ] PostgreSQL runtime connectivity / persistence evidence。
- [ ] migration runtime validation evidence。
- [ ] Google integration success/failure evidence。
- [ ] Bridge / MCP validation evidence。
- [ ] tests / CI evidence。

## Phase 1 明確不作為完成條件

以下項目延後，不阻塞目前 Phase 1：

- Android / iOS 正式打包與上架。
- 完整 offline-first 寫入。
- SQLite 作 local cache 的雙向同步。
- 原生本機通知完整驗收。
- Today Cockpit。
- Attention Model / Focus。
- Routine Library。
- Global Capture 完整版。
- Plan / Review。
- Contextual AI entry points。
- People / relationship context。

## Phase 1.5 / Phase 2 Gate

Phase 1 Release Gate 通過後，才進入 Phase 1.5 real-use validation；Phase 2 的實作優先順序應以真實使用 evidence 為依據，而不是直接照參考專案功能表搬運。
