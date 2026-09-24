# 生活助理 App v0.1 文件集

## 專案定位

這是一個以「個人生活執行中樞」為核心的 Flutter 專案。

核心定位：

> **Data + UI + API + Execution + Integration**

`life_assistant` 負責生活資料、使用介面、Backend API、實際操作執行、外部服務整合，以及對 ChatGPT / Agent 提供安全且版本化的 Bridge / MCP 介面。

`life_assistant` **不是**通用 Agent orchestration 平台；LangGraph、Global Tool Registry、Workflow Registry、Agent Runtime、Agent Worker 與跨系統 multi-tool orchestration 由獨立的 `omniAgent` 專案負責。

v0.1 先把日常生活中的：

- 待辦
- 行程
- Gmail 重要事項
- 提醒
- 生活專案
- 習慣／例行事項
- 採買
- 筆記／知識庫
- 附件
- 執行紀錄

集中到單一介面，並透過明確規則與外部整合增加智慧性。

## 目前 Phase 1 技術方向

正式目標架構：

```text
Firebase Hosting
        ↓
Flutter Web / PWA
        ↓
Cloud Run — FastAPI Backend
        ↓
PostgreSQL
```

- Flutter / Dart
- Phase 1 優先 Flutter Web / PWA，不以 Android / iOS 安裝包作為主交付路線
- Firebase Hosting 負責前端 Web/PWA 發布
- Cloud Run 執行 FastAPI Backend
- PostgreSQL 作為新的 operational source of truth
- Google 登入
- Gmail 整合
- Google Calendar 雙向整合
- Google Drive Bridge / Integration
- ChatGPT Bridge Backend
- MCP Server / Capability Catalog
- 單人使用優先
- Android / iOS 封裝延後到 Web/PWA 與 Backend 穩定後

## Release Strategy

目前採以下順序：

### Phase 1 — Platform Release

先完成並上線目前 Web / Cloud 主線：

- Flutter Web / PWA
- FastAPI / Cloud Run
- PostgreSQL
- SQLite → PostgreSQL migration
- Google integrations
- ChatGPT Bridge Backend / MCP baseline
- security / logging / observability

Phase 1 採 **scope freeze**。可持續做未來功能的研究、UX、schema proposal 與 API contract proposal，但不因新的 Life OS 構想持續擴張第一次上線範圍。

### Phase 1.5 — Real-use Validation

上線後以真實使用觀察首頁、提醒、routine、Gmail / Calendar / Task 轉換與跨頁摩擦；先修正 bug、資料一致性與高摩擦流程，再確認下一階段優先順序。

### Phase 2 — Product Enhancement

候選方向依序為：

1. Today Cockpit
2. Attention Model / Focus
3. Routine Library
4. Global Capture
5. Plan
6. Review
7. Contextual AI entry points

詳細方向見 [`doc/future_product_enhancements.md`](doc/future_product_enhancements.md)。

## life_assistant 與 omniAgent 邊界

### life_assistant 負責

- Data / operational source of truth
- UI / Web / PWA
- FastAPI Backend
- 實際 action execution
- Google / Drive / Gmail / Calendar integrations
- ChatGPT Bridge Backend
- MCP Server / Integration API
- life_assistant 自己的 Capability Catalog
- schema validation、permission / confirmation policy、idempotency
- Activity / execution log
- 非 AI reasoning 的一般 background jobs

### omniAgent 負責

- LangGraph / Agent orchestration
- Agent reasoning loop
- Global Tool Registry
- Workflow Registry
- Agent Runtime / Agent Worker
- 跨多系統 tool routing 與 multi-step workflow
- retry / resume / partial-success orchestration

詳細邊界見 [`doc/project_boundary.md`](doc/project_boundary.md)。

## 現有實作與遷移

目前 repository 已有大量原生 Flutter + SQLite 功能與資料模型。這些成果保留，不視為廢棄：

- 現有 SQLite 是既有版本的資料來源與 migration source。
- 不清空或 drop 現有 SQLite 資料。
- 新架構完成後，資料逐步遷移到 PostgreSQL。
- 若未來原生 App 需要離線能力，SQLite 可保留為 local/offline cache，但不再作為全系統中央主資料來源。
- 既有 Google Drive ChatGPT Bridge 可保留作相容或 fallback integration，不代表未來仍以 Drive 檔案交換作唯一 Bridge 方式。

## 文件索引

- `doc/spec.md`：產品與功能規格
- `doc/architecture.md`：技術架構與模組邊界
- `doc/project_boundary.md`：life_assistant / omniAgent 責任邊界
- `doc/data_model.md`：PostgreSQL 目標資料模型與 SQLite 遷移對照
- `doc/migration_spec.md`：SQLite → PostgreSQL 與 schema migration 規格
- `doc/project_structure.md`：Flutter Web / Backend 模組邊界
- `doc/acceptance.md`：目前 Phase 1 驗收條件
- `doc/decisions.md`：目前已確認的重要產品與架構決策
- `doc/progress.md`：既有實作與驗證進度
- `doc/todo.md`：目前工作優先順序
- `doc/wbs.md`：Phase 1 → 1.5 → 2 工作分解
- `doc/future_product_enhancements.md`：上線後 Life OS / Compass 研究吸收方向
- `doc/design_system.md`：UI / UX 與設計系統
- `doc/integrations.md`：Google / Drive / Bridge / MCP 整合
- `doc/security.md`、`doc/permissions.md`：權限、安全與隱私規格
- `doc/coding_rules.md`：開發規則與 Definition of Done

## Phase 1 成功標準

1. 使用者可從手機或電腦瀏覽器開啟 Flutter Web / PWA。
2. 前端可透過 FastAPI Backend 讀寫核心資料。
3. PostgreSQL 可可靠保存 operational data。
4. 既有 SQLite 資料有明確 migration 路徑，且不因遷移被破壞。
5. Google Calendar / Gmail 整合失敗時，有明確錯誤與可追蹤 Log。
6. 所有重要操作都有 Activity / execution 記錄。
7. ChatGPT Bridge Backend / MCP 能在不繞過 life_assistant 權限與 validation 的前提下讀取或提出操作。
8. life_assistant 可獨立完成，不以 omniAgent 的 LangGraph / Agent Runtime 完成為前置條件。
9. Web/PWA 穩定後，再評估 Android / iOS 原生封裝與 SQLite offline cache。
10. Today / Focus / Routine Library 等 Phase 2 強化功能**不作為 Phase 1 上線條件**。
