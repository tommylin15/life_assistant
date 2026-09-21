# 生活助理 App v0.1 — Data Model

## 1. 資料模型定位

新的正式目標資料庫為 PostgreSQL。現有 SQLite schema 仍是 migration source，欄位語意原則上保留，避免因架構轉向而重做 domain model。

第一階段建議：

- 保留既有文字型 ID，避免 migration 時重建識別碼。
- SQLite `INTEGER` boolean 對應 PostgreSQL `boolean`。
- 時間欄位優先使用 `timestamptz`。
- JSON 字串欄位可改為 `jsonb`。
- 既有 FTS5 不直接搬移 index，PostgreSQL 搜尋另建索引。

## 2. items

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

- id text PK
- google_event_id text UNIQUE
- calendar_id text
- title text
- starts_at timestamptz
- ends_at timestamptz
- location text
- description text
- last_synced_at timestamptz

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

## 18. activity_logs

- id text PK
- action_type text
- entity_type text NULL
- entity_id text NULL
- summary text
- result text
- created_at timestamptz

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

## 21. 後端 operational tables

新的雲端架構可增加既有 SQLite 沒有的 operational tables，例如：

- scheduled_tasks
- task_executions
- integration_connections
- oauth / credential references（只存 reference，不存明文 secret）
- migration_runs

這些表必須在實作時以 migration 建立；本文件列出的是目標方向，不代表目前 repository 已完成。
