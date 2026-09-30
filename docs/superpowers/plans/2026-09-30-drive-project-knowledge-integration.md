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
- `Allow document content to be sent for AI analysis` must be an explicit persisted user setting; default is OFF.
- Existing authorization, execution logging, confirmation, and idempotency conventions apply to new mutations.
- Delivery status remains `PARTIAL` until implementation, tests, CI, deployment, runtime, and integration evidence are all sufficient for `DONE`.

## Review Focus

- **Cross-user Drive isolation:** a signed-in user must never list, mutate, enrich, or obtain picker credentials for another user's Drive workspace/document; Tasks 2, 4, 5, and 7 pin `user_sub` filtering.
- **Repeated Picker selection:** selecting/registering the same Google file repeatedly or into multiple workspaces must upsert one `drive_documents` row and create only unique relationship rows; Task 2 pins this.
- **AI disabled/unavailable:** Project attachment must remain successful and return enrichment `skipped`/`failed` without rollback; Task 7 pins this.
- **Unsupported text extraction:** unsupported files remain attachable/openable, but Drive -> Note import returns `drive_text_unavailable` and creates no Note; Task 5 pins this.
- **Provider access lost later:** refresh/open/import attempts surface the current Google authorization/provider error and never present an old Note snapshot as current Drive content; Tasks 2 and 5 pin this.

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
- Create `backend/tests/test_project_drive_documents.py`
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
- Consumes existing `Base`, `Project`, `Note`, `Tag` / `EntityTag`, and current Google `user_sub` identity.
- Produces model classes: `DriveWorkspace`, `DriveDocument`, `DriveWorkspaceDocument`, `ProjectDriveDocument`, `NoteDriveDocument`, `DriveSettings`, `DriveDocumentEnrichmentRun`, `DriveNoteLinkSuggestion`.
- Produces schema types: `DriveWorkspaceCreate`, `DriveWorkspaceUpdate`, `DriveWorkspaceOut`, `DriveDocumentOut`, `DriveSettingsOut`, `DriveSettingsUpdate`, `DriveNoteLinkSuggestionOut`, `PickerSessionOut`.

- [ ] **Step 1: Write failing model tests**

Assert `DriveWorkspace.user_sub` and `DriveDocument.user_sub` exist; `(user_sub, google_folder_id)` and `(user_sub, google_file_id)` are unique; Project/workspace relationship tables have composite uniqueness; `NoteDriveDocument.relation_type` supports `source_import|related`; `DriveSettings` defaults are `auto_tags_enabled=True`, `suggest_notes_enabled=True`, `allow_ai_content=False`, `max_note_suggestions=5`.

- [ ] **Step 2: Write failing migration test**

Assert revision `20260930_0008` has down revision `20260930_0007`, creates the eight tables above, adds FKs to `projects.id`, `notes.id`, and `drive_documents.id`, and does not alter `google_connections.scopes`.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
cd backend
python -m unittest tests.test_drive_models tests.test_drive_migration -v
```

Expected: FAIL because Drive models/migration do not exist.

- [ ] **Step 4: Implement the models and migration**

Use string UUID PKs consistent with the repository. Persist `user_sub` on `DriveWorkspace`, `DriveDocument`, and `DriveSettings`. Migration is additive only; no destructive rewrite.

- [ ] **Step 5: Verify GREEN and migration SQL**

```bash
python -m unittest tests.test_drive_models tests.test_drive_migration -v
alembic upgrade head --sql > /tmp/drive-knowledge.sql
```

Expected: PASS and generated SQL contains additive DDL only.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/drive.py backend/app/models/drive_schemas.py backend/alembic/env.py backend/alembic/versions/20260930_0008_drive_project_knowledge.py backend/tests/test_drive_models.py backend/tests/test_drive_migration.py
git commit -m "feat: add drive knowledge data model"
```

### Task 2: Google Drive adapter, picker session, workspace/document/settings API

**Files:**
- Create: `backend/app/services/google_drive_files.py`
- Create: `backend/app/services/drive_documents.py`
- Create: `backend/app/api/drive.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_google_drive_files.py`
- Create: `backend/tests/test_drive_api.py`

**Interfaces:**
- Consumes `get_access_token(db, user_sub, SERVICE_SCOPES["drive"][0])` from `google_oauth.py` and Task 1 models/schemas.
- Produces:
  - `DriveFileMetadata(id: str, name: str, mime_type: str, web_view_link: str | None, modified_at: datetime | None)`.
  - `async get_drive_file_metadata(db, user_sub: str, google_file_id: str) -> DriveFileMetadata`.
  - `async get_drive_text(db, user_sub: str, google_file_id: str, mime_type: str) -> str | None`.
  - `async get_picker_session(db, user_sub: str) -> PickerSessionOut`.
- Produces API routes:
  - `GET/POST /api/v1/drive/workspaces`
  - `PATCH/DELETE /api/v1/drive/workspaces/{workspace_id}`
  - `GET/PUT /api/v1/drive/settings`
  - `GET /api/v1/drive/picker-session`
  - `POST /api/v1/drive/documents/register`
  - `GET /api/v1/drive/documents?q=&workspace_id=`
  - `POST /api/v1/drive/documents/{document_id}/refresh`

- [ ] **Step 1: Write failing Google adapter tests**

Mock `httpx.AsyncClient` and assert Drive metadata calls use the current bearer token and minimum fields; Google Docs export as `text/plain`, Google Sheets as `text/csv` (first sheet, matching provider export semantics), Google Slides as `text/plain`, stored `text/*` files download as text, unsupported binary MIME types return `None`, and 401/403 provider responses surface a stable provider error.

- [ ] **Step 2: Write failing API tests for isolation/idempotency/settings**

Cover: user A cannot list/mutate user B workspace/document/settings; workspace creation verifies selected ID is a Google Drive folder; duplicate workspace folder resolves to one row; repeated registration of the same file keeps one `DriveDocument`; the same file may link to multiple workspaces; settings default exactly to Task 1 values; deleting a workspace never calls Google delete.

Also pin cleanup semantics: removing a workspace prunes an unreferenced `DriveDocument` registration only when it has no remaining workspace, Project, or Note relationship; otherwise the document record remains.

- [ ] **Step 3: Run focused tests and verify RED**

```bash
cd backend
python -m unittest tests.test_google_drive_files tests.test_drive_api -v
```

Expected: FAIL.

- [ ] **Step 4: Implement config and adapter**

Add `google_picker_developer_key` and `google_picker_app_id`. `PickerSessionOut` contains `access_token`, `expires_at`, `developer_key`, `app_id`; endpoint responses set `Cache-Control: no-store`. Never log OAuth access tokens.

- [ ] **Step 5: Implement registry/settings service and Drive router**

`POST /drive/documents/register` accepts `google_file_ids: list[str]` plus optional `workspace_id`; fetch metadata before upsert, scope by `current_user["sub"]`, and create unique relationships. Search only PostgreSQL-registered documents; never implement unrestricted Drive search.

- [ ] **Step 6: Verify GREEN and import**

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
- Produces `DriveApi` methods: `getWorkspaces`, `createWorkspace`, `updateWorkspace`, `deleteWorkspace`, `getSettings`, `updateSettings`, `getPickerSession`, `registerDocuments`, `getDocuments`, `refreshDocument`.
- Produces `Future<List<String>> pickDriveItems(PickerSession session, {required bool folders, bool multiSelect = true})`; Web implementation invokes Google Picker, stub throws `UnsupportedError`.

- [ ] **Step 1: Write failing route/page tests**

Assert `More` contains `Google Drive`; `/more/drive` renders registered documents, search, `開啟`, `加入專案`, `轉入 Notes`, and `更多`; empty state says only selected/authorized files appear. At this slice, `加入專案` and `轉入 Notes` render disabled until Tasks 4/5 activate them.

- [ ] **Step 2: Write failing settings tests**

Assert multiple workspaces render independently; add workspace invokes `pickDriveItems(... folders: true)` then `createWorkspace`; enable/default/remove actions call API; settings explain folder selection is not recursive authorization; persisted AI switches render from Task 2 settings.

- [ ] **Step 3: Run Flutter tests and verify RED**

```bash
flutter test test/drive_page_test.dart test/drive_settings_page_test.dart test/web_app_shell_test.dart
```

Expected: FAIL.

- [ ] **Step 4: Implement `DriveApi` and Picker bridge**

For file mode use `DocsView` list mode and optional `MULTISELECT_ENABLED`. For folder mode use `DocsView.setIncludeFolders(true)` plus `setSelectFolderEnabled(true)` and single-select. Set OAuth token/developer key/app ID from `PickerSession`. Cancellation returns an empty list and causes no mutation.

- [ ] **Step 5: Implement pages/routes**

Use `/more/drive` and `/more/drive/settings`. `Add Drive files` opens file Picker then registers IDs; workspace creation opens folder Picker. Drive document search remains app-metadata search only.

- [ ] **Step 6: Verify GREEN, analyze, build**

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
- Modify: `lib/web/drive_page.dart`
- Modify: `lib/web/projects_page.dart`
- Modify: `test/drive_page_test.dart`
- Modify: `test/projects_page_test.dart`

**Interfaces:**
- Consumes Task 1 `ProjectDriveDocument` and Task 2 document ownership helpers.
- Produces routes:
  - `GET /api/v1/projects/{project_id}/drive-documents`
  - `POST /api/v1/projects/{project_id}/drive-documents` body `{drive_document_id}`
  - `DELETE /api/v1/projects/{project_id}/drive-documents/{drive_document_id}`
- Produces Flutter `DriveApi.getProjectDocuments`, `attachDocumentToProject`, `detachDocumentFromProject`.

- [ ] **Step 1: Write failing backend tests**

Assert one document can attach to two Projects, repeated attachment is idempotent, detach affects only one Project, user cannot attach another user's Drive document, and deleting a Project with Drive relationships returns 409 until detached.

- [ ] **Step 2: Run backend test and verify RED**

```bash
cd backend
python -m unittest tests.test_project_drive_documents -v
```

Expected: FAIL.

- [ ] **Step 3: Implement backend relationships**

Use existing execution logging and action-id idempotency conventions. Detach changes only PostgreSQL relationship state and never calls Google Drive.

- [ ] **Step 4: Write failing Flutter tests**

Assert Project workspace renders `關聯文件` with name/type and actions `在 Drive 開啟`, `相關筆記`, `解除關聯`; attach flow selects a registered document; Drive page `加入專案` is now enabled and supports multi-Project selection.

- [ ] **Step 5: Implement UI/API methods**

Do not require Tags in this slice; Task 6 adds Tag rendering after the Tag endpoint exists.

- [ ] **Step 6: Verify GREEN**

```bash
cd backend && python -m unittest tests.test_project_drive_documents -v
cd .. && flutter test test/drive_page_test.dart test/projects_page_test.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/projects.py backend/app/services/drive_documents.py backend/app/models/drive_schemas.py backend/tests/test_project_drive_documents.py lib/web/drive_api.dart lib/web/drive_page.dart lib/web/projects_page.dart test/drive_page_test.dart test/projects_page_test.dart
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
  - `POST /api/v1/drive/documents/{document_id}/notes/import` body `{title?: str, project_id?: str, tags: list[str]}`.
  - `GET /api/v1/drive/documents/{document_id}/notes`.
  - `POST /api/v1/drive/documents/{document_id}/notes/{note_id}` for manual `related` relation.
  - `DELETE /api/v1/drive/documents/{document_id}/notes/{note_id}`.
  - `GET /api/v1/notes/{note_id}/drive-documents`.
- Produces Flutter `DriveApi.importDocumentAsNote`, `getDocumentNotes`, `linkDocumentNote`, `unlinkDocumentNote`, `getNoteDriveDocuments`.

- [ ] **Step 1: Write failing import tests**

Assert Google Docs/Sheets/Slides/readable text produce an independent Note body snapshot and `source_import` relation; changing mocked provider content later does not mutate the Note; unsupported MIME returns machine code `drive_text_unavailable` and creates no Note; provider 403/reauthorization error is surfaced rather than replaced by stale imported text.

- [ ] **Step 2: Write failing relationship tests**

Assert manual `related` relation is unique, visible from both Note and Drive routes, and unlink never deletes Note or Drive document. Scope all document-side operations by `user_sub`.

- [ ] **Step 3: Run backend tests and verify RED**

```bash
cd backend
python -m unittest tests.test_drive_note_import -v
```

Expected: FAIL.

- [ ] **Step 4: Implement import/relationship APIs**

Create the Note with current Notes semantics, apply requested Note Tags using existing Note Tag behavior, then persist `NoteDriveDocument(relation_type="source_import", relation_origin="import")`. Manual links use `related/manual`.

- [ ] **Step 5: Write failing Flutter tests**

Assert Drive `轉入 Notes` now enables, opens title/Project/Tag inputs, and saved Note shows `來源：Google Drive` + `開啟原始 Drive 文件`; existing Note UI can show related Drive docs.

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
- Reuses case-insensitive Tag lookup with `EntityTag(entity_type="drive_document", entity_id=document_id, tag_id=...)`.

- [ ] **Step 1: Write failing Tag tests**

Assert Drive documents reuse existing `Tag` rows case-insensitively, duplicate inputs normalize to one relationship, replacing Drive Tags does not mutate Note Tags, and user A cannot tag user B document.

- [ ] **Step 2: Run RED**

```bash
cd backend
python -m unittest tests.test_drive_tags -v
```

Expected: FAIL.

- [ ] **Step 3: Implement Drive Tag endpoints/service**

Extract a small shared Tag helper only if required to avoid direct copy of Note Tag lookup/replace logic; do not refactor unrelated Tag behavior.

- [ ] **Step 4: Write failing Flutter Tag tests**

Assert Drive cards and Project related-document rows render Tags and manual edit works.

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
- Consumes registered Drive document, extracted text, selected Project context, existing Tag vocabulary, Notes FTS, Task 6 Tag mutation, and Task 5 Note-document relation.
- Produces provider protocol:
  - `async suggest_tags(context: DocumentContext) -> list[TagSuggestion]`.
  - `async rank_related_notes(context: DocumentContext, candidates: list[NoteCandidate], limit: int) -> list[RelatedNoteSuggestion]`.
- Produces adapters:
  - `DisabledAIEnrichmentProvider`.
  - `OpenAIResponsesEnrichmentProvider` using `httpx` + strict Structured Outputs; provider request details stay only in `ai_enrichment.py`.
- Produces config: `ai_enrichment_provider` (`disabled|openai`, default `disabled`), `ai_enrichment_model` (required when provider=`openai`), `ai_enrichment_api_key` (required when provider=`openai`), `ai_enrichment_base_url` default `https://api.openai.com/v1`.
- Fixed v1 scoring/cost constants: `AUTO_TAG_CONFIDENCE_THRESHOLD=0.80`, `RELATED_NOTE_CONFIDENCE_THRESHOLD=0.60`, `MAX_DOCUMENT_CONTEXT_CHARS=12000`, `MAX_NOTE_SNIPPET_CHARS=800`, deterministic candidate cap `20`.
- Produces routes:
  - `POST /api/v1/drive/documents/{document_id}/enrich` with optional `{reanalyze: bool}`.
  - `GET /api/v1/drive/documents/{document_id}/enrichment`.
  - `GET /api/v1/drive/documents/{document_id}/suggestions`.
  - `POST /api/v1/drive/suggestions/{suggestion_id}/decision` body `{decision: "accepted"|"rejected"}`.

- [ ] **Step 1: Write failing privacy/settings tests**

Assert `allow_ai_content=False` prevents any provider call; max suggestions rejects outside `1..10`; user-scoped settings cannot affect another user; the prompt/request payload never includes Google OAuth tokens or permission objects.

- [ ] **Step 2: Write failing retrieval/fingerprint/bounds tests**

Assert candidate retrieval prioritizes same Project/shared Tags/FTS and caps at 20; document context truncates to 12000 chars and candidate snippets to 800; fingerprint changes when analyzed content/settings/model contract changes; unchanged successful fingerprint reuses results; `reanalyze=true` bypasses reuse.

- [ ] **Step 3: Write failing provider/partial-success tests**

Mock OpenAI Responses API and assert structured Tag/rerank results parse; only Tags >=0.80 auto-apply; related Note suggestions below 0.60 are discarded; provider timeout/failure leaves durable Project relationship intact and produces `failed|partial` enrichment state.

- [ ] **Step 4: Write failing suggestion-decision tests**

Assert `pending` suggestions are non-authoritative; `accepted` creates/ensures `NoteDriveDocument(relation_type="related", relation_origin="ai_accepted")`; `rejected` creates none; repeated decision is idempotent; cross-user suggestion access is denied.

- [ ] **Step 5: Run RED**

```bash
cd backend
python -m unittest tests.test_drive_enrichment -v
```

Expected: FAIL.

- [ ] **Step 6: Implement provider abstraction/orchestration**

Use two narrow strict-schema model calls (Tags, rerank), no tools/agent loop. Persist suggestions/status/provider/model/fingerprint only, not a full duplicate of source content.

- [ ] **Step 7: Wire enrichment after Project relationship commit**

When settings allow it, run enrichment only after Project link persistence succeeds. Catch extraction/provider/model errors and return core success plus `partial|failed|skipped` enrichment state without rollback.

- [ ] **Step 8: Verify GREEN**

```bash
cd backend
python -m unittest tests.test_drive_enrichment tests.test_project_drive_documents tests.test_drive_tags -v
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
- Consumes Task 7 enrichment/suggestion endpoints and Task 2 persisted settings.
- Produces `DriveApi.runEnrichment`, `getEnrichment`, `getSuggestions`, `decideSuggestion`.

- [ ] **Step 1: Write failing first-use/privacy UI tests**

When `auto_tags_enabled`/`suggest_notes_enabled` are ON but `allow_ai_content` is OFF, first intelligent-enrichment attempt shows a consent explanation with two choices: enable AI content analysis, or continue core Project attachment without AI. No content is sent before consent.

- [ ] **Step 2: Write failing settings UI tests**

Assert switches for `自動智能 Tag`, `建議相關 Notes`, `允許將文件內容送交 AI 分析`; max suggestions defaults 5 and supports `1..10`; `重新分析` is available; AI-disabled state explicitly says manual Tags/links remain usable.

- [ ] **Step 3: Write failing suggestion-review tests**

Assert at most configured suggestions render with Note title, confidence, reason; pending suggestions expose `接受`/`略過`; accepted relation appears from both Note and Drive views; no UI auto-accepts high-confidence links.

- [ ] **Step 4: Write failing partial-status test**

Project attach with `enrichment_status=failed` still renders the related document and non-blocking `智能整理未完成` status.

- [ ] **Step 5: Run RED**

```bash
flutter test test/drive_settings_page_test.dart test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
```

Expected: FAIL.

- [ ] **Step 6: Implement intelligent-organization UI**

Keep core success and enrichment state visually separate. Accepted AI relationships reuse the same related-document UI as manual relationships; origin is metadata, not a separate knowledge silo.

- [ ] **Step 7: Verify GREEN/full Flutter suite**

```bash
flutter test
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add lib/web/drive_api.dart lib/web/drive_settings_page.dart lib/web/drive_page.dart lib/web/projects_page.dart lib/web/notes_page.dart test/drive_settings_page_test.dart test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
git commit -m "feat: add drive intelligent organization ui"
```

### Task 9: CI, deployment wiring, production runtime acceptance, checkpoint

**Files:**
- Create: `.github/scripts/verify_drive_knowledge_production.mjs`
- Create: `.github/workflows/drive-knowledge-runtime-acceptance.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/deploy-cloud-run.yml` only for non-destructive new Picker/AI runtime config.
- Modify: `.github/workflows/deploy-firebase-hosting.yml` only if Web build requires public Picker configuration.
- Update Drive long-lived checkpoint under allowed `life_assistantGPT` root after runtime evidence exists.

**Interfaces:**
- Consumes all Tasks 1-8 and the existing GitHub Actions deployment path.
- Produces repeatable evidence for registration, multi-Project links, Note import, Tags, AI suggestion acceptance, and AI-failure non-rollback.

- [ ] **Step 1: Write production acceptance script**

Script fails unless a dedicated explicitly selected test file proves: authenticated settings access, registered document, multi-Project relationship, detach-without-provider-delete, supported one-time Note import, source-link readback, Tag readback, suggestion pending-before-accept, accepted relation visible, and AI-failure/non-blocking behavior when failure fixture is enabled.

- [ ] **Step 2: Add runtime workflow and CI syntax check**

Add `node --check .github/scripts/verify_drive_knowledge_production.mjs` to CI. Runtime workflow must report live AI provider `NOT VERIFIED` when `AI_ENRICHMENT_PROVIDER=disabled` or credentials/model are absent; mocked provider tests remain separate evidence.

- [ ] **Step 3: Run complete local verification**

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

- [ ] **Step 4: Commit acceptance/deployment wiring**

```bash
git add .github/scripts/verify_drive_knowledge_production.mjs .github/workflows/drive-knowledge-runtime-acceptance.yml .github/workflows/ci.yml .github/workflows/deploy-cloud-run.yml .github/workflows/deploy-firebase-hosting.yml
git commit -m "test: add drive knowledge production acceptance"
```

- [ ] **Step 5: Verify GitHub Actions and deployments from `main`**

Required evidence: CI PASS, Cloud Run deployment PASS, Firebase Hosting deployment PASS, Alembic migration application PASS. CI alone is not DONE.

- [ ] **Step 6: Run authenticated production/runtime acceptance**

Record per layer:

- Implementation: PASS/FAIL
- Tests: PASS/FAIL
- CI: PASS/FAIL
- Deployment: PASS/FAIL
- Runtime: PASS/FAIL/NOT VERIFIED
- Integration: PASS/FAIL/NOT VERIFIED

If live model credentials/config are absent, AI live-provider integration remains `NOT VERIFIED`; do not hide that behind mocked tests.

- [ ] **Step 7: Write final checkpoint to Drive**

Under `life_assistantGPT`, update/create long-lived acceptance progress with commit SHA, workflow run IDs, deployment revisions/URLs, runtime evidence, remaining `NOT VERIFIED` items, and overall `DONE` or `PARTIAL` according to governance.
