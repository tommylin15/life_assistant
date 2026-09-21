# 生活助理 App v0.1 — Migration Specification

## 1. 目標

目前 repository 已有 SQLite schema 與既有資料；新的正式目標資料庫改為 PostgreSQL。

本文件規範：

1. 現有 SQLite schema migration 必須繼續安全維護，直到資料搬遷完成。
2. SQLite → PostgreSQL 必須有可驗證的 migration 流程。
3. PostgreSQL 上線後，後續 schema change 使用 PostgreSQL migration 管理。

## 2. 基本原則

- 不允許為了轉向新架構而 drop 或清空既有 SQLite database。
- migration 必須可測試。
- migration 前必須保留可恢復來源。
- 同一筆資料必須有穩定 ID，避免重複匯入。
- migration 必須產生 summary / error log，但不得記錄 token、PIN、密碼或敏感正文。
- 在驗證完成前，不把 PostgreSQL 宣告成已完成 migration。

## 3. SQLite 既有 migration

在切換完成前，既有 SQLite schema version 仍維持整數版本：

```text
1, 2, 3...
```

SQLite schema change 仍需：

- from_version
- to_version
- migration code
- rollback / recovery strategy（若可行）
- migration test

不得以 drop database 取代 migration。

## 4. SQLite → PostgreSQL 遷移流程

建議流程：

```text
Backup SQLite
↓
Read / validate source schema version
↓
Extract entities in deterministic order
↓
Transform SQLite-specific values/types
↓
Upsert into PostgreSQL staging / target tables
↓
Verify row counts + key relationships + critical fields
↓
Record migration result
↓
Switch read path only after verification
```

至少驗證：

- 主表筆數
- primary / foreign key 關係
- soft-delete 狀態
- created_at / updated_at / completed_at 等時間欄位
- checklist / tags / project 關聯
- note links
- reminders
- activity logs
- Google integration reference IDs

## 5. 型別轉換原則

- SQLite `TEXT` ID → PostgreSQL `text` 或 `uuid`，第一階段優先保留既有 ID，避免資料重建。
- SQLite `INTEGER` boolean → PostgreSQL `boolean`。
- SQLite `DATETIME` / ISO text → PostgreSQL `timestamptz`，統一時區語意。
- JSON 字串欄位可逐步轉 `jsonb`。
- FTS5 不直接搬移 index；PostgreSQL 搜尋策略另外建立並重新索引。

## 6. 切換策略

優先採可逆切換：

1. 建立 PostgreSQL schema。
2. 執行 migration / backfill。
3. 做一致性驗證。
4. Backend 先以測試環境讀寫 PostgreSQL。
5. 確認無誤後才切換正式 read/write path。
6. SQLite 保留一段時間作 recovery source，不立即刪除。

## 7. 失敗處理

若 migration 失敗：

- 不清除 SQLite 原資料。
- 不將失敗或部分完成標記為成功。
- 保留錯誤摘要與可重跑資訊。
- 若 PostgreSQL 已寫入部分資料，重跑必須透過穩定 ID / upsert 避免重複。

## 8. PostgreSQL 後續 migration

PostgreSQL 成為正式 source of truth 後：

- 每次 schema change 必須有版本化 migration。
- migration 必須先在 dev / test 驗證。
- destructive change 必須先確認備份與回退策略。
- 不允許 production 上手動改 schema 後不留 migration。

## 9. Acceptance

- 可從目前 SQLite 最新 schema 安全匯出。
- 可完整匯入 PostgreSQL 測試環境。
- 重跑 migration 不造成重複資料。
- 關聯與關鍵欄位驗證通過。
- migration 中斷不毀損 SQLite 原資料。
- PostgreSQL schema 有可持續維護的 migration 機制。
