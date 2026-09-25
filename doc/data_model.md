# 生活助理 App v0.1 — Data Model

最後更新：2026-09-25

## 1. 定位與 Source of Truth

正式目標資料庫為 PostgreSQL；legacy Flutter SQLite schema v3 保留作 migration source。實際 Cloud schema / migration 狀態以 `backend/app/models`、Alembic revisions 與 runtime evidence 為準。

原則：

- migration 優先保留 stable text IDs。
- 時間欄位使用 timezone-aware timestamp 語意。
- SQLite FTS5 index 不直接搬到 PostgreSQL。
- operational / integration tables 必須版本化管理。
- 文件描述不代表 table 已實際部署；code + migration + evidence 才能判定。

## 2. Cloud `tasks`

目前已實作並有互動 CRUD evidence。

主要欄位：

- `id` varchar(36) PK
- `title` varchar(500) NOT NULL
- `note` text NULL
- `status` varchar(20)
- `priority` varchar(10)
- `due_at` timestamptz NULL
- `reminder_at` timestamptz NULL
- `project_id` varchar(36) NULL
- `created_at` timestamptz
- `updated_at` timestamptz

注意：目前 `project_id` 為 application-level reference，尚未建立 DB foreign key；Project delete API 會先檢查 linked Task 並在有關聯時回 409。

## 3. Cloud `projects`

2026-09-25 已實作；commit `0ea1d1fad596bcce4683df82b7d68caa4d7e42be`。

主要欄位：

- `id` varchar(36) PK
- `name` varchar(500) NOT NULL
- `summary` text NULL
- `status` varchar(32) NOT NULL，default `active`
- `created_at` timestamptz
- `updated_at` timestamptz

Indexes：

- `ix_projects_status`
- `ix_projects_name`

Migration：`20260925_0003_projects`，down revision `20260925_0002`。

Evidence：Alembic chain CI validation PASS、Cloud Run deploy PASS。部署流程目前沒有 production `alembic upgrade` evidence，因此 production Alembic apply 狀態為 NOT VERIFIED；Cloud startup 仍有 additive `Base.metadata.create_all` transitional safety net。

## 4. Legacy SQLite domain mapping

以下 table 仍是 migration source / existing assets；除另有 Cloud model 說明外，不代表已完成 PostgreSQL target schema。

### `items`

對應 Cloud `tasks`。Legacy 額外語意包含 `source_type`、`source_ref`、`completed_at`、`deleted_at` 等，完整 migration mapping 尚未完成。

### `checklist_items`

- id
- item_id
- title
- is_done
- sort_order
- created_at

Cloud target：尚未完成。

### `projects`

Legacy 與 Cloud 皆有 target；stable IDs 應優先保留。

### `notes` / `note_links`

- notes：id, title, body, project_id, created_at, updated_at
- note_links：source_note_id, target_note_id
- legacy FTS5 不直接搬 index

Cloud target：尚未完成。

### `habits` / `habit_logs`

Cloud target：尚未完成。

### `shopping_lists` / `shopping_items`

Cloud target：尚未完成。

### `tags` / `entity_tags`

Cloud target：尚未完成。

### `attachments`

Legacy 使用 local path；Cloud 目標應改用 central `storage_ref` / equivalent，不把單一裝置絕對路徑當中央資料模型。

Cloud target：尚未完成。

### `calendar_events_cache`

Legacy cache table 可保留作 migration/reference；目前 Cloud Calendar 能力直接由 Backend 呼叫 Google Calendar，是否建立 PostgreSQL cache 仍待架構決策。

### `gmail_refs`

只應保存必要 metadata，不長期鏡像完整郵件正文。Cloud Gmail API 目前可直接即時讀 metadata；是否持久化 cache 仍待決策。

### `reminders`

Cloud target：尚未完成。

### `templates`

Cloud target：尚未完成。

### `activity_logs`

Legacy SQLite activity log 與新的 Cloud `execution_logs` 不應直接視為相同 table；migration 時須定義語意轉換。

### `preferences` / `bridge_state`

Cloud target / migration strategy：尚未完成。

## 5. Google Integration Operational Tables

### `google_connections`

已實作。

主要欄位：

- `user_sub` PK
- `email`
- `encrypted_access_token`
- `encrypted_refresh_token`
- `scopes`
- `access_token_expires_at`
- `created_at`
- `updated_at`

Token 不得以 plaintext 輸出至一般 API / log。

### `google_oauth_states`

已實作，用於 state validation / expiry。

主要欄位：

- `state_hash` PK
- `user_sub`
- `email`
- `services`
- `expires_at`
- `created_at`

## 6. Cloud `execution_logs`

已實作；migration `20260925_0002_execution_logs`。

主要欄位：

- id PK
- request_id
- action_id NULL
- user_sub
- action_type
- entity_type / entity_id NULL
- provider NULL
- status
- result NULL
- error_category NULL
- summary NULL
- started_at
- finished_at NULL

目前 audit 對象：

- Task create/update/complete/delete
- Project create/update/delete
- Calendar create/update/delete
- Gmail → Task / Calendar / Project
- Drive Bridge ensure

狀態語意：`running`、`success`、`failure`、必要時 `partial_success`。

## 7. Alembic Chain

目前版本：

1. `20260925_0001_google_integrations`
2. `20260925_0002_execution_logs`
3. `20260925_0003_projects`

CI 會驗證 migration SQL chain。正式 production migration runner / job 尚待完成；目前 Cloud Run startup 有 additive create-all safety net。

## 8. Full Migration Target Readiness

| Domain | Cloud target |
|---|---|
| Task | ✅ 已有 |
| Project | ✅ 已有 |
| Execution audit | ✅ 已有 |
| Google integration operational data | ✅ 已有 |
| Checklist | ❌ 尚缺 |
| Notes / Links / search | ❌ 尚缺 |
| Habits / logs | ❌ 尚缺 |
| Shopping | ❌ 尚缺 |
| Tags | ❌ 尚缺 |
| Attachments | ❌ 尚缺 |
| Reminders | ❌ 尚缺 |
| Templates | ❌ 尚缺 |
| Preferences / Bridge state | ❌ 尚缺 / 待策略 |

因此完整 SQLite → PostgreSQL migration 尚不可宣告 READY/DONE。下一階段應先補其餘必要 Cloud target schema，再實作 deterministic export/import/upsert 與 verification。

## 9. Migration / Integrity Rules

- 不 drop / 清空 legacy SQLite source。
- stable ID 優先。
- 重跑需 idempotent。
- row counts、keys、relationships、critical timestamps 必須驗證。
- partial success 不得寫成 success。
- destructive schema change 需依工程治理 runbook 取得必要確認與 recovery evidence。
