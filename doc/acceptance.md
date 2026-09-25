# 生活助理 App v0.1 — Acceptance Criteria

最後更新：2026-09-25

> 本文件定義 **Phase 1 Platform Release** 的完成條件。Phase 2 的 Today / Focus / Routine Library / Global Capture 等強化功能不屬於目前 Release Gate。
>
> `[x]` 只代表已有足夠的 implementation / CI / deployment / runtime evidence；外部整合若尚未以真實帳號驗收，仍維持 `[ ]`。

## Phase 1 Web / Cloud 核心

- [x] Flutter Web 可正常 build。
- [x] 前端可透過 Firebase Hosting 發布到 dev / test 環境。
- [x] FastAPI Backend 可部署到 Cloud Run dev / test 環境。
- [x] Flutter Web 可透過 Backend API 讀取與寫入 Task 核心資料。
- [x] PostgreSQL 可建立 schema 並持久保存 Task operational data。
- [x] Web 主線不直接連 PostgreSQL；透過 Backend API 存取。
- [ ] Backend API 錯誤有一致格式與可追蹤 execution log。
- [ ] 手機與電腦瀏覽器皆完成主要介面驗收。
- [x] PWA 可加入手機主畫面 baseline，且 icon / manifest 已完成實際安裝修正。

## SQLite Migration

- [x] 既有 SQLite 資料與 legacy implementation 保留，未因 Cloud 主線被清空或 drop。
- [ ] 可從目前最新 SQLite schema 匯出核心資料供 Cloud migration。
- [ ] 可匯入 PostgreSQL dev / test schema。
- [ ] migration 重跑不造成重複資料。
- [ ] 主表筆數與關鍵關聯可驗證。
- [ ] migration 失敗時 SQLite 原資料保持完整。
- [ ] migration result 可區分 success / partial success / failure。
- [ ] 有可重跑的 migration runtime evidence，而不是只確認 migration script 存在。

## Core Features

- [x] 使用者可在 Web 主線新增 / 修改 / 完成 / 刪除待辦。
- [ ] Web 主線待辦完整支援日期、優先度、提醒、標籤、專案並完成 UX 驗收。
- [ ] Checklist 在 Web / Backend 主線可使用。
- [ ] Web 首頁能顯示完整今日摘要。
- [x] Phase 1 不需先完成 Today Cockpit / Focus / Plan / Review 主導航重構。

## Calendar

- [x] Google 登入。
- [ ] 可讀取 Calendar，且真實帳號 runtime 驗收 PASS。
- [ ] 可新增 Calendar event，且真實帳號 runtime 驗收 PASS。
- [ ] 可修改 Calendar event。
- [ ] 可刪除 Calendar event。
- [ ] Calendar 整合失敗有明確錯誤與 execution evidence，且不破壞主資料。
- [ ] 外部失敗不呈現為 full success。

> 目前 implementation 已有 Calendar read / create；因真實帳號 integration acceptance 尚未在本文件同步時取得完整 PASS evidence，所以仍未勾選最終驗收項目。

## Gmail

- [ ] 可讀必要 metadata，且真實帳號 runtime 驗收 PASS。
- [ ] 可轉待辦。
- [ ] 可轉行程。
- [ ] 可掛到專案。
- [ ] Gmail integration error 可追蹤到 execution evidence。

> Gmail metadata API 已實作並部署；最終 acceptance 仍等待真實帳號 runtime 驗收。

## Google Drive Integration

- [ ] `life_assistant/ChatGPT_Bridge` 可由 Backend 以 `drive.file` scope 建立或確認，且真實帳號 runtime 驗收 PASS。
- [x] Web UI 只在使用者明確操作時才執行 Drive Bridge ensure。
- [x] 不使用全 Drive scope 作為第一批 baseline。

## 專案 / 筆記 / 習慣 / 採買

- [ ] Project Cloud Backend CRUD 可管理相關資料。
- [ ] Note Cloud Backend 可搜尋。
- [ ] Habit Cloud Backend 可重複與記錄完成。
- [ ] Shopping Cloud Backend 可快速新增與勾選。

> 上述功能在 legacy Flutter + SQLite 已有既有資產，但不得因此視為新的 Cloud Backend / PostgreSQL acceptance 已完成。

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
- [x] 舊 Google Drive Bridge 明確定位為相容 / fallback integration。
- [ ] life_assistant 提供完整自己的 Capability Catalog / MCP Tool Catalog。

> 第一批 Google capability metadata 已有 `name/version/risk/confirmation` baseline，但尚不足以視為完整 MCP / Integration Catalog Release Gate。

## Project Boundary

- [x] life_assistant 的 Phase 1 主線不以 omniAgent 完成為前置條件。
- [x] LangGraph 不作為 life_assistant 完成條件。
- [x] Global Tool Registry 不作為 life_assistant 完成條件。
- [x] Workflow Registry 不作為 life_assistant 完成條件。
- [x] Agent Runtime / Agent Worker 不作為 life_assistant 完成條件。
- [x] life_assistant background jobs 不包含通用 Agent reasoning loop。
- [ ] omniAgent 實際呼叫 life_assistant 時，只透過版本化 MCP / API contract，不依賴內部 DB table 或 private implementation。

## 安全

- [x] Google access / refresh token 不以 plaintext 存一般資料表；Backend 使用 encrypted token storage baseline。
- [x] Google OAuth error log 不直接輸出 client secret / token，並使用 machine-readable error category baseline。
- [x] Backend authentication 有 Google identity + protected API baseline。
- [ ] Backend authorization / minimum-permission policy 完整驗證。
- [ ] destructive / sensitive action 經 life_assistant 最終 permission / policy gate。

## Log / Observability

- [ ] 重要寫入有 Activity / execution log。
- [ ] 外部 API 失敗可追蹤到 execution record。
- [ ] migration 成功 / 部分成功 / 失敗可區分。
- [ ] AI / Bridge proposed action 與實際 execution result 可區分。
- [ ] partial success 不會被記錄成 full success。
- [x] deployment evidence 可追溯到 GitHub commit / workflow run。

## Release Evidence

Phase 1 不可只因文件或程式碼存在就判定完成，至少需有：

- [x] Flutter Web build evidence。
- [x] Firebase Hosting dev/test deployment evidence。
- [x] Cloud Run dev/test deployment evidence。
- [x] PostgreSQL runtime connectivity / Task persistence evidence。
- [ ] migration runtime validation evidence。
- [ ] Google integration success/failure evidence（Gmail / Calendar / Drive 真實帳號完整驗收）。
- [ ] Bridge / MCP validation evidence。
- [x] tests / CI pipeline evidence。

## 2026-09-25 Evidence Snapshot

- Firebase Hosting workflow run #62：PASS，commit `1da5c1c0044a14406ff94896a04d994fcf48fd82`。
- Cloud Run workflow run #116：PASS，同一 commit。
- 使用者互動驗收：Google 登入 PASS、Task CRUD PASS。
- Google integration APIs：Gmail metadata / Calendar read+create / Drive Bridge implementation 已部署；完整真實帳號 integration acceptance 尚未完成。

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
