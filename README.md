# 生活助理 App v0.1 文件集

## 專案定位

這是一個以「個人生活執行中樞」為核心的 Flutter 專案。

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
- 單人使用優先
- Android / iOS 封裝延後到 Web/PWA 與 Backend 穩定後

## 現有實作與遷移

目前 repository 已有大量原生 Flutter + SQLite 功能與資料模型。這些成果保留，不視為廢棄：

- 現有 SQLite 是既有版本的資料來源與 migration source。
- 不清空或 drop 現有 SQLite 資料。
- 新架構完成後，資料逐步遷移到 PostgreSQL。
- 若未來原生 App 需要離線能力，SQLite 可保留為 local/offline cache，但不再作為全系統中央主資料來源。

## 文件索引

- `doc/spec.md`：產品與功能規格
- `doc/architecture.md`：技術架構與模組邊界
- `doc/data_model.md`：PostgreSQL 目標資料模型與 SQLite 遷移對照
- `doc/migration_spec.md`：SQLite → PostgreSQL 與 schema migration 規格
- `doc/project_structure.md`：Flutter Web / Backend 模組邊界
- `doc/acceptance.md`：目前 Phase 1 驗收條件
- `doc/decisions.md`：目前已確認的重要產品與架構決策
- `doc/progress.md`：既有實作與驗證進度
- `doc/design_system.md`：UI / UX 與設計系統
- `doc/integrations.md`：Google / Drive / Bridge 整合
- `doc/security.md`、`doc/permissions.md`：權限、安全與隱私規格
- `doc/coding_rules.md`：開發規則與 Definition of Done

## Phase 1 成功標準

1. 使用者可從手機或電腦瀏覽器開啟 Flutter Web / PWA。
2. 前端可透過 FastAPI Backend 讀寫核心資料。
3. PostgreSQL 可可靠保存 operational data。
4. 既有 SQLite 資料有明確 migration 路徑，且不因遷移被破壞。
5. Google Calendar / Gmail 整合失敗時，有明確錯誤與可追蹤 Log。
6. 所有重要操作都有 Activity / execution 記錄。
7. Web/PWA 穩定後，再評估 Android / iOS 原生封裝與 SQLite offline cache。
