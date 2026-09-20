# 生活助理 App v0.1 — Data Model

## 1. items

建議欄位：

- id TEXT PK
- title TEXT NOT NULL
- note TEXT
- status TEXT NOT NULL
- priority TEXT NOT NULL
- due_at DATETIME NULL
- reminder_at DATETIME NULL
- project_id TEXT NULL
- source_type TEXT
- source_ref TEXT
- created_at DATETIME NOT NULL
- updated_at DATETIME NOT NULL
- completed_at DATETIME NULL
- deleted_at DATETIME NULL

## 2. checklist_items

- id TEXT PK
- item_id TEXT FK
- title TEXT NOT NULL
- is_done INTEGER
- sort_order INTEGER
- created_at DATETIME

## 3. projects

- id TEXT PK
- name TEXT NOT NULL
- summary TEXT
- status TEXT
- created_at DATETIME
- updated_at DATETIME

## 4. notes

- id TEXT PK
- title TEXT
- body TEXT
- project_id TEXT NULL
- created_at DATETIME
- updated_at DATETIME

全文搜尋建議使用 SQLite FTS5。

## 5. note_links

- source_note_id TEXT
- target_note_id TEXT

## 6. habits

- id TEXT PK
- title TEXT
- recurrence_rule TEXT
- reminder_time TEXT NULL
- is_active INTEGER
- created_at DATETIME

## 7. habit_logs

- id TEXT PK
- habit_id TEXT FK
- completed_at DATETIME

## 8. shopping_lists

- id TEXT PK
- name TEXT
- project_id TEXT NULL
- created_at DATETIME

## 9. shopping_items

- id TEXT PK
- list_id TEXT FK
- name TEXT
- category TEXT
- is_done INTEGER
- sort_order INTEGER

## 10. tags

- id TEXT PK
- name TEXT UNIQUE

## 11. entity_tags

- entity_type TEXT
- entity_id TEXT
- tag_id TEXT

## 12. attachments

- id TEXT PK
- entity_type TEXT
- entity_id TEXT
- display_name TEXT
- local_path TEXT
- mime_type TEXT
- created_at DATETIME

## 13. calendar_events_cache

- id TEXT PK
- google_event_id TEXT UNIQUE
- calendar_id TEXT
- title TEXT
- starts_at DATETIME
- ends_at DATETIME
- location TEXT
- description TEXT
- last_synced_at DATETIME

## 14. gmail_refs

只保存必要 metadata，不建議在 SQLite 長期保存完整郵件正文。

- id TEXT PK
- gmail_message_id TEXT UNIQUE
- thread_id TEXT
- subject TEXT
- sender TEXT
- received_at DATETIME
- snippet TEXT
- linked_entity_type TEXT NULL
- linked_entity_id TEXT NULL
- last_synced_at DATETIME

## 15. reminders

- id TEXT PK
- entity_type TEXT
- entity_id TEXT
- scheduled_at DATETIME
- type TEXT
- is_enabled INTEGER

## 16. templates

- id TEXT PK
- name TEXT
- template_type TEXT
- payload_json TEXT
- created_at DATETIME
- updated_at DATETIME

## 17. activity_logs

- id TEXT PK
- action_type TEXT
- entity_type TEXT NULL
- entity_id TEXT NULL
- summary TEXT
- result TEXT
- created_at DATETIME

## 18. preferences

- key TEXT PK
- value_json TEXT

## 19. bridge_state

- key TEXT PK
- value_json TEXT

用途：

- Bridge ID
- schema version
- last export timestamp
- last import timestamp
- last Drive folder reference
