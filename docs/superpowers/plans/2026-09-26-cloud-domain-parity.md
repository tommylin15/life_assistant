# Cloud Domain Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostgreSQL/FastAPI Cloud target parity for Notes, Habits, Shopping, and Templates while preserving existing SQLite contracts and audit behavior.

**Architecture:** Add one additive Alembic revision and focused SQLAlchemy models for the four domains, then add Pydantic contracts and authenticated `/api/v1` routers that follow the existing Task/Project execution-log pattern. Keep storage normalized, preserve stable IDs and legacy nullable/source shapes, and do not expand into Phase 2 behavior or invent a new SQLite→PostgreSQL import framework in this change.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async ORM, Alembic, PostgreSQL, `unittest`, GitHub Actions, Cloud Run.

**Spec:** `doc/cloud_domain_parity_design.md`

## Global Constraints

- Use **Parity-first normalized schema**; do not introduce generic entity/JSONB-everything storage.
- Preserve existing SQLite entity shape, stable IDs, and repository behavior where the Cloud contract mirrors local behavior.
- PostgreSQL schema changes must use versioned Alembic migration; never drop or clear SQLite data.
- New endpoints use `/api/v1`, `current_user`, `AsyncSession`, Pydantic validation, and execution logging for mutations.
- New domain execution logs use `provider="life_assistant"` and must not contain Note bodies or Template payload bodies.
- Notes DB `title`/`body` remain nullable for migration compatibility. Cloud create requires both fields as strings; Cloud patch may update either field but must reject explicit `null` for `title` or `body`; empty strings are valid.
- Habit Cloud API does not add delete/activate/deactivate behavior; `GET /habits` returns active habits only.
- Shopping item PATCH only toggles `is_done`; no quantity/price/store/delete behavior in this batch.
- Template `payload_json` is an opaque string and must round-trip unchanged; do not parse, normalize, reorder, or migrate it to JSONB.
- Note/Shopping `project_id` remains a reference without a new DB FK in this batch; project delete guard must block linked Task, Note, or Shopping List with 409.
- Do not add Notes FTS, tags/attachments Cloud migration, MCP expansion, Habit analytics, Template apply/versioning, or Phase 2 UX.
- Do not claim SQLite→PostgreSQL historical data backfill PASS unless a real importer/backfill path is actually executed and verified.
- `main` is the only formal branch and successful CI on `main` can trigger `Deploy Cloud Run`. During implementation, do not advance the remote `main` ref task-by-task. Keep task commits local/unpublished (or as unattached Git objects) and fast-forward `main` once after Tasks 1-7 pass, so incomplete intermediate states do not auto-deploy.
- Current Cloud Run deployment targets GitHub environment `dev-test`; runtime mutation acceptance must use that environment and exact `[ACCEPTANCE TEST]` IDs/names.
- The existing deploy workflow validates Alembic only with `alembic upgrade head --sql`; it does not apply the migration to the runtime DB. Runtime schema/Alembic revision state must therefore be verified separately before claiming migration PASS.

## Review Focus

1. **Runtime migration drift:** `Base.metadata.create_all()` can create additive tables even if `alembic_version` is behind; execution must verify current DB revision before/after rollout and must not claim migration PASS from `--sql` alone. Task 1 and Task 8 own this.
2. **Legacy nullable Notes:** a migrated row with `title=NULL` or `body=NULL` must remain readable and must not be rewritten during schema migration; Task 2 pins this behavior.
3. **Note-link edge cases:** duplicate links must be idempotent, self-link requests must return 422, and delete must clean links without deleting the peer note; Task 2 owns these tests.
4. **Habit history semantics:** every completion must append a new row and history must preserve multiple completions in descending time order; Task 3 owns these tests.
5. **Opaque Template payloads / Project references:** Template text must round-trip exactly, and project deletion must remain blocked by linked Task/Note/Shopping List without new hard FKs; Tasks 5 and 6 pin these behaviors.

---

## File Structure

### Create

- `backend/app/models/note.py` — `Note` and `NoteLink` SQLAlchemy tables.
- `backend/app/models/habit.py` — `Habit` and `HabitCompletion` tables.
- `backend/app/models/shopping.py` — `ShoppingList` and `ShoppingItem` tables.
- `backend/app/models/template.py` — `Template` table.
- `backend/app/api/notes.py` — Note CRUD and note-link endpoints.
- `backend/app/api/habits.py` — Habit CRUD subset and completion history endpoints.
- `backend/app/api/shopping.py` — Shopping list/item endpoints.
- `backend/app/api/templates.py` — Template CRUD subset.
- `backend/alembic/versions/20260926_0004_cloud_domain_parity.py` — additive PostgreSQL target schema migration.
- `backend/tests/test_cloud_domain_models.py` — target table/model and migration-contract tests.
- `backend/tests/test_notes.py` — Notes API/schema contract tests.
- `backend/tests/test_habits.py` — Habits API/schema contract tests.
- `backend/tests/test_shopping.py` — Shopping API/schema contract tests.
- `backend/tests/test_templates.py` — Templates API/schema contract tests.

### Modify

- `backend/alembic/env.py` — import new ORM models so `Base.metadata` knows the tables.
- `backend/app/models/schemas.py` — add Pydantic request/response models without creating a new schema package.
- `backend/app/main.py` — register four new routers under `/api/v1`.
- `backend/app/api/projects.py` — extend delete guard to Notes and Shopping Lists.
- `backend/tests/test_projects.py` — pin the expanded delete guard contract.
- `doc/cloud_domain_parity_design.md` — update status/evidence only when supported by implementation/runtime evidence.

---

### Task 1: Establish migration safety, models, and target schema

**Files:**
- Create: `backend/app/models/note.py`
- Create: `backend/app/models/habit.py`
- Create: `backend/app/models/shopping.py`
- Create: `backend/app/models/template.py`
- Create: `backend/alembic/versions/20260926_0004_cloud_domain_parity.py`
- Create: `backend/tests/test_cloud_domain_models.py`
- Modify: `backend/alembic/env.py`

**Interfaces:**
- Consumes: `Base` from `app.db.session`; migration head `20260925_0003`.
- Produces: ORM classes `Note`, `NoteLink`, `Habit`, `HabitCompletion`, `ShoppingList`, `ShoppingItem`, `Template` and Alembic revision `20260926_0004`.

- [ ] **Step 1: Record current dev-test DB migration state before schema work**

Use existing GCP/dev inspection capability to query the exact `life_assistant` database for `SELECT version_num FROM alembic_version` and the existence of the seven target tables. Record only schema/revision metadata, not user data.

Expected before this change: current revision is known explicitly. If tables already exist without the matching Alembic revision, stop implementation and treat that as migration drift to repair before applying `0004`.

- [ ] **Step 2: Write failing model-contract tests**

In `backend/tests/test_cloud_domain_models.py`, assert exact table names, required columns/nullability, `note_links` composite PK, FKs for note links/habit completions/shopping items, no `updated_at` on Habits/Shopping Lists, no timestamps on Shopping Items, and `payload_json` remains a text column.

- [ ] **Step 3: Run the model tests and verify failure**

Run: `cd backend && python -m unittest tests.test_cloud_domain_models -v`

Expected: FAIL because the model modules/classes do not exist yet.

- [ ] **Step 4: Implement the four focused SQLAlchemy model modules**

Use these exact class/table names:

```text
Note -> notes
NoteLink -> note_links
Habit -> habits
HabitCompletion -> habit_completions
ShoppingList -> shopping_lists
ShoppingItem -> shopping_items
Template -> templates
```

Use `String(36)` stable IDs and the exact column/nullability rules from the spec. `project_id` is a plain nullable `String(36)` in this batch.

- [ ] **Step 5: Add the Alembic migration and model imports**

Create revision `20260926_0004` with `down_revision = "20260925_0003"`. `upgrade()` creates all seven tables and the `(habit_id, completed_at)` index; `downgrade()` removes only objects created by this revision in dependency-safe reverse order. Import all new model classes in `backend/alembic/env.py` for metadata registration.

- [ ] **Step 6: Verify model tests and offline Alembic chain**

Run:

```bash
cd backend
python -m unittest tests.test_cloud_domain_models -v
alembic upgrade head --sql > /tmp/life-assistant-cloud-domain-parity.sql
```

Expected: tests PASS; Alembic renders a continuous migration from `20260925_0003` to `20260926_0004` with no revision error.

- [ ] **Step 7: Create an unpublished Task 1 commit**

```bash
git add backend/app/models backend/alembic/env.py backend/alembic/versions/20260926_0004_cloud_domain_parity.py backend/tests/test_cloud_domain_models.py
git commit -m "feat: add cloud parity database schema"
```

Do not push/advance remote `main` yet.

---

### Task 2: Implement Notes API parity

**Files:**
- Create: `backend/app/api/notes.py`
- Create: `backend/tests/test_notes.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `Note`, `NoteLink`; `current_user`; `get_db`; `start_execution`, `finish_execution`, `fail_execution`.
- Produces: `NoteCreate`, `NoteUpdate`, `NoteOut`, `NoteLinkCreate`; router prefix `/notes`.

- [ ] **Step 1: Write failing Notes contract tests**

Pin these assertions:

```text
NoteCreate(title="", body="") succeeds
NoteCreate missing title -> validation failure
NoteCreate missing body -> validation failure
NoteUpdate() -> validation failure
NoteUpdate(title=None) -> validation failure
NoteUpdate(body=None) -> validation failure
GET /api/v1/notes without auth -> 401 + X-Request-ID
new self-link request -> 422
```

Also prove `NoteOut` can represent `title=None` and `body=None` for legacy migrated rows without manufacturing replacements.

- [ ] **Step 2: Run Notes tests and verify failure**

Run: `cd backend && python -m unittest tests.test_notes -v`

Expected: FAIL because Notes schemas/router are absent.

- [ ] **Step 3: Add Notes Pydantic schemas**

Add `NoteCreate`, `NoteUpdate`, `NoteOut`, `NoteLinkCreate` to `backend/app/models/schemas.py`. `NoteCreate.title/body` are required strings. `NoteUpdate` rejects empty PATCH and rejects explicit null for `title` or `body`; `project_id` may be explicitly null. `NoteOut.title/body` are nullable.

- [ ] **Step 4: Implement Notes router**

Implement:

```text
GET    /notes
POST   /notes
GET    /notes/{note_id}
PATCH  /notes/{note_id}
DELETE /notes/{note_id}
GET    /notes/{note_id}/links
POST   /notes/{note_id}/links
```

List by `updated_at DESC`. Linked-note listing is bidirectional and deduplicated. Duplicate link returns idempotent success. Self-link returns 422. Delete removes only links referencing the note plus the note itself. Mutations use `note.create`, `note.update`, `note.delete`, `note.link`, `provider="life_assistant"`.

- [ ] **Step 5: Register Notes router**

Import and include `notes_router` in `backend/app/main.py` with `prefix="/api/v1"`.

- [ ] **Step 6: Add behavior tests for links, delete, and audit boundaries**

Use `unittest.IsolatedAsyncioTestCase` plus dependency/method mocks where a real DB is unnecessary. Pin: missing source/target -> 404; duplicate link adds no second row; self-link -> 422; delete does not delete peer note; execution summary never includes Note body.

- [ ] **Step 7: Run Notes regression slice**

```bash
cd backend
python -m unittest tests.test_notes tests.test_projects tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 8: Create an unpublished Task 2 commit**

```bash
git add backend/app/api/notes.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_notes.py
git commit -m "feat: add notes cloud api"
```

Do not push/advance remote `main` yet.

---

### Task 3: Implement Habits API parity

**Files:**
- Create: `backend/app/api/habits.py`
- Create: `backend/tests/test_habits.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `Habit`, `HabitCompletion`, auth/DB/execution-log helpers.
- Produces: `HabitCreate`, `HabitUpdate`, `HabitOut`, `HabitCompletionOut`; router prefix `/habits`.

- [ ] **Step 1: Write failing Habit contract tests**

Pin: create requires `title` and `recurrence_rule`; `reminder_time` optional; empty PATCH rejected; unauthenticated list -> 401; model default `is_active=True`; API exposes no activate/deactivate/delete mutation.

- [ ] **Step 2: Run Habit tests and verify failure**

Run: `cd backend && python -m unittest tests.test_habits -v`

Expected: FAIL because Habit schemas/router are absent.

- [ ] **Step 3: Add Habit schemas and router**

Implement:

```text
GET    /habits                     # is_active = true only
POST   /habits
GET    /habits/{habit_id}
PATCH  /habits/{habit_id}
POST   /habits/{habit_id}/complete
GET    /habits/{habit_id}/completions
```

Patch only `title`, `recurrence_rule`, `reminder_time`. Completion appends a new UUID `HabitCompletion`; history orders `completed_at DESC`. Mutations log `habit.create`, `habit.update`, `habit.complete` with `provider="life_assistant"`.

- [ ] **Step 4: Register Habits router and add append-history tests**

Pin: missing habit -> 404; two complete calls produce two distinct rows; history preserves both descending; earlier completion rows are unchanged.

- [ ] **Step 5: Run Habit regression slice**

```bash
cd backend
python -m unittest tests.test_habits tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 6: Create an unpublished Task 3 commit**

```bash
git add backend/app/api/habits.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_habits.py
git commit -m "feat: add habits cloud api"
```

Do not push/advance remote `main` yet.

---

### Task 4: Implement Shopping API parity

**Files:**
- Create: `backend/app/api/shopping.py`
- Create: `backend/tests/test_shopping.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `ShoppingList`, `ShoppingItem`, auth/DB/execution-log helpers.
- Produces: `ShoppingListCreate`, `ShoppingItemCreate`, `ShoppingItemUpdate`, `ShoppingItemOut`, `ShoppingListOut`; paths under `/shopping-lists` and `/shopping-items`.

- [ ] **Step 1: Write failing Shopping contract tests**

Pin: list name required; item name required; category optional; `ShoppingItemUpdate` accepts only `is_done` and rejects empty PATCH; unauthenticated list -> 401; list response nests items ordered by `sort_order`.

- [ ] **Step 2: Run Shopping tests and verify failure**

Run: `cd backend && python -m unittest tests.test_shopping -v`

Expected: FAIL because Shopping schemas/router are absent.

- [ ] **Step 3: Add Shopping schemas and router**

Implement:

```text
GET   /shopping-lists
POST  /shopping-lists
GET   /shopping-lists/{list_id}
POST  /shopping-lists/{list_id}/items
PATCH /shopping-items/{item_id}
```

List responses nest items by `sort_order ASC`. Item creation checks list existence -> 404 if absent. Item PATCH updates only `is_done`. Mutations log `shopping_list.create`, `shopping_item.create`, `shopping_item.toggle` with `provider="life_assistant"`.

- [ ] **Step 4: Register Shopping router and add failure/audit tests**

Pin: invalid list -> 404; `project_id` is preserved exactly without existence validation; toggle does not mutate name/category/list_id.

- [ ] **Step 5: Run Shopping regression slice**

```bash
cd backend
python -m unittest tests.test_shopping tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 6: Create an unpublished Task 4 commit**

```bash
git add backend/app/api/shopping.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_shopping.py
git commit -m "feat: add shopping cloud api"
```

Do not push/advance remote `main` yet.

---

### Task 5: Implement Templates API parity

**Files:**
- Create: `backend/app/api/templates.py`
- Create: `backend/tests/test_templates.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `Template`, auth/DB/execution-log helpers.
- Produces: `TemplateCreate`, `TemplateUpdate`, `TemplateOut`; router prefix `/templates`.

- [ ] **Step 1: Write failing Template contract tests**

Pin: create requires `name`, `template_type`, `payload_json`; empty PATCH rejected; unauthenticated list -> 401; payload text `'{ "b":2, "a":1 }'` returns exactly the same string; arbitrary opaque string input is not parsed or rewritten.

- [ ] **Step 2: Run Template tests and verify failure**

Run: `cd backend && python -m unittest tests.test_templates -v`

Expected: FAIL because Template schemas/router are absent.

- [ ] **Step 3: Add Template schemas and router**

Implement:

```text
GET   /templates
POST  /templates
GET   /templates/{template_id}
PATCH /templates/{template_id}
```

Do not call `json.loads`, serialize, normalize, or move to JSONB. Mutations log `template.create` and `template.update` with `provider="life_assistant"`; summaries include template name only, never `payload_json`.

- [ ] **Step 4: Register Templates router and run regression slice**

```bash
cd backend
python -m unittest tests.test_templates tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 5: Create an unpublished Task 5 commit**

```bash
git add backend/app/api/templates.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_templates.py
git commit -m "feat: add templates cloud api"
```

Do not push/advance remote `main` yet.

---

### Task 6: Extend Project deletion guard

**Files:**
- Modify: `backend/app/api/projects.py`
- Modify: `backend/tests/test_projects.py`

**Interfaces:**
- Consumes: `Task`, `Note`, `ShoppingList`.
- Produces: `DELETE /api/v1/projects/{project_id}` -> 409 when any of those entity types references the project.

- [ ] **Step 1: Write failing Project guard tests**

Add explicit cases: linked Task -> 409; linked Note -> 409; linked ShoppingList -> 409; no linked entity -> existing delete path remains allowed.

- [ ] **Step 2: Run Project tests and verify new cases fail**

Run: `cd backend && python -m unittest tests.test_projects -v`

Expected: Task guard passes; Note/Shopping guard cases fail until implementation.

- [ ] **Step 3: Extend the guard with minimal queries**

Before the delete execution record starts, query each table for one matching `project_id` using `select(...).limit(1)`. Return 409 on any match. Do not add DB FK/cascade.

- [ ] **Step 4: Run Project tests**

Run: `cd backend && python -m unittest tests.test_projects -v`

Expected: PASS.

- [ ] **Step 5: Create an unpublished Task 6 commit**

```bash
git add backend/app/api/projects.py backend/tests/test_projects.py
git commit -m "fix: protect projects with cloud parity references"
```

Do not push/advance remote `main` yet.

---

### Task 7: Full local/backend verification before advancing main

**Files:**
- Modify only if verification exposes a defect in Tasks 1-6.

**Interfaces:**
- Consumes: all parity models/routes/tests.
- Produces: a commit chain whose tip imports cleanly, has a valid Alembic chain, and passes the complete repository checks needed before `main` moves.

- [ ] **Step 1: Run backend import/migration checks**

```bash
cd backend
python -c "from app.main import app; print('OK')"
alembic upgrade head --sql > /tmp/life-assistant-migrations.sql
python -m unittest discover -s tests -v
```

Expected: `OK`, no Alembic chain error, zero backend test failures/errors.

- [ ] **Step 2: Run repository-level checks matching CI where executable**

From repository root:

```bash
flutter analyze --no-pub --no-fatal-infos
flutter test --no-pub
flutter build web --target=lib/main_web.dart --no-pub
bash -n scripts/bootstrap_gcp_wif.sh
bash -n scripts/inspect_postgres_dev.sh
bash -n scripts/diagnose_db_secret.sh
bash -n scripts/rotate_google_oauth_secret.sh
```

Expected: no blocking failures. If local Flutter/tooling is unavailable, record `NOT VERIFIED` and rely on CI for that layer; do not claim local PASS.

- [ ] **Step 3: Contract review against the approved spec**

Verify exact endpoint paths, schema fields/nullability, action types/provider, no extra Phase 2 behavior, and no Note body/Template payload in audit summaries. Fix implementation, not the spec, unless a real contradiction requires user review.

- [ ] **Step 4: Classify pre-push evidence**

At minimum: implementation PASS, backend tests PASS, offline Alembic chain PASS. Historical SQLite backfill remains `NOT VERIFIED` unless an actual importer/backfill path was found and executed.

- [ ] **Step 5: Advance remote `main` once**

Fast-forward `main` from its previously verified SHA to the final Task 1-7 commit chain in one ref update/push operation. Do not force push or rewrite history.

---

### Task 8: CI, runtime migration, deployment, and acceptance

**Files:**
- Modify only when CI/runtime evidence identifies an actual defect.
- Update evidence/status docs only from real results.

**Interfaces:**
- Consumes: final `main` tip from Task 7 and existing CI/deploy workflows.
- Produces: PASS / FAIL / NOT VERIFIED evidence for CI, runtime migration, deployment, persistence, and execution log.

- [ ] **Step 1: Verify CI on the final `main` tip**

Required gates from `.github/workflows/ci.yml`: backend import, Alembic `--sql`, backend unittest discovery, Flutter analyze/test/build, deployment-script syntax. Record exact run/job evidence.

- [ ] **Step 2: Before relying on application startup, verify dev-test DB revision/table state again**

Query `alembic_version` and target-table existence in the `life_assistant` dev-test DB. If `0004` is not applied, do **not** count `Base.metadata.create_all()` table creation as migration success.

- [ ] **Step 3: Apply `alembic upgrade 20260926_0004` through an authorized dev-test path that can reach the private PostgreSQL network**

Use the project's existing GCP access pattern (for example the PostgreSQL dev VM/IAP path) rather than exposing the DB publicly. First run `alembic current`/equivalent schema revision inspection; apply only a normal forward additive migration. If runtime state shows conflicting pre-created tables, stop and repair/mark FAIL rather than using `stamp` or destructive SQL to hide drift without evidence.

- [ ] **Step 4: Verify DB migration state**

Required: `alembic_version = 20260926_0004`; all seven tables exist with expected columns/constraints/index; existing tables/data remain intact. This is the runtime Alembic PASS gate.

- [ ] **Step 5: Verify GitHub Actions Cloud Run deployment**

The existing workflow deploys to environment `dev-test`. Confirm deploy job success, resolved service URL, `/health` PASS, `/ready` PASS, and unauthenticated protected API behavior.

- [ ] **Step 6: Run authenticated acceptance smoke with `[ACCEPTANCE TEST]` data**

Verify:

```text
Note: create -> update -> read -> create/link second note -> linked read -> delete both
Habit: create -> update -> complete twice -> read completion history
Shopping: create list -> add item -> toggle -> read nested list
Template: create -> update -> read exact payload string
Activity/execution log: verify mutation families are visible and successful
Project: linked Note or Shopping List -> delete returns 409
```

Use exact returned IDs. Because Habit/Shopping/Template parity intentionally has no delete endpoints, perform these mutation smoke tests only against `dev-test`; cleanup those exact acceptance rows via a controlled DB transaction/maintenance path, never a broad delete. Record cleanup result separately.

- [ ] **Step 7: Verify PostgreSQL persistence and relation behavior**

Prove values survive separate API requests; Note links, Habit completions, Shopping items, and Template payload text persist; no unrelated production/user rows are modified.

- [ ] **Step 8: Classify final status**

```text
implementation: PASS / FAIL
backend tests: PASS / FAIL
Alembic offline chain: PASS / FAIL
runtime Alembic migration: PASS / FAIL / NOT VERIFIED
SQLite historical backfill: PASS / FAIL / NOT VERIFIED
CI: PASS / FAIL / NOT VERIFIED
deployment: PASS / FAIL / NOT VERIFIED
runtime CRUD/persistence: PASS / FAIL / NOT VERIFIED
execution log validation: PASS / FAIL / NOT VERIFIED
acceptance cleanup: PASS / FAIL / NOT VERIFIED
```

Cloud target schema/API may be marked `DONE` only when implementation/tests/CI/runtime migration/deployment/runtime CRUD/audit evidence are PASS. The wider SQLite historical backfill remains separately `NOT VERIFIED` until a real backfill workflow exists and is executed.

- [ ] **Step 9: Commit evidence/documentation updates only when supported by real results**

Do not mark release checklist items complete from code presence, CI green, or `create_all()` alone.
