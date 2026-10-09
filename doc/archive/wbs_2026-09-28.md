# 生活助理 App v0.1 — WBS

最後更新：2026-09-28

> 本 WBS 只描述 **scope decomposition**，不是目前排程。實際執行順序以 `phase1_delivery_order.md` 為準；完成狀態以 `acceptance.md` 為準。

## 0. 專案治理與邊界

- `PROJECT_RULES.md`
- `project_boundary.md`
- `decisions.md`
- Phase 1 scope control
- life_assistant / omniAgent boundary validation
- documentation / evidence consistency

## 1. Web / PWA Foundation

- Flutter Web build
- Firebase Hosting
- Router / state management
- API client boundary
- browser session handling
- responsive layout
- loading / empty / error / data states
- mobile / desktop browser verification

## 2. Backend / Cloud Run Foundation

- FastAPI route / service structure
- auth baseline
- authorization / minimum-permission policy
- destructive / sensitive action confirmation policy
- unified error contract
- request id
- logging / observability
- Cloud Run deployment
- secret / environment handling
- runtime verification

## 3. PostgreSQL / Data Layer

- Task
- Checklist / tags / reminders
- Project
- Note
- Habit / completion log
- Shopping list / items
- Template
- Activity / ExecutionLog
- Calendar / Gmail references
- attachment reference model
- repository / service boundaries
- transaction handling
- mutation idempotency
- Alembic migration/versioning

## 4. SQLite → PostgreSQL Migration

- legacy schema inventory
- mapping specification
- deterministic export
- import / upsert
- rerun idempotency
- duplicate prevention
- row-count verification
- relation / critical-field verification
- transaction rollback on failure
- source preservation
- success / partial-success / failure evidence
- real historical source migration when source becomes available

## 5. Core APIs

- Task CRUD
- Checklist
- Project CRUD
- Note CRUD / search
- Habit
- Shopping
- Template
- Activity / execution log
- attachment reference
- versioned external contract where needed

## 6. Core UI

### UI Vertical Slice A

- App Shell / responsive navigation
- Task full UX
- Project UX

### UI Vertical Slice B

- Notes + full-text search
- Habits
- Shopping
- Calendar
- Activity / Execution Log
- Integrations / Connections
- Settings

產品功能完成需包含 UI entry、操作 flow 與 mobile / desktop UX acceptance；Backend-only PASS 不等同產品 DONE。

## 7. Google Integrations

### Google Sign-In

- Web sign-in
- Backend token flow
- revoke / reconnect handling

### Calendar

- read / list
- create
- update
- delete
- explicit confirmation for destructive path
- provider failure evidence

### Gmail

- metadata / snippet
- Gmail → Task
- Gmail → Calendar
- Gmail → Project
- provider failure evidence

### Drive

- integration baseline
- Bridge ensure compatibility / fallback
- partial-success evidence

## 8. ChatGPT Bridge Backend / MCP

- context read model
- versioned API / MCP contract
- input / output schema validation
- Capability Catalog
- permission / risk / confirmation metadata and enforcement
- request_id / action_id idempotency
- proposed action review / execution / result
- Backend-owned action execution
- Activity / execution log
- partial-success / failure semantics
- legacy Drive Bridge compatibility
- omniAgent only through public/versioned life_assistant interface

## 9. Attachments / Storage

- central storage/reference strategy
- image
- PDF
- general files
- no single-device absolute path as central model

## 10. Security / Governance

- authentication
- authorization
- minimum permission
- secret / token storage
- sensitive log filtering
- destructive / sensitive confirmation
- audit trail
- mutation idempotency
- partial-success semantics

## 11. CI/CD / Deployment

- Flutter analyze / test / web build
- Backend tests
- Alembic validation
- one immutable backend image per release
- migration + API + runtime acceptance on same digest
- Firebase Hosting deployment
- Cloud Run deployment
- runtime health / readiness / auth checks
- Artifact Registry retention policy
- release evidence traceability

## 12. QA / Verification

- unit tests
- repository / service tests
- API tests
- migration tests
- Calendar / Gmail integration tests
- Bridge / MCP tests
- security / policy tests
- browser tests
- mobile / desktop responsive acceptance
- runtime / deployment evidence

## 13. Phase 1 Release Gate

- Web/PWA available
- Backend / Cloud Run operational
- PostgreSQL operational
- migration tooling and applicable real-data migration verified
- Google integrations verified to required level
- Bridge / MCP baseline verified to Phase 1 scope
- logs / observability verified
- security / permission baseline verified
- core product flows have usable UI
- `acceptance.md` + `release_checklist.md` consistent with runtime evidence

## 14. Phase 1.5 — Real-use Validation

- observe homepage / navigation usage
- identify noisy or duplicate reminders
- observe Gmail / Calendar / Task conversion flows
- identify frequently used routines
- identify cross-page friction
- fix bugs / consistency issues
- use real-use evidence to confirm Phase 2 priority

## 15. Phase 2 — Product Enhancement

Detailed candidates: `future_product_enhancements.md`.

- Today Cockpit
- Attention Model / Focus
- Routine Library
- Global Capture
- Plan
- Review
- Contextual AI entry points
- later: People / relationship context, richer export/views, advanced summaries

Phase 2 不改變 PostgreSQL operational source of truth，也不得繞過 Backend permission / execution boundary。
