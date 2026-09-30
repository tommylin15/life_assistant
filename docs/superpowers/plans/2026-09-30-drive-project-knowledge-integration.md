# Drive Project Knowledge Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved least-privilege Google Drive workspace, Project relationship, one-time Note import, shared Tag, and AI-assisted related-Note workflow end-to-end in the current Flutter Web + FastAPI + PostgreSQL application.

**Architecture:** Keep `drive.file` and use Google Picker as the only new-file grant boundary. Persist only app-owned Drive metadata/relationships in PostgreSQL, reuse the existing Tag vocabulary, keep Note imports independent from Drive after creation, and place AI behind a provider-agnostic enrichment interface whose failure never rolls back core Drive/Project operations.

**Tech Stack:** Flutter 3.47.3 Web, Riverpod, GoRouter, FastAPI 0.115, SQLAlchemy 2.0 async, PostgreSQL, Alembic, httpx, Google Drive API + Google Picker API, OpenAI Responses API adapter behind an internal enrichment interface, GitHub Actions, Firebase Hosting, Cloud Run.

**Spec:** `docs/superpowers/specs/2026-09-30-drive-project-knowledge-integration-design.md`

## Global Constraints

- Work directly on `main`; no feature branch or PR is required by project governance.
- Keep Google Drive authorization at `https://www.googleapis.com/auth/drive.file`; do not add `drive.readonly`.
- A configured workspace folder is logical organization only; it does not imply recursive access to existing children.
- Original Google Drive files remain the provider source of truth; no v1 API may rename, move, or delete them.
- Drive -> Note is a one-time snapshot import; no automatic or bidirectional sync.
- Drive document -> Project is many-to-many.
- Reuse `tags` / `entity_tags` with `entity_type="drive_document"`; do not create a second Tag system.
- Intelligent organization mode is fixed to: automatic Tags, related-Note suggestions requiring explicit user acceptance, and no automatic Note linking.
- AI enrichment is provider-agnostic at the domain boundary and non-blocking for core operations.
- `Allow document content to be sent for AI analysis` must be an explicit persisted user setting; when false, AI content analysis must not run.
- Existing authorization, execution logging, confirmation, and idempotency conventions apply to new mutations.
- Delivery status remains `PARTIAL` until implementation, tests, CI, deployment, runtime, and integration evidence are all sufficient for `DONE`.

## Review Focus

- **Cross-user Drive isolation:** a signed-in user must never list, mutate, enrich, or obtain picker credentials for another user's Drive workspace/document; Task 2 and Task 4 tests pin `user_sub` filtering.
- **Repeated Picker selection:** selecting/registering the same Google file repeatedly or into multiple workspaces must upsert one `drive_documents` row and create only unique relationship rows; Task 2 tests pin this.
- **AI disabled/unavailable:** Project attachment must remain successful and return an enrichment state of `skipped` or `failed` without rollback; Task 7 tests pin this.
- **Unsupported text extraction:** binary/unsupported files remain attachable/openable but Drive -> Note import must fail explicitly with `drive_text_unavailable` and create no Note; Task 5 tests pin this.
- **Provider access lost later:** refresh/open attempts must surface the current Google authorization/provider error and must not present an old Note snapshot as current Drive content; Task 2 and Task 5 tests pin this.

---

## File Structure

### Backend

- Create `backend/app/models/drive.py` — Drive workspace/document/relationship/settings/enrichment persistence models.
- Create `backend/app/models/drive_schemas.py` — Pydantic request/response types for Drive APIs.
- Create `backend/app/services/google_drive_files.py` — Google Drive token-backed metadata/text/picker-session adapter.
- Create `backend/app/services/drive_documents.py` — workspace/document registry and relationship business rules.
- Create `backend/app/services/drive_enrichment.py` — deterministic candidate retrieval, fingerprinting, Tag normalization, enrichment orchestration.
- Create `backend/app/services/ai_enrichment.py` — provider-neutral protocol + disabled/OpenAI provider adapters.
- Create `backend/app/api/drive.py` — Drive workspace/document/settings/import/enrichment endpoints.
- Modify `backend/app/api/projects.py` — Project <-> Drive-document endpoints and project delete guard.
- Modify `backend/app/api/notes.py` — Note <-> Drive-document read/manual relationship endpoints.
- Modify `backend/app/main.py` — register the Drive router.
- Modify `backend/app/config.py` — Google Picker + AI enrichment configuration.
- Modify `backend/alembic/env.py` — import Drive models for migration metadata.
- Create `backend/alembic/versions/20260930_0008_drive_project_knowledge.py` — additive schema migration.

### Flutter Web

- Create `lib/web/drive_api.dart` — typed HTTP boundary for Drive APIs.
- Create `lib/web/drive_picker.dart`, `lib/web/drive_picker_web.dart`, `lib/web/drive_picker_stub.dart` — conditional Google Picker bridge.
- Create `lib/web/drive_page.dart` — selected-document list, search, document actions.
- Create `lib/web/drive_settings_page.dart` — workspace + intelligent-organization settings.
- Modify `lib/web/web_app.dart` — `/more/drive` and `/more/drive/settings` routes and More entry.
- Modify `lib/web/projects_page.dart` — related Drive documents section and attach/detach flow.
- Modify `lib/web/notes_page.dart` — source/related Drive document section.

### Tests / Acceptance

- Create `backend/tests/test_drive_models.py`
- Create `backend/tests/test_drive_migration.py`
- Create `backend/tests/test_drive_api.py`
- Create `backend/tests/test_google_drive_files.py`
- Create `backend/tests/test_drive_note_import.py`
- Create `backend/tests/test_drive_tags.py`
- Create `backend/tests/test_drive_enrichment.py`
- Create `test/drive_page_test.dart`
- Create `test/drive_settings_page_test.dart`
- Modify `test/projects_page_test.dart`
- Modify `test/notes_page_test.dart`
- Create `.github/scripts/verify_drive_knowledge_production.mjs`
- Create `.github/workflows/drive-knowledge-runtime-acceptance.yml`
- Modify `.github/workflows/ci.yml` to syntax-check the new acceptance script.

---

### Task 1: Drive persistence model and additive migration

**Files:**
- Create: `backend/app/models/drive.py`
- Create: `backend/app/models/drive_schemas.py`
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260930_0008_drive_project_knowledge.py`
- Create: `backend/tests/test_drive_models.py`
- Create: `backend/tests/test_drive_migration.py`

**Interfaces:**
- Consumes: existing `Base`, `Project`, `Note`, `Tag` / `EntityTag`, and current Google `user_sub` identity.
- Produces model classes: `DriveWorkspace`, `DriveDocument`, `DriveWorkspaceDocument`, `ProjectDriveDocument`, `NoteDriveDocument`, `DriveSettings`, `DriveDocumentEnrichmentRun`, `DriveNoteLinkSuggestion`.
- Produces Pydantic types used by later tasks: `DriveWorkspaceCreate`, `DriveWorkspaceUpdate`, `DriveWorkspaceOut`, `DriveDocumentOut`, `DriveSettingsOut`, `DriveSettingsUpdate`, `DriveNoteLinkSuggestionOut`.

- [ ] **Step 1: Write failing model tests**

Add assertions that `DriveWorkspace.user_sub` and `DriveDocument.user_sub` exist; `(user_sub, google_folder_id)` and `(user_sub, google_file_id)` are unique; `ProjectDriveDocument` and `DriveWorkspaceDocument` use composite uniqueness; `NoteDriveDocument.relation_type` accepts `source_import|related`; `DriveSettings` defaults are `auto_tags_enabled=True`, `suggest_notes_enabled=True`, `allow_ai_content=False`, `max_note_suggestions=5`.

- [ ] **Step 2: Write failing migration test**

Assert revision `20260930_0008` has down revision `20260930_0007`, creates the eight tables above, adds FKs to `projects.id`, `notes.id`, and `drive_documents.id`, and does not alter `google_connections.scopes`.

- [ ] **Step 3: Run the focused tests and verify RED**

Run from `backend/`:

```bash
python -m unittest tests.test_drive_models tests.test_drive_migration -v
```

Expected: FAIL because Drive models/migration do not exist.

- [ ] **Step 4: Implement the models and migration**

Use string UUID PKs consistent with the repository. Persist `user_sub` on `DriveWorkspace`, `DriveDocument`, and `DriveSettings`; relationship tables rely on their Drive document/workspace parent for Drive-account isolation. Keep the migration additive; no destructive migration or data rewrite.

- [ ] **Step 5: Run focused tests and offline migration validation**

```bash
python -m unittest tests.test_drive_models tests.test_drive_migration -v
alembic upgrade head --sql > /tmp/drive-knowledge.sql
```

Expected: PASS and generated SQL contains only additive DDL for this feature.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/drive.py backend/app/models/drive_schemas.py backend/alembic/env.py backend/alembic/versions/20260930_0008_drive_project_knowledge.py backend/tests/test_drive_models.py backend/tests/test_drive_migration.py
git commit -m "feat: add drive knowledge data model"
```

### Task 2: Google Drive adapter, picker session, workspace/document registry API

**Files:**
- Create: `backend/app/services/google_drive_files.py`
- Create: `backend/app/services/drive_documents.py`
- Create: `backend/app/api/drive.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_google_drive_files.py`
- Create: `backend/tests/test_drive_api.py`

**Interfaces:**
- Consumes: `get_access_token(db, user_sub, SERVICE_SCOPES["drive"][0])` from `google_oauth.py` and Task 1 models/schemas.
- Produces:
  - `DriveFileMetadata(id: str, name: str, mime_type: str, web_view_link: str | None, modified_at: datetime | None)`.
  - `async get_drive_file_metadata(db, user_sub: str, google_file_id: str) -> DriveFileMetadata`.
  - `async get_drive_text(db, user_sub: str, google_file_id: str, mime_type: str) -> str | None`.
  - `async get_picker_session(db, user_sub: str) -> PickerSessionOut` where `PickerSessionOut` contains `access_token`, `expires_at`, `developer_key`, `app_id` and responses set `Cache-Control: no-store`.
- Produces API routes:
  - `GET/POST /api/v1/drive/workspaces`
  - `PATCH/DELETE /api/v1/drive/workspaces/{workspace_id}`
  - `GET /api/v1/drive/picker-session`
  - `POST /api/v1/drive/documents/register`
  - `GET /api/v1/drive/documents?q=&workspace_id=`
  - `POST /api/v1/drive/documents/{document_id}/refresh`

- [ ] **Step 1: Write failing Google adapter tests**

Mock `httpx.AsyncClient` and assert Drive metadata calls use `Authorization: Bearer <token>`, request only the required metadata fields, Google Docs export as `text/plain`, plain-text files download as text, unsupported binary MIME types return `None`, and 401/403 provider responses surface a stable provider error rather than stale content.

- [ ] **Step 2: Write failing API tests for workspace/document isolation and idempotency**

Cover: user A cannot list/mutate user B workspace/document; duplicate workspace folder returns/ensures one row; repeated registration of the same `google_file_id` keeps one `DriveDocument`; the same document may link to multiple workspaces; deleting a workspace removes only app metadata/relationship and never calls a Google delete endpoint.

- [ ] **Step 3: Run focused backend tests and verify RED**

```bash
python -m unittest tests.test_google_drive_files tests.test_drive_api -v
```

Expected: FAIL because service/router/config do not exist.

- [ ] **Step 4: Implement config and adapter**

Add settings `google_picker_developer_key` and `google_picker_app_id`; do not log their companion OAuth access token. Use the existing refreshed `drive.file` token. Use Google Picker web requirements: OAuth token + developer key + app ID, with the Picker view in list mode for the non-broad Drive scope.

- [ ] **Step 5: Implement registry service and Drive router**

`POST /drive/documents/register` accepts `google_file_ids: list[str]` and optional `workspace_id`; fetch metadata before upsert, enforce `current_user["sub"]`, and create unique workspace-document rows. Search only PostgreSQL-registered documents; do not implement whole-Drive search.

- [ ] **Step 6: Verify GREEN and app import**

```bash
python -m unittest tests.test_google_drive_files tests.test_drive_api -v
python -c "from app.main import app; print('OK')"
```

Expected: PASS / `OK`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/google_drive_files.py backend/app/services/drive_documents.py backend/app/api/drive.py backend/app/config.py backend/app/main.py backend/tests/test_google_drive_files.py backend/tests/test_drive_api.py
git commit -m "feat: add drive workspace registry api"
```

### Task 3: Google Picker bridge and Drive/settings Web UI

**Files:**
- Create: `lib/web/drive_api.dart`
- Create: `lib/web/drive_picker.dart`
- Create: `lib/web/drive_picker_web.dart`
- Create: `lib/web/drive_picker_stub.dart`
- Create: `lib/web/drive_page.dart`
- Create: `lib/web/drive_settings_page.dart`
- Modify: `lib/web/web_app.dart`
- Create: `test/drive_page_test.dart`
- Create: `test/drive_settings_page_test.dart`
- Modify: `test/web_app_shell_test.dart`

**Interfaces:**
- Consumes Task 2 APIs.
- Produces `DriveApi` methods: `getWorkspaces`, `createWorkspace`, `updateWorkspace`, `deleteWorkspace`, `getPickerSession`, `registerDocuments`, `getDocuments`, `refreshDocument`, `getSettings`, `updateSettings`.
- Produces `Future<List<String>> pickDriveItems(PickerSession session, {required bool folders, bool multiSelect = true})`; Web implementation invokes Google Picker, stub throws `UnsupportedError`.

- [ ] **Step 1: Write failing route and Drive page widget tests**

Assert `More` contains `Google Drive`; `/more/drive` renders registered documents and actions `開啟`, `加入專案`, `轉入 Notes`; search filters through `DriveApi.getDocuments`; empty state explicitly says only selected/authorized files appear.

- [ ] **Step 2: Write failing settings widget tests**

Assert multiple workspaces render independently; add workspace invokes `pickDriveItems(... folders: true)` then `createWorkspace`; enable/default/remove actions call API; settings explain folder selection is not recursive authorization; AI controls are visible even before Task 8 wires enrichment actions.

- [ ] **Step 3: Run Flutter tests and verify RED**

```bash
flutter test test/drive_page_test.dart test/drive_settings_page_test.dart test/web_app_shell_test.dart
```

Expected: FAIL because routes/pages/picker bridge do not exist.

- [ ] **Step 4: Implement `DriveApi` and conditional Picker bridge**

Load the Google Picker JavaScript API from the Web implementation, build a `DocsView` in list mode, apply multi-select when requested, set OAuth token/developer key/app ID from `PickerSession`, and return only IDs from a `PICKED` result. Cancellation returns an empty list and causes no mutation.

- [ ] **Step 5: Implement Drive and settings pages + routes**

Use `/more/drive` and `/more/drive/settings`; keep document search over registered app metadata only. Workspace creation uses folder selection, while `Add Drive files` uses file selection and then `registerDocuments`.

- [ ] **Step 6: Verify GREEN, analyze, and Web build**

```bash
flutter test test/drive_page_test.dart test/drive_settings_page_test.dart test/web_app_shell_test.dart
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/web/drive_api.dart lib/web/drive_picker.dart lib/web/drive_picker_web.dart lib/web/drive_picker_stub.dart lib/web/drive_page.dart lib/web/drive_settings_page.dart lib/web/web_app.dart test/drive_page_test.dart test/drive_settings_page_test.dart test/web_app_shell_test.dart
git commit -m "feat: add drive workspace web ui"
```

### Task 4: Project <-> Drive-document relationships and Project UI

**Files:**
- Modify: `backend/app/api/projects.py`
- Modify: `backend/app/services/drive_documents.py`
- Modify: `backend/app/models/drive_schemas.py`
- Create: `backend/tests/test_project_drive_documents.py`
- Modify: `lib/web/drive_api.dart`
- Modify: `lib/web/projects_page.dart`
- Modify: `test/projects_page_test.dart`

**Interfaces:**
- Consumes Task 1 `ProjectDriveDocument` and Task 2 document ownership helpers.
- Produces routes:
  - `GET /api/v1/projects/{project_id}/drive-documents`
  - `POST /api/v1/projects/{project_id}/drive-documents` body `{drive_document_id}`
  - `DELETE /api/v1/projects/{project_id}/drive-documents/{drive_document_id}`
- Produces Flutter `DriveApi.getProjectDocuments`, `attachDocumentToProject`, `detachDocumentFromProject`.

- [ ] **Step 1: Write failing backend relationship tests**

Assert one document can attach to two Projects, repeated attachment is idempotent, detach affects only the selected Project, user cannot attach another user's Drive document, and deleting a Project with Drive relationships returns 409 until they are detached (preserving current linked-entity delete semantics).

- [ ] **Step 2: Run backend test and verify RED**

```bash
cd backend && python -m unittest tests.test_project_drive_documents -v
```

Expected: FAIL.

- [ ] **Step 3: Implement backend relationship endpoints/service methods**

Use execution logging and action-id idempotency for attachment mutation. Do not call Google Drive on detach.

- [ ] **Step 4: Write failing Project widget tests**

Assert Project workspace renders `關聯文件`, shows file name/type/Tags and actions `在 Drive 開啟`, `相關筆記`, `解除關聯`; attach flow allows selecting a registered Drive document.

- [ ] **Step 5: Implement Project UI and API methods**

Keep related documents inside the selected Project workspace; unlink removes only the project relationship.

- [ ] **Step 6: Verify GREEN**

```bash
cd backend && python -m unittest tests.test_project_drive_documents -v
cd .. && flutter test test/projects_page_test.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/projects.py backend/app/services/drive_documents.py backend/app/models/drive_schemas.py backend/tests/test_project_drive_documents.py lib/web/drive_api.dart lib/web/projects_page.dart test/projects_page_test.dart
git commit -m "feat: link drive documents to projects"
```

### Task 5: One-time Drive -> Note import and bidirectional discoverability

**Files:**
- Modify: `backend/app/api/drive.py`
- Modify: `backend/app/api/notes.py`
- Modify: `backend/app/services/drive_documents.py`
- Modify: `backend/app/models/drive_schemas.py`
- Create: `backend/tests/test_drive_note_import.py`
- Modify: `lib/web/drive_api.dart`
- Modify: `lib/web/drive_page.dart`
- Modify: `lib/web/notes_page.dart`
- Modify: `test/drive_page_test.dart`
- Modify: `test/notes_page_test.dart`

**Interfaces:**
- Produces routes:
  - `POST /api/v1/drive/documents/{document_id}/notes/import` body `{title?: str, project_id?: str, tags: list[str]}` -> created `NoteOut` + source relation.
  - `GET /api/v1/drive/documents/{document_id}/notes`
  - `POST /api/v1/drive/documents/{document_id}/notes/{note_id}` for manual `related` relation.
  - `DELETE /api/v1/drive/documents/{document_id}/notes/{note_id}`.
  - `GET /api/v1/notes/{note_id}/drive-documents`.
- Produces Flutter `DriveApi.importDocumentAsNote`, `getDocumentNotes`, `linkDocumentNote`, `unlinkDocumentNote`, `getNoteDriveDocuments`.

- [ ] **Step 1: Write failing import tests**

Assert Google Doc/plain-text content creates an independent Note body snapshot and `source_import` relation; changing mocked provider text afterward does not mutate the Note; unsupported MIME returns API error code `drive_text_unavailable` and creates no Note; provider 403/reauthorization error is surfaced rather than replaced by stale imported text.

- [ ] **Step 2: Write failing relationship tests**

Assert manual `related` relation is unique, visible from both Note and Drive-document routes, cannot self-create a duplicate equivalent row, and deleting a relation never deletes either Note or Drive document.

- [ ] **Step 3: Run backend tests and verify RED**

```bash
cd backend && python -m unittest tests.test_drive_note_import -v
```

Expected: FAIL.

- [ ] **Step 4: Implement import and relationship APIs**

Create the Note using existing Notes semantics, then write `NoteDriveDocument(relation_type="source_import", relation_origin="import")` in the same application transaction boundary; manual links use `relation_type="related", relation_origin="manual"`.

- [ ] **Step 5: Write/extend failing Flutter tests**

Assert Drive `轉入 Notes` opens title/Project/Tag inputs; saved Note shows `來源：Google Drive` and `開啟原始 Drive 文件`; related Drive docs are visible on existing Note UI.

- [ ] **Step 6: Implement UI and verify GREEN**

```bash
cd backend && python -m unittest tests.test_drive_note_import -v
cd .. && flutter test test/drive_page_test.dart test/notes_page_test.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/drive.py backend/app/api/notes.py backend/app/services/drive_documents.py backend/app/models/drive_schemas.py backend/tests/test_drive_note_import.py lib/web/drive_api.dart lib/web/drive_page.dart lib/web/notes_page.dart test/drive_page_test.dart test/notes_page_test.dart
git commit -m "feat: import drive documents into notes"
```

### Task 6: Shared Drive-document Tags

**Files:**
- Modify: `backend/app/api/drive.py`
- Modify: `backend/app/services/drive_documents.py`
- Create: `backend/tests/test_drive_tags.py`
- Modify: `lib/web/drive_api.dart`
- Modify: `lib/web/drive_page.dart`
- Modify: `lib/web/projects_page.dart`
- Modify: `test/drive_page_test.dart`
- Modify: `test/projects_page_test.dart`

**Interfaces:**
- Produces routes:
  - `GET /api/v1/drive/documents/{document_id}/tags`
  - `PUT /api/v1/drive/documents/{document_id}/tags` body `{tags: list[str]}`.
- Reuses case-insensitive Tag lookup behavior from Notes with `EntityTag(entity_type="drive_document", entity_id=document_id, tag_id=...)`.

- [ ] **Step 1: Write failing Tag tests**

Assert Drive documents reuse existing `Tag` rows case-insensitively, duplicate inputs normalize to one relation, replacing Drive Tags does not mutate Note Tags, and user A cannot tag user B document.

- [ ] **Step 2: Run test and verify RED**

```bash
cd backend && python -m unittest tests.test_drive_tags -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Drive Tag endpoints/service**

Extract a small shared Tag helper only if needed to avoid duplicating Note Tag lookup/replace logic; do not refactor unrelated Tag behavior.

- [ ] **Step 4: Write failing Flutter Tag rendering/edit tests**

Assert document cards and Project related-document rows render Tags, manual edit works, and Note Tag UI remains unchanged.

- [ ] **Step 5: Implement UI and verify GREEN**

```bash
cd backend && python -m unittest tests.test_drive_tags -v
cd .. && flutter test test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/drive.py backend/app/services/drive_documents.py backend/tests/test_drive_tags.py lib/web/drive_api.dart lib/web/drive_page.dart lib/web/projects_page.dart test/drive_page_test.dart test/projects_page_test.dart
git commit -m "feat: add tags to drive documents"
```

### Task 7: Provider-agnostic AI enrichment, caching, and suggestion API

**Files:**
- Create: `backend/app/services/ai_enrichment.py`
- Create: `backend/app/services/drive_enrichment.py`
- Modify: `backend/app/api/drive.py`
- Modify: `backend/app/services/drive_documents.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/models/drive_schemas.py`
- Create: `backend/tests/test_drive_enrichment.py`

**Interfaces:**
- Consumes: registered Drive document, extracted text, selected Project context, existing Tag vocabulary, Notes FTS, Task 6 Tag mutation, Task 5 Note-document relation.
- Produces provider protocol:
  - `async suggest_tags(context: DocumentContext) -> list[TagSuggestion]`
  - `async rank_related_notes(context: DocumentContext, candidates: list[NoteCandidate], limit: int) -> list[RelatedNoteSuggestion]`
- Produces adapters:
  - `DisabledAIEnrichmentProvider`.
  - `OpenAIResponsesEnrichmentProvider` using `httpx` and strict Structured Outputs; provider request code stays only in `ai_enrichment.py`.
- Produces config: `ai_enrichment_provider` (`disabled|openai`, default `disabled`), `ai_enrichment_model` (required when provider is `openai`), `ai_enrichment_api_key` (required when provider is `openai`), optional `ai_enrichment_base_url` defaulting to `https://api.openai.com/v1`.
- Produces routes:
  - `GET/PUT /api/v1/drive/settings`
  - `POST /api/v1/drive/documents/{document_id}/enrich`
  - `GET /api/v1/drive/documents/{document_id}/enrichment`
  - `GET /api/v1/drive/documents/{document_id}/suggestions`
  - `POST /api/v1/drive/suggestions/{suggestion_id}/decision` body `{decision: "accepted"|"rejected"}`.

- [ ] **Step 1: Write failing settings/privacy tests**

Assert default `allow_ai_content=False`; when false, provider is never called even if auto Tags/suggestions are enabled; updating max suggestions rejects values outside `1..10`; settings are scoped by `user_sub`.

- [ ] **Step 2: Write failing deterministic retrieval/fingerprint tests**

Assert candidate retrieval prioritizes same Project/shared Tags/FTS and caps at 20; fingerprint changes when analyzed text/settings/model contract changes; unchanged successful fingerprint reuses stored results without provider call; explicit `reanalyze=true` bypasses reuse.

- [ ] **Step 3: Write failing provider and partial-success tests**

Mock the OpenAI Responses endpoint and assert only approved context fields are sent, structured result is parsed into Tags/suggestions, OAuth tokens never appear in request payload, provider timeout/failure leaves an already-created Project relationship intact, and enrichment status becomes `failed`/`partial` instead of rolling back core data.

- [ ] **Step 4: Write failing suggestion-decision tests**

Assert AI suggestions are non-authoritative while `pending`; `accepted` creates/ensures `NoteDriveDocument(relation_type="related", relation_origin="ai_accepted")`; `rejected` creates none; repeated decision is idempotent.

- [ ] **Step 5: Run test and verify RED**

```bash
cd backend && python -m unittest tests.test_drive_enrichment -v
```

Expected: FAIL.

- [ ] **Step 6: Implement provider abstraction and enrichment orchestration**

Use strict JSON-schema structured output for two narrow model calls (Tags, rerank). Do not give the model tools or an agent loop. Persist only suggestions/status/provider/model/fingerprint, not a duplicate of full source text.

- [ ] **Step 7: Wire enrichment to Project attachment after the core relationship commit**

If settings permit, run enrichment after the Project link is durable; return core success plus enrichment state. Catch provider/content errors and convert them to `partial|failed|skipped` without rollback.

- [ ] **Step 8: Verify GREEN**

```bash
cd backend && python -m unittest tests.test_drive_enrichment tests.test_project_drive_documents tests.test_drive_tags -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/ai_enrichment.py backend/app/services/drive_enrichment.py backend/app/api/drive.py backend/app/services/drive_documents.py backend/app/config.py backend/app/models/drive_schemas.py backend/tests/test_drive_enrichment.py
git commit -m "feat: add drive ai enrichment"
```

### Task 8: Intelligent-organization review UI

**Files:**
- Modify: `lib/web/drive_api.dart`
- Modify: `lib/web/drive_settings_page.dart`
- Modify: `lib/web/drive_page.dart`
- Modify: `lib/web/projects_page.dart`
- Modify: `lib/web/notes_page.dart`
- Modify: `test/drive_settings_page_test.dart`
- Modify: `test/drive_page_test.dart`
- Modify: `test/projects_page_test.dart`
- Modify: `test/notes_page_test.dart`

**Interfaces:**
- Consumes Task 7 settings/enrichment/suggestion endpoints.
- Produces `DriveApi.runEnrichment`, `getEnrichment`, `getSuggestions`, `decideSuggestion` and persisted settings controls.

- [ ] **Step 1: Write failing settings UI tests**

Assert switches for `自動智能 Tag`, `建議相關 Notes`, `允許將文件內容送交 AI 分析`; max-suggestion control defaults to 5; `重新分析` is available on documents; AI-disabled state explains manual Tags/links remain usable.

- [ ] **Step 2: Write failing suggestion-review tests**

Assert at most configured suggestions render with Note title, confidence, and reason; pending suggestions expose `接受`/`略過`; accepted relation appears in both Note and Drive-document views; no UI path auto-accepts high-confidence items.

- [ ] **Step 3: Write failing partial-status test**

Project attach with mocked `enrichment_status=failed` still renders the attached document and a non-blocking `智能整理未完成` status.

- [ ] **Step 4: Run Flutter tests and verify RED**

```bash
flutter test test/drive_settings_page_test.dart test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
```

Expected: FAIL.

- [ ] **Step 5: Implement intelligent-organization UI**

Keep core success and enrichment status visually separate. Accepted AI relationships use the same related-document UI as manual relationships, with optional origin/status detail but no separate knowledge silo.

- [ ] **Step 6: Verify GREEN and full Flutter suite**

```bash
flutter test
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add lib/web/drive_api.dart lib/web/drive_settings_page.dart lib/web/drive_page.dart lib/web/projects_page.dart lib/web/notes_page.dart test/drive_settings_page_test.dart test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
git commit -m "feat: add drive intelligent organization ui"
```

### Task 9: CI, deployment wiring, production runtime acceptance, and checkpoint

**Files:**
- Create: `.github/scripts/verify_drive_knowledge_production.mjs`
- Create: `.github/workflows/drive-knowledge-runtime-acceptance.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/deploy-cloud-run.yml` only for non-destructive new environment/config wiring needed by Picker/AI.
- Modify: `.github/workflows/deploy-firebase-hosting.yml` only if Web build needs Picker public configuration.
- Update after verification: `docs/superpowers/specs/2026-09-30-drive-project-knowledge-integration-design.md` status/checkpoint note if project documentation convention calls for it.
- Update Drive long-lived checkpoint under allowed `life_assistantGPT` root after runtime evidence exists.

**Interfaces:**
- Consumes all Tasks 1-8 and existing GitHub Actions deployment path.
- Produces repeatable runtime evidence for Drive registration, Project links, Note import, Tags, AI suggestion acceptance, and AI-failure non-rollback.

- [ ] **Step 1: Write the acceptance script first**

`verify_drive_knowledge_production.mjs` must fail unless it can prove, with a dedicated explicitly selected test file/account fixture: authenticated Drive settings access, registered selected document, multi-Project relationship, detach-without-provider-delete, supported one-time Note import, source link readback, Tag readback, suggestion pending-before-accept, accepted relation visible, and AI-failure/non-blocking behavior when the workflow fixture enables the failure path.

- [ ] **Step 2: Add workflow and CI syntax test**

Add `node --check .github/scripts/verify_drive_knowledge_production.mjs` to CI. Runtime workflow must not assume AI success when `AI_ENRICHMENT_PROVIDER=disabled`; report `NOT VERIFIED` for live AI provider acceptance until production model credentials/config are present.

- [ ] **Step 3: Run all local verification**

```bash
flutter analyze --no-fatal-infos
flutter test
flutter build web --target=lib/main_web.dart
cd backend
python -c "from app.main import app; print('OK')"
alembic upgrade head --sql > /tmp/life-assistant-migrations.sql
python -m unittest discover -s tests -v
cd ..
node --check .github/scripts/verify_drive_knowledge_production.mjs
```

Expected: all PASS.

- [ ] **Step 4: Commit deployment/acceptance changes**

```bash
git add .github/scripts/verify_drive_knowledge_production.mjs .github/workflows/drive-knowledge-runtime-acceptance.yml .github/workflows/ci.yml .github/workflows/deploy-cloud-run.yml .github/workflows/deploy-firebase-hosting.yml
git commit -m "test: add drive knowledge production acceptance"
```

- [ ] **Step 5: Push/confirm `main` and track GitHub Actions**

Required evidence:

- CI: PASS
- Cloud Run deployment: PASS
- Firebase Hosting deployment: PASS
- Alembic migration application: PASS

Do not call the feature DONE from CI alone.

- [ ] **Step 6: Run authenticated production/runtime acceptance**

Verify a real Picker-selected Drive file on the deployed app and record:

- Implementation: PASS/FAIL
- Tests: PASS/FAIL
- CI: PASS/FAIL
- Deployment: PASS/FAIL
- Runtime: PASS/FAIL/NOT VERIFIED
- Integration: PASS/FAIL/NOT VERIFIED

If model credentials are not configured, mark AI live-provider integration `NOT VERIFIED` while still reporting deterministic/provider-mocked tests separately.

- [ ] **Step 7: Write the final checkpoint to Drive**

Under the allowed `life_assistantGPT` root, update/create the long-lived acceptance progress document with commit SHA, workflow run IDs, deployment revisions/URLs, runtime test evidence, remaining `NOT VERIFIED` items, and overall `DONE` or `PARTIAL` according to project governance.
