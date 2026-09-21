# 生活助理 App v0.1 — Confirmed Decisions

## 目前已確認

- Flutter / Dart 繼續作為主要前端技術。
- Phase 1 優先 Flutter Web / PWA，不以 Android / iOS 安裝包為主要交付方式。
- Flutter Web / PWA 由 Firebase Hosting 發布。
- Backend 採 Python FastAPI，部署於 Cloud Run。
- PostgreSQL 作為新的 operational source of truth。
- 前端不直接存取 PostgreSQL。
- 現有 SQLite 保留為既有版本資料與 migration source；若未來原生 App 需要離線能力，可保留為 local/offline cache。
- Android / iOS 原生封裝延後到 Web/PWA 與 Backend 穩定後。
- 不使用 Firestore 作為主 operational database。
- 不把 Iceberg 當第一階段 operational DB。
- 單人版優先。
- Google 登入。
- Gmail：讀取 + 轉待辦 + 必要時轉 Calendar。
- Google Calendar：完整雙向整合。
- Google Drive：保留作為 Bridge / Integration 能力，但不再承擔中央資料來源角色。
- 重要操作需保留 Activity / execution log。
- Google 權限採最小權限與延遲授權。
- 開發完成需符合 coding_rules.md 與 release_checklist.md。

## 既有實作保留原則

- Repository 目前已有大量 Flutter + SQLite + Android 相關實作，這些成果不刪除、不假裝不存在。
- SQLite schema 與資料不得為了轉向雲端架構而直接 drop 或清空。
- SQLite → PostgreSQL 必須有明確、可驗證的 migration 路徑。
- 現有 local-first / offline-first 行為在 migration 期間仍屬既有版本能力；新的 Web/PWA Phase 1 不要求完整離線寫入。

## 後續階段才考慮

- Cloud Scheduler / Dispatcher
- Worker / Agent Runtime
- Tool Registry / Workflow Registry
- LangGraph
- MCP / Plugin 擴充
- Android / iOS 正式封裝
- SQLite local/offline cache 同步機制
- Temporal / Iceberg 等 durable / analytics infrastructure

## 明確取消的舊決策

以下舊決策不再作為目前架構基準：

- `SQLite only for v0.1 primary app data`
- `不使用 GCP backend`
- `SQLite 為 source of truth，Drive 僅為交換層`
- `原生手機 App 優先於 Web/PWA`

這些內容可作為歷史背景理解，但後續新實作應以本文件與 `PROJECT_RULES.md` 的最新架構為準。
