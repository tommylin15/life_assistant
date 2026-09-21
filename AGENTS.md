# AGENTS.md — Life Assistant

這是「生活助理 App v0.1」的代理人工作指引。正式專案規則以 [`doc/PROJECT_RULES.md`](doc/PROJECT_RULES.md) 為準；開始任何工作前必須先完整閱讀它。

## 工作順序

1. 讀取 `doc/PROJECT_RULES.md`。
2. 讀取與任務直接相關的規格，優先順序如下：
   - `decisions.md`：已確認決策
   - `spec.md`：產品範圍
   - `architecture.md`、`project_structure.md`：架構與邊界
   - `coding_rules.md`：實作與 Definition of Done
   - `migration_spec.md`、`error_handling.md`、`security.md`、`permissions.md`、`bridge_schema.md`、`sync_spec.md`：專項規則
   - `testing_strategy.md`、`release_checklist.md`：驗證與發版門檻
3. 先檢查現有實作、呼叫者與測試，再修改最少必要檔案。
4. 完成後執行適用驗證，並檢查規格是否需要同步更新。

若規格互相衝突，以 `doc/PROJECT_RULES.md` 為最高優先；在其餘產品規格間，依 `decisions.md`、`spec.md`、對應專項規格判斷，無法判斷時停下來指出衝突。

## 專案架構底線

目前正式目標架構：

```text
Firebase Hosting
    ↓
Flutter Web / PWA
    ↓
Cloud Run — FastAPI Backend
    ↓
PostgreSQL
```

- Flutter / Dart 仍為前端主技術，但 Phase 1 以 Web/PWA 為主要交付面。
- PostgreSQL 是新的 operational source of truth；前端不得直接碰資料庫。
- 現有 SQLite 屬既有版本資料與遷移來源；若未來保留原生 App，可降為 local/offline cache。
- UI → Application → Domain；Data / API Client / Integrations 實作 domain interfaces。
- Google、Drive Bridge、通知、語音與其他外部能力都經 adapter / connector。
- schema 變更必須 migration；不得 drop 或清空現有使用者資料。
- Bridge 外部 JSON 必須驗證；未支援 action、錯誤 bridge/schema 或重複 action 不得執行。
- 重要寫入在適用時記錄 Activity Log / execution log；不得記錄 token、PIN、密碼或敏感正文。
- 不把 Firebase Hosting、Cloud Run、PostgreSQL migration、排程、LangGraph 或其他尚未完成能力寫成已實作。
- 未經使用者明確指示，不主動擴大到 Temporal、Iceberg、多人協作或 production 級複雜基礎設施。

## Ponytail 實作風格

- 優先重用現有 helper、型別與模式；其次用 Dart/Flutter/Python 原生能力與既有依賴。
- 不建立只有一個實作的抽象、factory、config 或 speculative scaffolding。
- 修 bug 先追查所有 caller，在共用根因處修一次。
- 非 trivial 邏輯留下最小可執行驗證；不要為一行程式碼建立測試框架。
- 任何刻意接受的效能或正確性上限，用 `ponytail:` 註解寫明上限與升級條件。

## 驗證與 Git

- 優先執行與變更相符的測試、lint、`flutter analyze`、backend tests；若某一層尚未建立，做文件與可執行本機檢查並明確說明。
- 未經明確授權，不部署 production、不建立或擴大付費 GCP 資源。
- 任何 commit 或 push 前，應先完成專案要求的 `/ponytail-review` 或等價人工 review。

## 回報格式

完成回覆至少包含：

- 修改內容
- 驗證結果
- 尚待決定事項或未完成原因

不要把未實作的未來擴充寫成目前功能；契約改變時才更新相關規格文件。
