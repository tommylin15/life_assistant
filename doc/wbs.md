# 生活助理 App v0.1 — WBS

最後更新：2026-09-24

> 本 WBS 以目前正式 Web / Cloud 主線為準。舊 Flutter + SQLite 功能保留為 migration source 與既有資產，但不再作為目前主要交付路線。
>
> 執行策略：**Phase 1 先完成並上線；Phase 1.5 用真實使用驗證；Phase 2 再導入 Life OS 類強化功能。**

## 0. 專案治理與邊界

- 維護 `PROJECT_RULES.md`
- 維護 `project_boundary.md`
- 維護 `decisions.md`
- Phase 1 scope freeze
- 變更需記錄理由與影響
- life_assistant / omniAgent 邊界持續驗證

---

## 1. Web / PWA Foundation

### 1.1 Flutter Web
- Web build
- Responsive layout
- Router / state management
- API client boundary
- Browser storage / session handling
- Loading / empty / error / data states

### 1.2 Hosting
- Firebase Hosting dev/test
- PWA baseline
- Mobile / desktop browser verification

---

## 2. Backend Foundation

### 2.1 FastAPI
- Backend skeleton
- Route structure
- Auth baseline
- Permission baseline
- Error response contract
- Logging / observability

### 2.2 Cloud Run
- dev/test deployment
- environment configuration
- secret handling
- runtime verification

---

## 3. PostgreSQL / Data Layer

### 3.1 Core schema
- Task
- Project
- Note
- Habit
- ShoppingItem
- Template
- ActivityLog
- CalendarEventRef
- Attachment reference

### 3.2 Repository / Service boundary
- Repository pattern
- transaction boundary
- idempotency support
- migration/versioning baseline

---

## 4. SQLite → PostgreSQL Migration

- inventory current SQLite schema
- mapping specification
- export
- import
- repeatable migration
- duplicate prevention
- row-count verification
- relation verification
- failure handling
- partial-success reporting
- preserve original SQLite data

---

## 5. Core APIs

- Task CRUD
- Project CRUD
- Note CRUD / search
- Habit
- Shopping
- Template
- Activity / execution log
- attachment reference
- API contract/versioning

---

## 6. Core UI

- Dashboard
- Tasks
- Calendar
- Projects
- Notes
- Habits
- Shopping
- Activity / Execution Log
- Integrations / Connections
- Settings

Phase 1 UI 以現有 domain 能力完成可用版本，不在此階段加入 Today / Focus / Plan / Review 等新的主導航重構。

---

## 7. Google Integrations

### 7.1 Google Sign-In
- Web sign-in
- Backend token flow
- revoke / reconnect handling

### 7.2 Calendar
- read
- create
- update
- delete
- error tracking

### 7.3 Gmail
- metadata / snippet
- Gmail → Task
- Gmail → Calendar
- Gmail → Project
- error / revoke handling

### 7.4 Drive
- integration baseline
- legacy Drive Bridge compatibility / fallback

---

## 8. ChatGPT Bridge Backend

- context access / read model
- proposed action contract
- schema validation
- versioned capability schema
- request_id + action_id idempotency
- permission / risk / confirmation policy
- proposed action review
- action execution
- action result
- execution log
- partial success handling
- legacy Drive Bridge compatibility

---

## 9. MCP / Capability Catalog

- Backend MCP / Integration API entrypoint
- `task.list`
- `task.create`
- `task.update`
- `task.complete`
- `calendar.list`
- `calendar.create`
- `calendar.update`
- `note.search`
- `note.create`
- `project.get`
- `activity.list`
- version metadata
- permission / risk metadata
- confirmation metadata

Global Tool Registry / Workflow Registry 不屬於本專案。

---

## 10. Attachments / Storage

- define central storage/reference strategy
- image
- PDF
- general files
- avoid single-device absolute path as central model

---

## 11. Security / Governance

- authentication
- authorization
- minimum permission
- secret/token storage
- sensitive log filtering
- destructive action confirmation
- audit trail
- idempotency
- partial success semantics

---

## 12. QA / Verification

- unit tests
- repository/service tests
- API tests
- migration tests
- Calendar integration tests
- Gmail integration tests
- Bridge / MCP tests
- security tests
- browser tests
- mobile/desktop responsive verification
- runtime/deployment evidence

---

## 13. Release

### 13.1 Phase 1 Release Gate
- Web/PWA available
- FastAPI on Cloud Run
- PostgreSQL operational
- migration verified
- Google integrations verified
- Bridge / MCP baseline verified
- logs / observability verified
- security / permission baseline verified
- acceptance criteria passed

### 13.2 Explicitly deferred
- Android / iOS release packaging
- app-store release
- full offline-first sync
- SQLite as live central source of truth

---

## 14. Phase 1.5 — Real-use Validation

- observe homepage usage
- identify duplicate / noisy reminders
- observe Gmail / Calendar / Task conversion flows
- record frequently used routines
- identify cross-page friction
- fix bugs and consistency issues first
- use evidence to confirm Phase 2 priority

---

## 15. Phase 2 — Product Enhancement

詳細規格：`future_product_enhancements.md`

### 15.1 First batch
- Today Cockpit
- Attention Model / Focus
- Routine Library
- Global Capture

### 15.2 Second batch
- Plan
- Review
- Contextual AI entry points

### 15.3 Later candidates
- People / relationship context
- portable Markdown views / export
- advanced visual summaries

Phase 2 不改變 PostgreSQL operational source of truth，也不得繞過 Backend permission / execution boundary。

---

## 16. Engineering Guardrails

- Project Structure
- Migration Framework
- Error Taxonomy
- Permission Strategy
- Testing Strategy
- Release Checklist
- Coding Rules / Definition of Done
- Scope Freeze / Change Control
