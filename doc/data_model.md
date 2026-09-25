# 生活助理 App v0.1 — Data Model

最後更新：2026-09-25

## 1. 資料模型定位

新的正式目標資料庫為 PostgreSQL。現有 SQLite schema 仍是 migration source，欄位語意原則上保留，避免因架構轉向而重做 domain model。

第一階段原則：

- 保留既有文字型 ID，避免 migration 時重建識別碼。
- SQLite `INTEGER` boolean 對應 PostgreSQL `boolean`。
- 時間欄位優先使用 `timestamptz`。
- JSON 字串欄位可逐步改為 `jsonb`。
- 既有 FTS5 不直接搬移 index，PostgreSQL 搜尋另建索引。
- operational / integration tables 以 Alembic migration 管理，不以文件存在視為 schema 已部署。

## 2. items / tasks

Cloud Backend 目前已有 Task model / CRUD；legacy SQLite 對應欄位語意如下：

- id text PK
- title text NOT NULL
- note text
- status text NOT NULL
- priority text NOT NULL
- due_at timestamptz NULL
- reminder_at timestamptz NULL
- project_id text NULL
- source_type text
- source_ref text
- created_at timestamptz NOT NULL
- updated_at timestamptz NOT NULL
- completed_at timestamptz NULL
- deleted_at timestamptz NULL

> Cloud Task model 的實際欄位 / migration 以 Backend code + Alembic 為 source of truth；SQLite 欄位仍作 migration mapping 來源。

## 3. checklist_items

- id text PK
- item_id text FK
- title text NOT NULL
- is_done boolean
- sort_order integer
- created_at timestamptz

## 4. projects

- id text PK
- name text NOT NULL
- summary text
- status text
- created_at timestamptz
- updated_at timestamptz

目前 Cloud Backend Project model / CRUD **尚未實作**；legacy SQLite Project 不代表 Cloud Project 已完成。

## 5. notes

- id text PK
- title text
- body text
- project_id text NULL
- created_at timestamptz
- updated_at timestamptz

全文搜尋改以 PostgreSQL full-text search / trigram 等方案評估，不延續 SQLite FTS5 index 本身。

## 6. note_links

- source_note_id text
- target_note_id text

## 7. habits

- id text PK
- title text
- recurrence_rule text
- reminder_time text NULL
- is_active boolean
- created_at timestamptz

## 8. habit_logs

- id text PK
- habit_id text FK
- completed_at timestamptz

## 9. shopping_lists

- id text PK
- name text
- project_id text NULL
- created_at timestamptz

## 10. shopping_items

- id text PK
- list_id text FK
- name text
- category text
- is_done boolean
- sort_order integer

## 11. tags

- id text PK
- name text UNIQUE

## 12. entity_tags

- entity_type text
- entity_id text
- tag_id text

## 13. attachments

- id text PK
- entity_type text
- entity_id text
- display_name text
- storage_ref text
- mime_type text
- created_at timestamptz

`storage_ref` 取代把本機絕對路徑視為長期中央資料模型的做法；實際附件儲存方式另由 integration / storage 規格定義。

## 14. calendar_events_cache

Legacy / cache mapping：

- id text PK
- google_event_id text UNIQUE
- calendar_id text
- title text
- starts_at timestamptz
- ends_at timestamptz
- location text
- description text
- project_id text NULL
- last_synced_at timestamptz

目前 Cloud Google Calendar API 直接透過 Backend 呼叫 Google Calendar；是否建立 PostgreSQL cache 仍屬後續架構決策。

## 15. gmail_refs

只保存必要 metadata，不長期保存完整郵件正文。

- id text PK
- gmail_message_id text UNIQUE
- thread_id text
- subject text
- sender text
- received_at timestamptz
- snippet text
- linked_entity_type text NULL
- linked_entity_id text NULL
- last_synced_at timestamptz

目前 Cloud Gmail metadata API 可即時讀取；PostgreSQL `gmail_refs` 是否落地仍需配合 migration / cache 策略。

## 16. reminders

- id text PK
- entity_type text
- entity_id text
- scheduled_at timestamptz
- type text
- is_enabled boolean

## 17. templates

- id text PK
- name text
- template_type text
- payload_json jsonb
- created_at timestamptz
- updated_at timestamptz

## 18. legacy activity_logs

Legacy SQLite activity log：

- id text PK
- action_type text
- entity_type text NULL
- entity_id text NULL
- summary text
- result text
- created_at timestamptz

此表屬舊原生資產；新的 Cloud Backend audit baseline 使用 `execution_logs`，兩者在 migration 時需明確區分，不應直接假設相同語意。

## 19. preferences

- key text PK
- value_json jsonb

## 20. bridge_state

- key text PK
- value_json jsonb

用途：

- Bridge ID
- schema version
- last export timestamp
- last import timestamp
- last Drive folder reference

## 21. Google integration operational tables

Cloud Backend 已實作並部署：

### google_connections

用途：保存使用者 Google integration connection metadata 與 encrypted token references/data。

主要欄位 baseline：

- user_sub PK
- email
- encrypted_access_token
- encrypted_refresh_token
- scopes
- access_token_expires_at
- created_at
- updated_at

不得把 token 明文輸出到 API / debug log。

### google_oauth_states

用途：OAuth state validation / expiry。

主要欄位 baseline：

- state_hash PK
- user_sub
- email
- services
- expires_at
- created_at

## 22. execution_logs

Cloud Backend 已於 2026-09-25 建立 operational execution log baseline，並以 Alembic migration 管理。

主要欄位：

- id text PK
- request_id text NOT NULL
- action_id text NULL
- user_sub text NOT NULL
- action_type text NOT NULL
- entity_type text NULL
- entity_id text NULL
- provider text NULL
- status text NOT NULL
- summary text NULL
- result text NULL
- error_category text NULL
- started_at timestamptz NOT NULL
- finished_at timestamptz NULL

用途：

- Task mutation audit
- Google Calendar create/update/delete audit
- Gmail → Task / Calendar audit
- Drive Bridge ensure audit
- failure / partial-success / audit-finalization evidence

原則：

- action 執行前先建立 `running` record；audit start 失敗則 action 不執行。
- 成功後轉 `success` 並記錄 result。
- 失敗後轉 `failure` 並記錄 error category。
- 部分完成可使用 `partial_success`，不得寫成 full success。
- 不保存 token、password 或完整敏感郵件正文。

目前 `/api/v1/activity` 提供 authenticated read baseline。

## 23. 後續 operational tables

仍可依 Phase 1 / Phase 2 需求增加：

- scheduled_tasks
- task_executions（若需要與通用 execution_logs 分離）
- migration_runs
- MCP / Bridge idempotency records
- confirmation / policy decision records

這些仍屬目標方向，除非 repository code + migration + runtime evidence 已存在，否則不得標成完成。

## 24. Source of Truth / Migration 規則

- 目前實際 schema / migration 狀態：以 Backend models + Alembic + runtime evidence 為準。
- legacy SQLite schema：作為資料搬遷來源，不等於 Cloud schema 已完成。
- 文件描述與程式不同時，先保留差異並以 repository implementation 判定現況，再更新文件。
- destructive schema change 必須依工程治理 runbook 取得必要確認與 recovery evidence。
