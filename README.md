# 生活助理 App v0.1 文件集

## 專案定位

這是一個以「個人生活執行中樞」為核心的 Flutter App。

v0.1 目標不是做一個通用 AI 聊天 App，而是先把日常生活中的：

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

集中到單一 App，並透過明確規則與 ChatGPT Bridge 增加智慧性。

## v0.1 技術原則

- Flutter
- Dart
- Local-first
- SQLite 為 App 主資料來源
- 不使用自建 GCP 後端
- Google 登入
- Gmail 整合
- Google Calendar 雙向整合
- Google Drive Bridge
- 本機通知
- 不內建 OpenAI API
- 不依賴 Iceberg
- 單人使用
- 多裝置僅限 Google 原生資料同步

## 文件索引

- `spec.md`：產品與功能規格
- `wbs.md`：工作分解結構
- `todo.md`：開發待辦與優先順序
- `ui.md`：UI / UX 規格
- `design_system.md`：色票、字體、間距、元件與 Markdown Editor 設計系統
- `architecture.md`：技術架構與模組邊界
- `data_model.md`：SQLite 資料模型
- `integrations.md`：Gmail / Calendar / Drive / ChatGPT Bridge 整合
- `sync_spec.md`：手機資料夾 ↔ Google Drive 雙向同步規格
- `bridge_schema.md`：ChatGPT ↔ Drive ↔ App JSON 協議與 Action Schema
- `security.md`：權限、安全與隱私規格
- `acceptance.md`：v0.1 驗收條件
- `decisions.md`：目前已確認的重要產品決策

## v0.1 成功標準

1. 使用者能每天打開 App 快速知道「今天有哪些事情要注意」。
2. 待辦、行程、提醒、郵件衍生事項可集中管理。
3. App 在沒有網路時，核心本機功能仍可使用。
4. Google Calendar / Gmail 整合失敗時，不影響 SQLite 本機資料。
5. 使用者能把 App 狀態透過 Google Drive Bridge 交給 ChatGPT 分析。
6. 所有重要操作都有簡化 Activity Log。
- `project_structure.md`：Flutter 資料夾結構、模組邊界、Repository / Use Case / Adapter 規則
- `migration_spec.md`：SQLite schema migration 與資料安全規格
- `error_handling.md`：錯誤分類、重試與使用者提示規格
- `testing_strategy.md`：單元、整合、UI、離線與 release gate 測試策略
- `permissions.md`：Google OAuth 與裝置權限策略
- `release_checklist.md`：v0.1 發版檢查清單
- `coding_rules.md`：Codex / 開發者實作規則與 Definition of Done
