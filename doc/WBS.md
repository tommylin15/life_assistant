# life_assistant — WBS

最後更新：2026-09-22

## 0. 專案邊界

life_assistant = **Data + UI + API + Execution + Integration**。

不包含 LangGraph、Global Tool Registry、Workflow Registry、Agent Runtime、Agent Worker 或跨產品 Agent orchestration；這些由 omniAgent 負責。

## 1. Cloud Foundation

### 1.1 Flutter Web / PWA
- Flutter Web build
- responsive shell
- routing
- environment config
- Firebase Hosting dev/test
- PWA baseline

### 1.2 FastAPI Backend
- backend skeleton
- config / environment
- health endpoint
- auth / permission baseline
- unified error model
- request / execution logging
- Cloud Run dev/test

### 1.3 PostgreSQL
- schema baseline
- migrations
- repository layer
- transaction policy
- connection management
- dev/test database

## 2. Core Domain APIs

### 2.1 Tasks
- list/get/create/update/complete
- priority/status/due/reminder/tags/project/checklist

### 2.2 Projects
- CRUD
- aggregate related tasks/events/notes/gmail refs/attachments/activity

### 2.3 Notes
- CRUD
- markdown
- search
- tags/links/project relation

### 2.4 Habits / Shopping / Templates
- CRUD and domain rules
- completion/history where applicable

### 2.5 Activity / Execution Log
- actor/source
- action
- status
- entity reference
- error reference
- partial success

## 3. SQLite → PostgreSQL Migration

### 3.1 Inventory
- current SQLite schema snapshot
- source tables/relationships
- unsupported/legacy fields

### 3.2 Mapping
- entity mapping
- ID strategy
- timestamp/timezone normalization
- nullable/default policy

### 3.3 Migration Runner
- export
- transform
- import
- idempotency
- retry-safe behavior

### 3.4 Validation
- row counts
- relationship checks
- sample checks
- failure rollback / source preservation
- migration report

## 4. Frontend Migration

### 4.1 API Client
- base client
- auth
- error mapping
- loading/empty/error/data states

### 4.2 Pages
- Dashboard
- Tasks
- Calendar
- Projects
- Notes
- Habits
- Shopping
- Activity Log
- Integrations
- ChatGPT Bridge / MCP
- Settings

### 4.3 Responsive / Accessibility
- phone browser
- tablet
- desktop
- keyboard navigation
- semantics
- contrast / scaling

## 5. Google Integrations

### 5.1 Google Auth
- web sign-in
- backend validation
- secure token handling
- revoke/reconnect

### 5.2 Calendar
- read/create/update/delete
- project/task conversion
- error handling

### 5.3 Gmail
- metadata/snippet
- task/calendar/project conversion
- minimal data retention

### 5.4 Drive
- Bridge legacy/fallback
- file/reference integration where required

## 6. ChatGPT Bridge Backend

### 6.1 Contract
- versioned schema
- current context read model
- proposed action envelope
- action result envelope

### 6.2 Safety / Governance
- schema validation
- permission
- risk level
- confirmation policy
- request/action idempotency
- audit log
- partial success

### 6.3 Execution
- task actions
- calendar actions
- note actions
- project actions
- shopping actions
- result reporting

### 6.4 Legacy Drive Bridge
- preserve existing schema compatibility where practical
- mark SQLite-specific assumptions as legacy
- keep fallback path distinct from main Backend/MCP route

## 7. MCP / life_assistant Capability Catalog

### 7.1 MCP Server / Integration API
- transport/auth decision
- schema/versioning
- error contract

### 7.2 Initial Capabilities
- task.list/create/update/complete
- calendar.list/create/update
- note.search/create
- project.get
- activity.list

### 7.3 Capability Metadata
- version
- permission
- risk
- confirmation requirement
- input/output schema

> 此 catalog 只描述 life_assistant 自己的能力，不是 omniAgent 的 Global Tool Registry。

## 8. Background Jobs

- Calendar sync
- Gmail sync
- notifications
- migration jobs
- export/backup
- maintenance

限制：不得在此實作 Agent reasoning loop。

## 9. Attachment / Storage

- storage strategy
- upload/download
- metadata
- secure reference
- image/PDF/general file
- migration from local paths where required

## 10. Security / Observability

- authentication
- authorization
- secret management
- sensitive log scrub
- audit trail
- rate / abuse safeguards where relevant
- traceable external API errors
- operational metrics

## 11. CI / Deployment

- repair current CI failure
- frontend lint/test/build
- backend test
- migration test
- Firebase dev/test deploy
- Cloud Run dev/test deploy
- release gate

## 12. Phase 1 Acceptance

- Web/PWA works on phone and desktop browsers
- core CRUD goes through Backend
- PostgreSQL persists operational data
- SQLite migration is verifiable and non-destructive
- Calendar/Gmail integrations work with clear failure states
- ChatGPT Bridge Backend works with validation/policy/audit
- MCP/Integration API exposes life_assistant capabilities safely
- no Agent orchestration dependency required for life_assistant completion

## 13. Explicitly Outside This WBS

- LangGraph
- Global Tool Registry
- Workflow Registry
- Agent Runtime
- Agent Worker
- cross-product tool routing
- generic multi-step Agent planning
- omniAgent internal retry/resume orchestration
