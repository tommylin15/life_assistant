# Cloud Domain Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostgreSQL/FastAPI Cloud target parity for Notes, Habits, Shopping, and Templates while preserving existing SQLite contracts and audit behavior.

**Architecture:** Add one additive Alembic revision and focused SQLAlchemy models for the four domains, then add Pydantic contracts and authenticated `/api/v1` routers that follow the existing Task/Project execution-log pattern. Keep storage normalized, preserve stable IDs and legacy nullable/source shapes, and do not expand into Phase 2 behavior or invent a new SQLite→PostgreSQL import framework in this change.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy async ORM, Alembic, PostgreSQL, `unittest`, GitHub Actions, Cloud Run.

**Spec:** `doc/cloud_domain_parity_design.md`

## Global Constraints

- Use **Parity-first normalized schema**; do not introduce generic entity/JSONB-everything storage.
- Preserve existing SQLite entity shape, stable IDs, and repository behavior where the Cloud contract is intended to mirror local behavior.
- PostgreSQL schema changes must use versioned Alembic migration; never drop or clear SQLite data.
- New endpoints use `/api/v1`, `current_user`, `AsyncSession`, Pydantic validation, and execution logging for mutations.
- New domain execution logs use `provider="life_assistant"` and must not contain Note bodies or Template payload bodies.
- Notes DB `title`/`body` remain nullable for migration compatibility, but Cloud create/update contracts require the fields when creating and allow explicit empty strings.
- Habit Cloud API does not add delete/activate/deactivate behavior; `GET /habits` returns active habits only.
- Shopping item PATCH only toggles `is_done`; no quantity/price/store/delete behavior in this batch.
- Template `payload_json` is an opaque string and must round-trip unchanged; do not parse, normalize, reorder, or migrate it to JSONB.
- Note/Shopping `project_id` remains a reference without a new DB FK in this batch; project delete guard must block linked Task, Note, or Shopping List with 409.
- Do not add Notes FTS, tags/attachments Cloud migration, MCP expansion, Habit analytics, Template apply/versioning, or Phase 2 UX.
- Do not claim SQLite→PostgreSQL historical data backfill PASS unless a real importer/backfill path is actually executed and verified; this plan only guarantees target schema/API plus Alembic-chain validation unless such a path already exists at execution time.

## Review Focus

1. **Legacy nullable Notes:** a migrated row with `title=NULL` or `body=NULL` must remain readable and must not be rewritten during schema migration; Task 2 pins this behavior.
2. **Note-link edge cases:** duplicate links must be idempotent, self-link requests must return 422, and delete must clean links without deleting the peer note; Task 2 owns these tests.
3. **Habit history semantics:** every completion must append a new row and history must preserve multiple completions in descending time order; Task 3 owns these tests.
4. **Opaque Template payloads:** strings that are not normalized JSON must round-trip byte-for-byte as text; Task 5 owns this test.
5. **Project deletion with new references:** Project deletion must remain blocked by linked Task, Note, or Shopping List without adding a hard DB FK; Task 6 owns these tests.

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
- `doc/cloud_domain_parity_design.md` — update status/evidence only if implementation changes the documented contract; do not rewrite design during implementation without an explicit reason.

---

### Task 1: Add PostgreSQL target models and Alembic migration

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

- [ ] **Step 1: Write failing model-contract tests**

In `backend/tests/test_cloud_domain_models.py`, add tests that assert exact table names, required columns/nullability, `note_links` composite PK, FKs for note links/habit completions/shopping items, no `updated_at` on Habits/Shopping Lists, no timestamps on Shopping Items, and `payload_json` remains a text column.

- [ ] **Step 2: Run the model tests and verify failure**

Run: `cd backend && python -m unittest tests.test_cloud_domain_models -v`

Expected: FAIL because the model modules/classes do not exist yet.

- [ ] **Step 3: Implement the four focused SQLAlchemy model modules**

Use these class/table names exactly:

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

- [ ] **Step 4: Add the Alembic migration and model imports**

Create revision `20260926_0004` with `down_revision = "20260925_0003"`. `upgrade()` creates all seven tables and the `(habit_id, completed_at)` index; `downgrade()` removes only objects created by this revision in dependency-safe reverse order. Import all new model classes in `backend/alembic/env.py` for metadata registration.

- [ ] **Step 5: Verify model tests and Alembic chain**

Run:

```bash
cd backend
python -m unittest tests.test_cloud_domain_models -v
alembic upgrade head --sql > /tmp/life-assistant-cloud-domain-parity.sql
```

Expected: tests PASS; Alembic renders a continuous migration from `20260925_0003` to `20260926_0004` with no revision error.

- [ ] **Step 6: Commit Task 1**

```bash
git add backend/app/models backend/alembic/env.py backend/alembic/versions/20260926_0004_cloud_domain_parity.py backend/tests/test_cloud_domain_models.py
git commit -m "feat: add cloud parity database schema"
```

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

Add tests for:

```text
NoteCreate(title="", body="") succeeds
NoteCreate missing title -> validation failure
NoteCreate missing body -> validation failure
NoteUpdate() -> validation failure
GET /api/v1/notes without auth -> 401 + X-Request-ID
POST self-link -> schema/route rule maps to 422
```

Also add a model/read-contract test proving a `Note` object may hold `title=None` and `body=None` without the response/migration layer manufacturing replacement values.

- [ ] **Step 2: Run Notes tests and verify failure**

Run: `cd backend && python -m unittest tests.test_notes -v`

Expected: FAIL because Notes schemas/router are absent.

- [ ] **Step 3: Add Notes Pydantic schemas**

Add exact classes to `backend/app/models/schemas.py`:

```python
class NoteCreate(BaseModel): ...
class NoteUpdate(BaseModel): ...
class NoteOut(BaseModel): ...
class NoteLinkCreate(BaseModel): ...
```

`NoteUpdate` rejects an empty PATCH; `NoteLinkCreate.target_note_id` is required. `NoteOut.title` and `NoteOut.body` are nullable to preserve migrated rows.

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

Ordering: Notes list by `updated_at DESC`. Link listing is bidirectional and deduplicated. Duplicate insert returns idempotent success. Self-link returns 422. Delete removes NoteLink rows referencing the note before deleting the note. Mutations use action types `note.create`, `note.update`, `note.delete`, `note.link` and `provider="life_assistant"`.

- [ ] **Step 5: Register Notes router**

Import and include `notes_router` in `backend/app/main.py` with `prefix="/api/v1"`.

- [ ] **Step 6: Add behavior tests for link/idempotency/delete/audit boundaries**

Use `unittest.IsolatedAsyncioTestCase` plus dependency/method mocks where a real DB is unnecessary. Pin these outcomes: missing source/target -> 404; duplicate link does not add a second row; self-link -> 422; delete targets only the requested note and related links; execution-log summaries never include `body`.

- [ ] **Step 7: Run Notes tests plus existing backend regression slice**

Run:

```bash
cd backend
python -m unittest tests.test_notes tests.test_projects tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

```bash
git add backend/app/api/notes.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_notes.py
git commit -m "feat: add notes cloud api"
```

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

Pin: create requires non-null `title` and `recurrence_rule`; `reminder_time` optional; empty PATCH rejected; protected list returns 401 without auth; model default `is_active=True`; no API schema exposes activate/deactivate/delete.

- [ ] **Step 2: Run Habit tests and verify failure**

Run: `cd backend && python -m unittest tests.test_habits -v`

Expected: FAIL because Habit schemas/router are absent.

- [ ] **Step 3: Add Habit schemas and router**

Implement:

```text
GET    /habits                     # only is_active = true
POST   /habits
GET    /habits/{habit_id}
PATCH  /habits/{habit_id}
POST   /habits/{habit_id}/complete
GET    /habits/{habit_id}/completions
```

Patch only `title`, `recurrence_rule`, `reminder_time`. Completion creates a new `HabitCompletion` UUID row and does not mutate older rows. History orders `completed_at DESC`. Mutations log `habit.create`, `habit.update`, `habit.complete` with `provider="life_assistant"`.

- [ ] **Step 4: Register Habits router and add append-history tests**

Add router to `backend/app/main.py`. Test missing habit -> 404; two complete calls produce two completion rows; history preserves both in descending timestamp order; completion logs do not overwrite prior records.

- [ ] **Step 5: Run Habit regression tests**

Run:

```bash
cd backend
python -m unittest tests.test_habits tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add backend/app/api/habits.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_habits.py
git commit -m "feat: add habits cloud api"
```

---

### Task 4: Implement Shopping API parity

**Files:**
- Create: `backend/app/api/shopping.py`
- Create: `backend/tests/test_shopping.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `ShoppingList`, `ShoppingItem`, auth/DB/execution-log helpers.
- Produces: `ShoppingListCreate`, `ShoppingItemCreate`, `ShoppingItemUpdate`, `ShoppingItemOut`, `ShoppingListOut`; routers for `/shopping-lists` and `/shopping-items`.

- [ ] **Step 1: Write failing Shopping contract tests**

Pin: list name required; item name required; category optional; `ShoppingItemUpdate` accepts only `is_done` and rejects empty PATCH; unauthenticated list -> 401; response list contains nested items ordered by `sort_order`.

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

List responses nest items sorted by `sort_order ASC`. Item creation checks list existence and returns 404 when absent. Item PATCH updates only `is_done`. Mutations log `shopping_list.create`, `shopping_item.create`, `shopping_item.toggle` with `provider="life_assistant"`.

- [ ] **Step 4: Register Shopping router and add failure/audit tests**

Pin invalid list -> 404; project_id is preserved exactly without existence validation; toggle does not mutate name/category/list_id; audit summary does not contain unrelated sensitive payloads.

- [ ] **Step 5: Run Shopping regression tests**

Run:

```bash
cd backend
python -m unittest tests.test_shopping tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add backend/app/api/shopping.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_shopping.py
git commit -m "feat: add shopping cloud api"
```

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

Pin: create requires `name`, `template_type`, `payload_json`; empty PATCH rejected; unauthenticated list -> 401; payload text such as `'{ "b":2, "a":1 }'` returns exactly the same string; non-normalized/opaque string input is not parsed or rewritten.

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

Do not call `json.loads`, serialize, normalize, or move to JSONB. Mutations log `template.create` and `template.update` with `provider="life_assistant"`; execution summaries include template name only, never `payload_json`.

- [ ] **Step 4: Register Templates router and run tests**

Run:

```bash
cd backend
python -m unittest tests.test_templates tests.test_execution_log -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add backend/app/api/templates.py backend/app/models/schemas.py backend/app/main.py backend/tests/test_templates.py
git commit -m "feat: add templates cloud api"
```

---

### Task 6: Extend Project deletion guard for Cloud parity references

**Files:**
- Modify: `backend/app/api/projects.py`
- Modify: `backend/tests/test_projects.py`

**Interfaces:**
- Consumes: `Task`, `Note`, `ShoppingList`.
- Produces: existing `DELETE /api/v1/projects/{project_id}` behavior with 409 when any of those entity types reference the project.

- [ ] **Step 1: Write failing Project guard tests**

Add three explicit cases:

```text
linked Task -> 409
linked Note -> 409
linked ShoppingList -> 409
```

Keep a no-linked-entity case proving the existing delete path remains allowed.

- [ ] **Step 2: Run Project tests and verify the new cases fail**

Run: `cd backend && python -m unittest tests.test_projects -v`

Expected: existing Task guard passes; Note/Shopping guard tests fail until implementation.

- [ ] **Step 3: Extend the guard with minimal queries**

Before starting the delete execution record, check each table for one matching `project_id` using `select(...).limit(1)`. Return 409 when any linked entity exists. Do not add a DB FK or cascade in this task.

- [ ] **Step 4: Run Project tests**

Run: `cd backend && python -m unittest tests.test_projects -v`

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

```bash
git add backend/app/api/projects.py backend/tests/test_projects.py
git commit -m "fix: protect projects with cloud parity references"
```

---

### Task 7: Full backend verification and contract review

**Files:**
- Modify only if verification exposes a defect in files from Tasks 1-6.

**Interfaces:**
- Consumes: all Cloud parity models/routes/tests.
- Produces: a backend tree that imports cleanly, has a valid Alembic chain, and passes the full backend test suite.

- [ ] **Step 1: Run import and migration checks**

```bash
cd backend
python -c "from app.main import app; print('OK')"
alembic upgrade head --sql > /tmp/life-assistant-migrations.sql
```

Expected: `OK`; Alembic completes with revision `20260926_0004` and no chain error.

- [ ] **Step 2: Run full backend tests**

Run: `cd backend && python -m unittest discover -s tests -v`

Expected: PASS with zero failures/errors.

- [ ] **Step 3: Run a contract diff review against the spec**

Check endpoint paths, schema fields/nullability, action types, provider, no extra Phase 2 behavior, and no Note body/Template payload in execution summaries. If implementation differs, fix implementation unless the user explicitly approves a spec change.

- [ ] **Step 4: Verify historical-backfill status honestly**

Confirm whether the repository now contains and executes a real SQLite→PostgreSQL backfill path for these four domains. If none exists, record migration/backfill as `NOT VERIFIED`; do not mark overall historical migration PASS merely because Alembic target-schema migration passes.

- [ ] **Step 5: Commit verification-only fixes if any**

If no source changes were required, do not create an empty commit.

---

### Task 8: CI, deployment, and runtime acceptance

**Files:**
- Modify only when CI/runtime evidence identifies an actual defect.
- Optional documentation evidence update: `doc/cloud_domain_parity_design.md` or the repository's existing acceptance/evidence document, only with actual results.

**Interfaces:**
- Consumes: committed `main` implementation from Tasks 1-7 and existing GitHub Actions deployment pipeline.
- Produces: CI/deployment/runtime evidence with PASS / FAIL / NOT VERIFIED status.

- [ ] **Step 1: Push/commit implementation to `main` and inspect CI**

Expected CI gates from `.github/workflows/ci.yml`:

```text
backend import
Alembic --sql validation
backend unittest discover
Flutter analyze/test/build
GCP script syntax
```

Record exact workflow/run evidence. CI green is necessary but not sufficient for DONE.

- [ ] **Step 2: Follow the existing main → GitHub Actions → Cloud Run deployment path**

Do not bypass the established deployment workflow with an ad-hoc production deploy unless the repository/runtime evidence shows the workflow itself is broken and the project governance allows the repair.

- [ ] **Step 3: Verify Cloud Run health/readiness after deployment**

Check `/health` and `/ready`. Required result: backend reachable and PostgreSQL readiness reports OK.

- [ ] **Step 4: Run acceptance-style API smoke with `[ACCEPTANCE TEST]` data**

With authenticated calls, verify:

```text
Note: create -> update -> read -> create/link second note -> linked read -> delete both
Habit: create -> update -> complete twice -> read completion history
Shopping: create list -> add item -> toggle -> read nested list
Template: create -> update -> read exact payload string
Activity/execution log: verify each mutation family is visible and successful
```

Cleanup only the exact IDs created by this acceptance run. Do not use broad deletes.

- [ ] **Step 5: Verify PostgreSQL persistence/relations**

Prove data survives separate API requests and that Note links, Habit completions, Shopping list/items, and Template payloads persist correctly. Confirm project deletion returns 409 when linked Note or Shopping List exists.

- [ ] **Step 6: Classify final status**

Use:

```text
implementation: PASS / FAIL
backend tests: PASS / FAIL
Alembic target migration: PASS / FAIL
SQLite historical backfill: PASS / FAIL / NOT VERIFIED
CI: PASS / FAIL / NOT VERIFIED
deployment: PASS / FAIL / NOT VERIFIED
runtime CRUD/persistence: PASS / FAIL / NOT VERIFIED
execution log validation: PASS / FAIL / NOT VERIFIED
```

Mark the Cloud target schema/API work `DONE` only if its required implementation/tests/CI/deployment/runtime evidence is complete. Keep the wider SQLite historical migration status separate if no real backfill path exists.

- [ ] **Step 7: Commit evidence/documentation updates only when supported by real results**

Do not mark release checklist items complete from code presence alone.
