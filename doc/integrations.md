# 生活助理 App v0.1 — Integrations

## 1. Google Sign-In

用途：

- 身分識別
- Gmail 授權
- Calendar 授權
- Drive Bridge 授權

要求：

- 採最小權限原則
- scope 分項請求
- 清楚顯示使用目的
- 支援重新授權
- 支援斷線 / revoke 後的降級模式

---

## 2. Gmail

### v0.1

- 取得郵件必要 metadata
- 顯示摘要
- 一鍵轉待辦
- 一鍵轉行程
- 掛到專案

### 不做

- App 內寄信
- App 內回信
- 自建 Mail Client
- Gmail 全文長期鏡像

---

## 3. Google Calendar

### v0.1

- 讀取
- 建立
- 修改
- 刪除
- 本機 / Backend 快取策略依目前架構實作
- Gmail / Item 轉行程

### 衝突策略

- 遠端修改與本機／Backend 修改同時存在時，應提示或依明確 policy 處理
- 不應靜默覆蓋
- 刪除動作需確認或符合明確 policy

---

## 4. ChatGPT Bridge Backend

ChatGPT Bridge Backend 屬於 life_assistant，目的在於讓 ChatGPT 或其他授權 client 安全地讀取 life_assistant context、提出 proposed actions，並由 life_assistant Backend 執行。

核心責任：

- context read / export
- proposed action contract
- schema validation
- request / action idempotency
- permission / confirmation policy
- action execution
- action result
- Activity / execution log

ChatGPT Bridge Backend 不等於 LangGraph Agent，也不負責跨系統 reasoning orchestration。

---

## 5. MCP / Integration API

life_assistant 可提供 MCP Server 或等價 Integration API，對外暴露自己的能力，例如：

- task.list / create / update / complete
- calendar.list / create / update
- note.search / create
- project.get
- activity.list

life_assistant 只維護自己的 Capability Catalog / MCP Tool Catalog，包括：

- tool name
- version
- input / output schema
- required permission
- risk / confirmation requirement
- idempotency contract
- error contract

跨產品的 Global Tool Registry、Workflow Registry、Agent Runtime 與 Agent Worker 不在本專案，由 `omniAgent` 負責。

---

## 6. Google Drive Bridge（Legacy / Fallback）

### 6.1 目的

既有 Google Drive Bridge 保留作為相容 / fallback integration，讓 App 與 ChatGPT 在沒有直接 MCP / Backend integration 時交換結構化資料。

Drive Bridge 不再是新架構的中央資料來源，也不是唯一 ChatGPT integration 方法。

### 6.2 預設路徑

```text
生活助理/
└── ChatGPT_Bridge/
    ├── README.md
    ├── bridge_manifest.json
    ├── current_state.json
    ├── inbox.json
    ├── projects.json
    ├── pending_actions.json
    └── history/
```

### 6.3 bridge_manifest.json

至少包含：

- bridge_id
- schema_version
- app_version
- exported_at

### 6.4 life_assistant → Drive

輸出可包含：

- 今日狀態
- 近期待辦
- 近期行程
- 等待中事項
- 進行中專案
- 使用者指定上下文

### 6.5 ChatGPT → Drive

可寫入：

- proposed_actions
- summaries
- recommendations

### 6.6 匯入規則

所有 proposed actions 必須：

1. schema 驗證
2. permission / policy 驗證
3. 顯示預覽或依 policy 決定是否需要確認
4. 由 life_assistant 執行
5. 寫入 Activity / execution log
6. 產生 execution result

不得讓 ChatGPT 或 omniAgent 直接繞過 life_assistant Backend / policy 寫入 PostgreSQL。

---

## 7. ChatGPT Onboarding

App 可提供「ChatGPT Bridge / MCP 設定」入口。

可能狀態：

- Backend / MCP：Available / Unavailable
- Google Drive fallback：Connected / Not connected
- Bridge Folder：Ready / Missing
- ChatGPT integration：Not verified / Verified

舊 Google Drive Bridge 的測試流程可以保留，但應明確標示為 fallback / compatibility path。

---

## 8. Share Bridge

提供：

- 複製文字
- 複製 JSON
- 系統分享

用途：

- MCP / Backend integration 尚未設定時
- Google Drive Bridge 未設定時
- 緊急 fallback
- 使用者只想分享單一事項時

---

## 9. Local Folder ↔ Google Drive Folder Sync

既有同步能力可保留；其是否繼續作為 Phase 1 主功能，需依 Web / Backend 架構與實際需求驗證。

核心規則仍應遵守：

- 不靜默覆蓋衝突
- destructive sync 需可追蹤
- PostgreSQL 主資料與 Bridge / sync 檔案角色不得混淆

完整舊規格見 `sync_spec.md`。

---

## 10. ChatGPT Bridge JSON Contract

既有 Drive Bridge JSON schema、action registry、版本相容與驗證規則見：

`bridge_schema.md`

該文件保留作既有 Drive Bridge contract；若其中出現「SQLite 是主資料來源」等舊架構描述，屬 legacy context。

目前正式 source of truth 與 integration 邊界以：

- `PROJECT_RULES.md`
- `decisions.md`
- `architecture.md`
- `project_boundary.md`

為準。

實作時不得以 README prose 取代 schema 驗證。
