# 生活助理 App v0.1 — Testing Strategy

## 1. Unit Tests

至少覆蓋：

- Quick input parser
- Rule engine
- Priority sorting
- Date handling
- Bridge schema validator
- Sync change detection
- Conflict detection
- Backup metadata
- Migration

## 2. Repository Tests

- Task CRUD
- Project CRUD
- Notes FTS
- Habit recurrence
- Activity log
- Preferences

## 3. Integration Tests

### Google

- Sign-in
- Calendar read/create/update/delete
- Gmail metadata
- Drive folder access

### Sync

- Initial Drive → Local
- Local modify → Drive
- Drive modify → Local
- Local delete → Drive delete
- Drive delete → Local delete
- Both modify → conflict
- Delete vs modify → conflict
- Partial failure

### Bridge

- valid actions
- invalid bridge_id
- unsupported action
- duplicate action
- schema mismatch
- action result generation

## 4. UI Tests

核心流程：

```text
Open App
→ Dashboard
→ Create Task
→ Edit
→ Complete
→ Log visible
```

以及：

```text
Gmail item
→ Convert to Task
```

```text
Drive Bridge
→ Import Proposed Actions
→ Review
→ Accept
```

## 5. Offline Tests

- 開飛航仍能管理本機資料
- 離線編輯 Markdown
- 離線建立待辦
- 網路恢復後手動同步

## 6. Release Gate

P0 測試不得有 known blocker。
