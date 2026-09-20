# 生活助理 App v0.1 — SQLite Migration Specification

## 1. 原則

- 所有 schema change 必須有 migration
- 不允許開發期習慣性 drop database
- migration 必須可測試
- backup restore 必須知道 schema version

## 2. Versioning

使用整數版本：

```text
1, 2, 3...
```

每次 migration：

- from_version
- to_version
- SQL / migration code
- rollback strategy（若可行）
- migration test

## 3. 啟動流程

```text
Open DB
↓
Read user_version
↓
Run sequential migrations
↓
Verify schema
↓
Start App
```

若 migration 失敗：

- 不繼續啟動到可寫狀態
- 保留原 DB
- 顯示可恢復錯誤
- 提供備份 / 匯出選項

## 4. Data Safety

高風險 migration 前：

- 自動建立本機 migration backup
- 成功後才更新 schema version

## 5. Acceptance

- 可從 v1 連續升到最新版
- migration 中斷不毀損主 DB
- migration tests 覆蓋主要版本鏈
