# 生活助理 App v0.1 — WBS

## 0. 專案初始化

### 0.1 Flutter 專案
- 建立專案
- 套件結構
- Lint
- 環境設定
- Build flavors（如需要）

### 0.2 基礎架構
- Routing
- State management
- Repository pattern
- Error handling
- Logging
- Theme tokens

---

## 1. SQLite 與 Domain

### 1.1 Database
- migration
- repository
- seed data
- backup / restore

### 1.2 Domain
- Item
- Project
- Note
- Habit
- Shopping
- Attachment
- Template
- ActivityLog
- Preference

---

## 2. UI Foundation

### 2.1 Theme
- 溫暖手帳
- 極簡清爽
- 深色夜間

### 2.2 Common Components
- Cards
- Empty state
- Error state
- Section header
- Tag chips
- Priority indicator
- Date selector
- Attachment picker

---

## 3. Dashboard

- 智慧摘要
- 快捷列
- 待辦區
- 行程區
- 提醒區
- 等待中
- 區塊開關
- 規則式排序
- 規則式建議

---

## 4. Tasks

- CRUD
- Priority
- Status
- Due date
- Reminder
- Checklist
- Tags
- Project linking
- Attachments
- Quick input parser
- Search

---

## 5. Calendar

- Google Sign-In
- Calendar OAuth
- Read
- Create
- Update
- Delete
- Cache
- Month view
- Week view
- Conflict handling

---

## 6. Gmail

- Gmail OAuth
- Metadata retrieval
- Summary list
- Convert to task
- Convert to calendar
- Link to project
- Error / revoke handling

---

## 7. Projects

- Project CRUD
- Project Home
- Linked tasks
- Linked events
- Linked notes
- Attachments
- Recent Activity

---

## 8. Notes / Knowledge Base

- Notes CRUD
- FTS5
- Tags
- Links
- Convert to task
- Convert to calendar
- Project linking
- Attachments

---

## 9. Habits

- Recurrence
- Reminder
- Complete action
- History

---

## 10. Shopping

- Lists
- Items
- Categories
- Project linking
- Complete action

---

## 11. Notifications

- Local notification engine
- Due reminder
- Daily summary
- Daily review
- Habit reminder

---

## 12. Voice

- Speech-to-text
- Quick input handoff
- Permission handling

---

## 13. Files / Attachments

- Photo picker
- Camera scan
- PDF / file picker
- Private file storage
- Delete / cleanup

---

## 14. Templates

- Built-in templates
- Custom templates
- Save task as template
- Save project as template

---

## 15. Activity Log

- Domain event logging
- User-visible log page
- Error log separation

---

## 16. Backup / Export

- SQLite backup
- Restore
- JSON export
- CSV export

---

## 17. Security

- Biometric
- PIN
- Secure storage
- OAuth token protection
- destructive action confirmation

---

## 18. ChatGPT Share Bridge

- Generate text context
- Generate JSON context
- Copy
- Share

---

## 19. Google Drive Bridge

- Bridge Schema Validation
- Action Registry
- Idempotency / Duplicate Protection

- Drive OAuth
- Bridge folder setup
- Manifest
- Export current state
- Import proposed actions
- Schema validation
- Review / accept / reject
- Bridge verification
- Onboarding tutorial
- Activity log

---

## 20. QA

- Unit tests
- Repository tests
- Parser tests
- Calendar integration tests
- Gmail integration tests
- Drive Bridge tests
- Migration tests
- Offline tests
- Backup restore tests
- Security tests

---

## 21. Release

- Android build
- iOS build
- permission review
- privacy text
- onboarding
- versioning


## 22. Engineering Guardrails

- Project Structure
- Migration Framework
- Error Taxonomy
- Permission Strategy
- Testing Strategy
- Release Checklist
- Coding Rules / Definition of Done
