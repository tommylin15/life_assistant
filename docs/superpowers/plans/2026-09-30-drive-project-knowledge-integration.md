# Drive Project Knowledge Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the approved least-privilege Google Drive workspace, Project relationship, one-time Note import, shared Tag, and AI-assisted related-Note workflow end-to-end in the current Flutter Web + FastAPI + PostgreSQL application.

**Architecture:** Keep `drive.file` and use Google Picker as the only new-file grant boundary. The backend never sends its stored Google OAuth access/refresh token to Flutter; instead it returns only Picker-safe public configuration, and the browser obtains a separate short-lived Google Identity Services token scoped exactly to `drive.file` for Picker use. PostgreSQL remains the source of truth for app-owned Drive metadata/relationships, Note imports remain independent snapshots, and AI stays behind a provider-agnostic non-blocking enrichment interface.

**Tech Stack:** Flutter Web / Dart 3.13, Riverpod, GoRouter, FastAPI, SQLAlchemy async, PostgreSQL, Alembic, httpx, Google Drive API + Google Picker API + Google Identity Services, optional OpenAI Responses API adapter behind an internal enrichment interface, GitHub Actions, Firebase Hosting, Cloud Run.

**Spec:** `docs/superpowers/specs/2026-09-30-drive-project-knowledge-integration-design.md`

## Global Constraints

- Work directly on `main`; no feature branch or PR is required by project governance.
- Keep Google Drive authorization at `https://www.googleapis.com/auth/drive.file`; do not add `drive.readonly`.
- Google Picker is the explicit file-selection/grant boundary. A configured workspace folder is logical organization only and never means recursive access to existing children.
- The backend Google token may contain several already-approved service scopes; **never return that token or the refresh token to the browser**.
- Picker obtains its own in-memory, short-lived browser token through Google Identity Services with scope exactly `https://www.googleapis.com/auth/drive.file`.
- Backend Picker configuration may expose only the Web OAuth client ID, restricted Picker API key, app ID/project number, and the fixed `drive.file` scope. It must never expose `GOOGLE_CLIENT_SECRET` or stored tokens.
- Selected Google file IDs are sent to the backend; the backend re-fetches metadata/content using its server-side Drive authorization and remains the authority on whether a selected file is readable.
- Original Google Drive files remain the provider source of truth; no v1 API may rename, move, or delete them.
- Drive -> Note is a one-time snapshot import; no automatic or bidirectional sync.
- Drive document -> Project is many-to-many.
- Reuse `tags` / `entity_tags` with `entity_type="drive_document"`; do not create a second Tag system.
- Intelligent organization mode is fixed to: automatic Tags, related-Note suggestions requiring explicit user acceptance, and no automatic Note linking.
- `Allow document content to be sent for AI analysis` is a persisted explicit user setting and defaults to OFF.
- AI enrichment is provider-agnostic and non-blocking. Project attachment commits before enrichment; enrichment failure never rolls back a successful Project relationship.
- AI candidate retrieval caps at 20 Notes; user-visible related-Note suggestions default to 5.
- `AI_ENRICHMENT_PROVIDER=disabled` is a supported production mode. Do not assume any production model credential exists.
- Adding/changing a production AI secret is a separate high-risk deployment action and requires explicit confirmation under project governance when applicable.
- Existing authorization, execution logging, confirmation, and idempotency conventions apply to new mutations.
- Removing workspaces, internal document registrations, Tags, or app relationships must never delete the provider file.
- Delivery status remains `PARTIAL` until implementation, tests, CI, deployment, runtime, and integration evidence are sufficient for `DONE`.

## Review Focus

- **Cross-user Drive isolation:** user A must never list, mutate, enrich, or relate user B’s workspace/document; Tasks 2, 4, 5, 6, and 7 pin `owner_sub`/`user_sub` filtering.
- **Picker token minimization and account mismatch:** Picker uses a separate browser `drive.file` token only; selected IDs are still verified by the backend, and an ID inaccessible to the signed-in backend Google account fails cleanly instead of being registered; Tasks 2 and 3 pin this.
- **Repeated Picker selection:** selecting the same Google file repeatedly or into multiple workspaces keeps one provider record per `(owner_sub, google_file_id)` and unique relationship rows; Task 2 pins this.
- **Unsupported text extraction:** unsupported binary files remain attachable/openable but Drive -> Note returns `drive_text_unavailable` and creates no Note; Task 5 pins this.
- **AI disabled/unavailable:** core Project attachment remains committed and returns enrichment `skipped|partial|failed` without rollback; Task 7 pins this.

---

## File Structure

### Backend

- Create `backend/app/models/drive.py` — Drive workspace/document/relationship/settings/enrichment persistence models.
- Create `backend/app/models/drive_schemas.py` — Pydantic request/response types for Drive APIs.
- Create `backend/app/services/google_api.py` — shared authenticated Google HTTP request helper extracted from the current Google integrations router.
- Create `backend/app/services/google_drive_files.py` — Drive metadata/readable-text adapter; no provider mutations.
- Create `backend/app/services/tag_service.py` — generic EntityTag operations reused by Notes and Drive documents.
- Create `backend/app/services/drive_documents.py` — workspace/document registry and relationship business rules.
- Create `backend/app/services/ai_enrichment.py` — provider-neutral protocol + disabled/OpenAI adapter.
- Create `backend/app/services/drive_enrichment.py` — deterministic candidates, fingerprint/cache, Tag application, suggestion persistence, partial-success orchestration.
- Create `backend/app/api/drive.py` — `/api/v1/drive/*` application endpoints.
- Modify `backend/app/api/google_integrations.py` — consume extracted `google_api` helper without changing Gmail/Calendar/Bridge behavior.
- Modify `backend/app/api/projects.py` — Project delete guard for Drive relationships.
- Modify `backend/app/api/notes.py` — reuse generic Tag service and clean Note-Drive relationships on Note deletion.
- Modify `backend/app/main.py` — register Drive router/model metadata.
- Modify `backend/app/config.py`, `backend/.env.example` — Picker/AI configuration.
- Modify `backend/alembic/env.py` — import Drive models for migration metadata if required by current Alembic pattern.
- Create `backend/alembic/versions/20260930_0008_drive_project_knowledge.py` — additive schema migration.

### Flutter Web

- Create `lib/web/drive_api.dart` — HTTP boundary for Drive APIs.
- Create `lib/web/google_drive_picker.dart`, `lib/web/google_drive_picker_web.dart`, `lib/web/google_drive_picker_stub.dart` — testable Picker abstraction.
- Create `lib/web/drive_page.dart` — registered selected-document manager.
- Create `lib/web/drive_settings_page.dart` — workspace + intelligent-organization settings.
- Create `web/google_drive_picker_bridge.js` — minimal Picker + Google Identity Services bridge.
- Modify `web/index.html` — load the bridge/scripts required by the Web-only implementation.
- Modify `lib/web/api_client.dart`, `lib/web/web_app.dart` — API plumbing, `/more/drive`, `/more/drive/settings`, More entry.
- Modify `lib/web/projects_page.dart`, `lib/web/project_api.dart` — related Drive documents.
- Modify `lib/web/notes_page.dart`, `lib/web/note_api.dart` — source/related Drive documents.

### Tests / Acceptance

- Create `backend/tests/test_drive_models.py`
- Create `backend/tests/test_drive_migration.py`
- Create `backend/tests/test_tag_service.py`
- Create `backend/tests/test_google_api_service.py`
- Create `backend/tests/test_google_drive_files.py`
- Create `backend/tests/test_drive_api.py`
- Create `backend/tests/test_project_drive_documents.py`
- Create `backend/tests/test_drive_note_import.py`
- Create `backend/tests/test_drive_tags.py`
- Create `backend/tests/test_drive_enrichment.py`
- Create `test/drive_page_test.dart`
- Create `test/drive_settings_page_test.dart`
- Modify `test/projects_page_test.dart`, `test/notes_page_test.dart`, `test/web_app_shell_test.dart`
- Create `.github/scripts/verify_drive_knowledge_production.mjs`
- Create `.github/workflows/drive-knowledge-runtime-acceptance.yml`
- Modify existing CI/deploy workflows only where the new test/config path requires it.

---

### Task 1: Drive persistence model and additive migration

**Files:**
- Create: `backend/app/models/drive.py`
- Create: `backend/app/models/drive_schemas.py`
- Modify: `backend/alembic/env.py` if required by current metadata-import pattern
- Create: `backend/alembic/versions/20260930_0008_drive_project_knowledge.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_drive_models.py`
- Test: `backend/tests/test_drive_migration.py`

**Interfaces:**
- Consumes existing `Base`, `Project`, `Note`, `Tag` / `EntityTag`, and authenticated Google `user["sub"]` identity.
- Produces ORM classes `DriveWorkspace`, `DriveDocument`, `DriveWorkspaceDocument`, `ProjectDriveDocument`, `NoteDriveDocument`, `DriveAiSettings`, `DriveDocumentEnrichmentRun`, `DriveNoteLinkSuggestion`.
- Produces migration revision `20260930_0008`, revising `20260930_0007`.

- [ ] **Step 1: Write failing model tests**

Assert `owner_sub` is required on workspaces/documents/settings; `(owner_sub, google_folder_id)` and `(owner_sub, google_file_id)` are unique; relationship tables use composite uniqueness; `DriveAiSettings` defaults are `auto_tags=True`, `suggest_related_notes=True`, `allow_content_analysis=False`, `max_related_notes=5`; relation values are validated at schema/service boundaries as `source_import|related` and `manual|ai_accepted|import`.

- [ ] **Step 2: Write failing migration tests**

Assert `down_revision == "20260930_0007"`, all eight tables are created, relationship FKs point to existing Project/Note tables, and one active default workspace per owner is enforced with a PostgreSQL partial unique index. Assert no existing Google OAuth scope/token column is widened or rewritten.

- [ ] **Step 3: Run tests and verify RED**

```bash
cd backend
pytest -q tests/test_drive_models.py tests/test_drive_migration.py
```

Expected: FAIL because Drive models/migration do not exist.

- [ ] **Step 4: Implement models and additive migration**

Use `String(36)` UUID storage to match the current domain. New Drive records are user-scoped; association rows reference the scoped document/workspace records. No destructive migration or data rewrite.

- [ ] **Step 5: Register model metadata and verify GREEN**

```bash
cd backend
pytest -q tests/test_drive_models.py tests/test_drive_migration.py tests/test_alembic_metadata_bootstrap_apply.py tests/test_cloud_domain_models.py
alembic upgrade head --sql > /tmp/drive-knowledge.sql
```

Expected: PASS and SQL contains additive DDL only.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/drive.py backend/app/models/drive_schemas.py backend/app/main.py backend/alembic/env.py backend/alembic/versions/20260930_0008_drive_project_knowledge.py backend/tests/test_drive_models.py backend/tests/test_drive_migration.py
git commit -m "feat: add drive knowledge data model"
```

### Task 2: Shared Google request helper, Drive adapter, Picker config, workspace/document registry

**Files:**
- Create: `backend/app/services/google_api.py`
- Create: `backend/app/services/google_drive_files.py`
- Create: `backend/app/services/drive_documents.py`
- Create: `backend/app/api/drive.py`
- Modify: `backend/app/api/google_integrations.py`
- Modify: `backend/app/config.py`, `backend/.env.example`, `backend/app/main.py`
- Test: `backend/tests/test_google_api_service.py`
- Test: `backend/tests/test_google_drive_files.py`
- Test: `backend/tests/test_drive_api.py`
- Regression: existing `backend/tests/test_google_integrations.py`

**Interfaces:**
- Produces `async request_google(db, user_sub, scope, method, url, **kwargs) -> httpx.Response` with the current Google retry/error behavior moved out of the integrations router.
- Produces `DriveFileMetadata(id, name, mime_type, web_view_link, modified_at, parents)` and `DriveTextResult(supported, text, source_mime_type)`.
- Produces `async get_drive_file_metadata(db, user_sub, google_file_id) -> DriveFileMetadata` and `async read_drive_text(...) -> DriveTextResult`.
- Produces `GET /api/v1/drive/picker-config` -> `PickerConfigOut(client_id, developer_key, app_id, scope)` where scope is exactly `drive.file`; **no OAuth token fields exist**.
- Produces workspace/settings/document registry endpoints:
  - `GET/POST /api/v1/drive/workspaces`
  - `PATCH/DELETE /api/v1/drive/workspaces/{workspace_id}`
  - `GET/PUT /api/v1/drive/ai-settings`
  - `GET /api/v1/drive/documents?q=&workspace_id=`
  - `POST /api/v1/drive/documents/register`
  - `POST /api/v1/drive/documents/{document_id}/refresh`
  - `DELETE /api/v1/drive/documents/{document_id}`

- [ ] **Step 1: Write failing shared-Google-request regression tests**

Pin current behavior: refresh once on `401`; repeated `401/403` -> stable permission/reauthorization error; network failure -> `503`; other provider error -> `502`.

- [ ] **Step 2: Extract `request_google` and migrate existing Google integrations calls**

Public Gmail/Calendar/Drive Bridge behavior must not change.

- [ ] **Step 3: Write failing Drive read tests**

Pin supported v1 extraction: Google Docs `text/plain`, Sheets `text/csv` (first-sheet semantics), Slides `text/plain`, stored `text/*`/JSON/CSV/Markdown as bounded text; PDF/Office binary/images/audio/video/unknown -> `supported=False` with no fabricated text. Metadata must capture only required provider identity/view fields, not persist permission lists.

- [ ] **Step 4: Write failing Picker config security tests**

Assert authenticated endpoint returns exactly client ID, developer key, app ID, and fixed `drive.file` scope. Assert response contains no `client_secret`, `access_token`, `refresh_token`, Gmail scope, or Calendar scope. Missing Picker config returns a stable configuration error.

- [ ] **Step 5: Write failing workspace/settings/registration tests**

Cover user isolation, folder MIME verification, one default workspace per owner, duplicate folder/file idempotency, same file in multiple workspaces, registered-metadata search only, settings defaults, and repeated file registration. Selected file metadata is always re-fetched by backend; never trust Picker-provided name/URL. A file ID inaccessible to the backend’s signed-in Drive authorization fails registration.

- [ ] **Step 6: Implement Drive backend**

Add Picker config settings `google_picker_developer_key`, `google_picker_app_id`; reuse existing `google_client_id` as public Web client ID. `POST /documents/register` accepts 1..100 unique `google_file_ids` plus optional workspace ID, re-fetches metadata, then upserts `(owner_sub, google_file_id)` and associations. Search never calls unrestricted Google Drive search.

- [ ] **Step 7: Add internal unregister guard**

`DELETE /drive/documents/{id}` requires target-bound explicit confirmation. Return `409` while any workspace/Project/Note relationship references the document. Allowed deletion cleans app-owned Tags/suggestions/enrichment metadata only and never invokes Google file deletion.

- [ ] **Step 8: Verify GREEN**

```bash
cd backend
pytest -q tests/test_google_api_service.py tests/test_google_drive_files.py tests/test_drive_api.py tests/test_google_integrations.py
python -c "from app.main import app; print('OK')"
```

Expected: PASS / `OK`.

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/google_api.py backend/app/services/google_drive_files.py backend/app/services/drive_documents.py backend/app/api/drive.py backend/app/api/google_integrations.py backend/app/config.py backend/.env.example backend/app/main.py backend/tests/test_google_api_service.py backend/tests/test_google_drive_files.py backend/tests/test_drive_api.py
git commit -m "feat: add drive workspace registry backend"
```

### Task 3: Google Identity Services Picker bridge and Drive/settings Web UI

**Files:**
- Create: `web/google_drive_picker_bridge.js`
- Modify: `web/index.html`
- Create: `lib/web/google_drive_picker.dart`, `lib/web/google_drive_picker_web.dart`, `lib/web/google_drive_picker_stub.dart`
- Create: `lib/web/drive_api.dart`, `lib/web/drive_page.dart`, `lib/web/drive_settings_page.dart`
- Modify: `lib/web/api_client.dart`, `lib/web/web_app.dart`
- Test: `test/drive_page_test.dart`, `test/drive_settings_page_test.dart`, `test/web_app_shell_test.dart`

**Interfaces:**
- `GoogleDrivePicker.pickFiles({String? folderId, bool allowMultiple = true}) -> Future<List<String>>` returns provider IDs only.
- `GoogleDrivePicker.pickFolder() -> Future<String?>` returns one folder ID.
- `DriveApi.getPickerConfig()` returns `clientId/developerKey/appId/scope`; no token.
- Routes `/more/drive` and `/more/drive/settings`; More adds `Google Drive`.

- [ ] **Step 1: Write failing Picker abstraction tests**

Widget tests inject a fake picker; no real Google script/OAuth opens under `flutter test`.

- [ ] **Step 2: Implement Web bridge with separate browser token**

Load Google Identity Services + Picker. Call `google.accounts.oauth2.initTokenClient` with the returned client ID and scope exactly `https://www.googleapis.com/auth/drive.file`; hold the returned access token only in memory, then pass it to `PickerBuilder.setOAuthToken`. Use the returned restricted developer key/app ID. Never read, receive, persist, or reuse the backend’s stored Google token. Cancellation returns no IDs and causes no mutation.

- [ ] **Step 3: Implement file/folder Picker modes**

File mode uses list-oriented Docs view and optional multi-select. Folder mode allows folder selection and single-select. Return selected IDs only. Where supported, give GIS the current signed-in account as a hint; backend access verification remains authoritative if the Picker account differs.

- [ ] **Step 4: Write failing Drive/settings widget tests**

Cover registered document search, `Open`, disabled-until-ready `Add to Project`/`Convert to Note`, workspace filters, empty state explaining selected-only scope, reauthorization/provider errors, multiple workspace CRUD, default workspace, AI setting defaults, and explicit text that workspace folders are not recursively indexed.

- [ ] **Step 5: Implement pages/routes and registration flow**

`Add Drive files` -> Picker -> send IDs to backend -> render backend-returned metadata. Workspace add -> folder Picker -> backend verifies folder metadata. Open uses the Google-provided web view link through existing browser navigation.

- [ ] **Step 6: Verify GREEN, analyze, build**

```bash
flutter test test/drive_page_test.dart test/drive_settings_page_test.dart test/web_app_shell_test.dart
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/google_drive_picker_bridge.js web/index.html lib/web/google_drive_picker.dart lib/web/google_drive_picker_web.dart lib/web/google_drive_picker_stub.dart lib/web/drive_api.dart lib/web/drive_page.dart lib/web/drive_settings_page.dart lib/web/api_client.dart lib/web/web_app.dart test/drive_page_test.dart test/drive_settings_page_test.dart test/web_app_shell_test.dart
git commit -m "feat: add drive picker workspace ui"
```

### Task 4: Project <-> Drive-document relationships and Project UI

**Files:**
- Modify: `backend/app/api/drive.py`, `backend/app/api/projects.py`, `backend/app/services/drive_documents.py`, `backend/app/models/drive_schemas.py`
- Test: `backend/tests/test_project_drive_documents.py`, regression `backend/tests/test_projects.py`
- Modify: `lib/web/drive_api.dart`, `lib/web/drive_page.dart`, `lib/web/project_api.dart`, `lib/web/projects_page.dart`
- Modify: `test/drive_page_test.dart`, `test/projects_page_test.dart`

**Interfaces:**
- Schema `DriveProjectLinksCreate(project_ids: list[str])`, 1..100 unique IDs.
- Endpoints:
  - `GET /api/v1/drive/project-documents`
  - `POST /api/v1/drive/documents/{document_id}/projects`
  - `DELETE /api/v1/drive/documents/{document_id}/projects/{project_id}`
- Flutter supports multi-Project attach and single Project detach.

- [ ] **Step 1: Write failing backend relationship tests**

Assert one document links to multiple Projects; repeated bulk attach is idempotent; unknown Project -> `404`; cross-user document is not linkable; detach affects only the specified Project and never unregisters/deletes the provider file.

- [ ] **Step 2: Write failing Project delete guard**

A Project with `ProjectDriveDocument` returns `409 "Project has linked Drive documents"`, matching current linked task/note/shopping safety.

- [ ] **Step 3: Implement backend relations and commit before enrichment exists**

Use existing execution logging/idempotency conventions. No AI call in this task.

- [ ] **Step 4: Write failing Project/Drive widget tests**

Drive `Add to Project` supports multi-select. Project renders `關聯文件` with file name/type and actions `在 Drive 開啟`, `相關筆記`, `解除關聯`.

- [ ] **Step 5: Implement UI and verify GREEN**

```bash
cd backend && pytest -q tests/test_project_drive_documents.py tests/test_projects.py
cd .. && flutter test test/drive_page_test.dart test/projects_page_test.dart
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/drive.py backend/app/api/projects.py backend/app/services/drive_documents.py backend/app/models/drive_schemas.py backend/tests/test_project_drive_documents.py backend/tests/test_projects.py lib/web/drive_api.dart lib/web/drive_page.dart lib/web/project_api.dart lib/web/projects_page.dart test/drive_page_test.dart test/projects_page_test.dart
git commit -m "feat: link drive documents to projects"
```

### Task 5: One-time Drive -> Note import and Note/Drive discoverability

**Files:**
- Modify: `backend/app/api/drive.py`, `backend/app/api/notes.py`, `backend/app/services/drive_documents.py`, `backend/app/models/drive_schemas.py`
- Test: `backend/tests/test_drive_note_import.py`, regression `backend/tests/test_notes.py`
- Modify: `lib/web/drive_api.dart`, `lib/web/drive_page.dart`, `lib/web/note_api.dart`, `lib/web/notes_page.dart`
- Modify: `test/drive_page_test.dart`, `test/notes_page_test.dart`

**Interfaces:**
- `POST /api/v1/drive/documents/{document_id}/note-import` with optional title/project and Tags.
- `GET/POST/DELETE` Drive-document <-> Note related relationship endpoints.
- `GET /api/v1/drive/notes/{note_id}/documents` for reverse discoverability.
- `source_import/import` for snapshot source; `related/manual` for manual relationship.

- [ ] **Step 1: Write failing supported import tests**

Readable content creates a normal independent Note, optional `project_id`, requested Tags, and `source_import` relationship. Omitted title defaults to provider filename. Later provider content changes do not mutate the Note.

- [ ] **Step 2: Write failing unsupported/provider-error tests**

Unsupported binary -> stable `422 drive_text_unavailable`, no Note/relationship, Drive document stays registered/openable. Lost provider access surfaces the current Google error; never present an old Note snapshot as current Drive content.

- [ ] **Step 3: Write failing manual relationship tests**

Manual related relation is unique and visible from both directions; unlink deletes only the relationship. Cross-user Drive document relationship requests fail.

- [ ] **Step 4: Implement import/relationship APIs and Note deletion cleanup**

Note deletion cleans its `NoteDriveDocument` rows along with existing NoteLink/EntityTag cleanup. Execution summaries never contain document/Note body text.

- [ ] **Step 5: Write failing Flutter import/source tests and implement UI**

`Convert to Note` becomes active; dialog supports title, Project, Tags; imported Note displays `來源：Google Drive` + `開啟原始文件`; related Drive files are separately labeled.

- [ ] **Step 6: Verify GREEN**

```bash
cd backend && pytest -q tests/test_drive_note_import.py tests/test_notes.py
cd .. && flutter test test/drive_page_test.dart test/notes_page_test.dart
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/drive.py backend/app/api/notes.py backend/app/services/drive_documents.py backend/app/models/drive_schemas.py backend/tests/test_drive_note_import.py backend/tests/test_notes.py lib/web/drive_api.dart lib/web/drive_page.dart lib/web/note_api.dart lib/web/notes_page.dart test/drive_page_test.dart test/notes_page_test.dart
git commit -m "feat: import drive documents into notes"
```

### Task 6: Generic Tag service and Drive-document Tags

**Files:**
- Create: `backend/app/services/tag_service.py`
- Modify: `backend/app/api/notes.py`, `backend/app/api/drive.py`
- Test: `backend/tests/test_tag_service.py`, `backend/tests/test_drive_tags.py`, regression `backend/tests/test_notes.py`
- Modify: `lib/web/drive_api.dart`, `lib/web/drive_page.dart`, `lib/web/projects_page.dart`
- Modify: `test/drive_page_test.dart`, `test/projects_page_test.dart`

**Interfaces:**
- `list_entity_tags`, `replace_entity_tags`, `add_entity_tags` mutate/read generic `Tag`/`EntityTag`; transaction ownership remains with caller.
- Drive endpoints `GET/PUT /api/v1/drive/documents/{document_id}/tags`.

- [ ] **Step 1: Write failing generic Tag tests**

Pin case-insensitive Tag reuse, de-duplication, replace semantics, additive merge, and the invariant that additive AI behavior never removes existing user Tags.

- [ ] **Step 2: Implement Tag service and refactor Notes Tag endpoints without changing their contract**

Use `flush()` when creating a Tag ID; service does not commit.

- [ ] **Step 3: Write failing Drive Tag tests**

Drive uses `entity_type="drive_document"`; replacing Drive Tags cannot mutate Note Tags; user isolation applies.

- [ ] **Step 4: Implement Drive Tag endpoints/UI rendering/editing**

Project related-document rows and Drive cards render the shared Tag vocabulary.

- [ ] **Step 5: Verify GREEN**

```bash
cd backend && pytest -q tests/test_tag_service.py tests/test_drive_tags.py tests/test_notes.py
cd .. && flutter test test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/tag_service.py backend/app/api/notes.py backend/app/api/drive.py backend/tests/test_tag_service.py backend/tests/test_drive_tags.py backend/tests/test_notes.py lib/web/drive_api.dart lib/web/drive_page.dart lib/web/projects_page.dart test/drive_page_test.dart test/projects_page_test.dart
git commit -m "feat: share tags with drive documents"
```

### Task 7: Provider-agnostic AI enrichment, cache, and Note suggestions

**Files:**
- Create: `backend/app/services/ai_enrichment.py`, `backend/app/services/drive_enrichment.py`
- Modify: `backend/app/config.py`, `backend/.env.example`, `backend/app/models/drive_schemas.py`, `backend/app/api/drive.py`
- Test: `backend/tests/test_drive_enrichment.py`, regression `backend/tests/test_project_drive_documents.py`, `backend/tests/test_drive_tags.py`

**Interfaces:**
- Provider protocol:
  - `suggest_tags(context) -> list[TagSuggestion]`
  - `rank_related_notes(context, candidates) -> list[RelatedNoteSuggestion]`
- Adapters: `DisabledAiEnrichmentProvider`, `OpenAIResponsesEnrichmentProvider`.
- Config: `AI_ENRICHMENT_PROVIDER=disabled|openai` default `disabled`; `AI_ENRICHMENT_MODEL` required only for OpenAI; `OPENAI_API_KEY` required only for OpenAI; configurable base URL.
- Fixed v1 bounds: candidate cap 20; max displayed setting 1..20/default 5; document context max 12,000 chars; candidate Note snippet max 800 chars; Tag auto-apply threshold 0.80; related-Note suggestion threshold 0.60.
- Endpoints: run/read enrichment; list suggestions; accept/reject suggestion.

- [ ] **Step 1: Write failing privacy/settings tests**

When content consent is OFF or provider is disabled, no model call occurs. Provider request may include only required document title/MIME/bounded extracted text, relevant Project context, existing Tag vocabulary, and bounded candidate Note fields. It must not include OAuth tokens, Drive permission lists, unrelated Notes/Projects, or DB dumps.

- [ ] **Step 2: Write failing deterministic retrieval/fingerprint tests**

Candidates use same Project/shared Tags/Note FTS/keyword overlap, de-duplicate, cap at 20. Fingerprint changes with analyzed content/provider modified metadata, relevant settings/model contract, Tag vocabulary input, and candidate identity/update timestamps. Matching successful fingerprint reuses results; explicit reanalyze bypasses reuse.

- [ ] **Step 3: Write failing provider/partial-success tests**

Mock OpenAI Responses API with strict structured output. No model name is hardcoded. Only Tag suggestions >=0.80 auto-apply additively. Related Note suggestions <0.60 are discarded. Provider timeout/failure creates `partial|failed` enrichment evidence but leaves already-committed Project relationships intact.

- [ ] **Step 4: Write failing suggestion-decision tests**

Pending is non-authoritative. Accept idempotently ensures `related/ai_accepted`; reject creates none. Contradictory decision after final decision -> `409`. Cross-user access fails.

- [ ] **Step 5: Implement provider and orchestration**

Use two narrow model calls (Tags and rerank), no agent/tool loop. Persist fingerprint/provider/model/status/suggestions and short reasons only, not a full source-content duplicate.

- [ ] **Step 6: Integrate enrichment after Project attachment commit**

Core relation commits first. Enrichment executes in a guarded second phase only when enabled/consented. API/UI can report core `PASS` plus enrichment `SKIPPED/PARTIAL/FAIL` separately.

- [ ] **Step 7: Verify GREEN**

```bash
cd backend
pytest -q tests/test_drive_enrichment.py tests/test_project_drive_documents.py tests/test_drive_tags.py
```

Expected: PASS with zero real model calls.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/ai_enrichment.py backend/app/services/drive_enrichment.py backend/app/config.py backend/.env.example backend/app/models/drive_schemas.py backend/app/api/drive.py backend/tests/test_drive_enrichment.py backend/tests/test_project_drive_documents.py backend/tests/test_drive_tags.py
git commit -m "feat: add drive knowledge enrichment"
```

### Task 8: Intelligent-organization review UI

**Files:**
- Modify: `lib/web/drive_api.dart`, `lib/web/drive_settings_page.dart`, `lib/web/drive_page.dart`, `lib/web/projects_page.dart`, `lib/web/notes_page.dart`, `lib/web/api_client.dart`
- Modify: `test/drive_settings_page_test.dart`, `test/drive_page_test.dart`, `test/projects_page_test.dart`, `test/notes_page_test.dart`

**Interfaces:**
- DriveApi: run/read enrichment, list suggestions, decide suggestion, manual related-Note link.

- [ ] **Step 1: Write failing consent/settings tests**

If automatic Tag/suggestion switches are ON but content consent is OFF, first AI attempt explains the consent choice: enable content analysis or continue core operation without AI. No model request occurs before consent. Settings expose automatic Tags, Note suggestions, content-analysis consent, max suggestions default 5, reanalyze/status.

- [ ] **Step 2: Write failing suggestion review tests**

Show at most configured suggestions with Note title/confidence/reason. `接受` creates the authoritative relationship; `略過/拒絕` does not. No automatic-accept control exists.

- [ ] **Step 3: Write failing manual fallback and partial-status tests**

With AI disabled, users can still edit Tags and manually relate a Note. Project attach with AI failure still renders the document and a separate `智能整理未完成` state.

- [ ] **Step 4: Implement dialogs/status/UI**

Accepted AI links and manual links use the same authoritative relation display; origin remains metadata. Core success and enrichment status are visually separate.

- [ ] **Step 5: Verify GREEN/full Flutter suite**

```bash
flutter test
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add lib/web/drive_api.dart lib/web/drive_settings_page.dart lib/web/drive_page.dart lib/web/projects_page.dart lib/web/notes_page.dart lib/web/api_client.dart test/drive_settings_page_test.dart test/drive_page_test.dart test/projects_page_test.dart test/notes_page_test.dart
git commit -m "feat: add drive intelligent organization ui"
```

### Task 9: CI, deployment, production-like acceptance, and checkpoint

**Files:**
- Create: `.github/scripts/verify_drive_knowledge_production.mjs`
- Create: `.github/workflows/drive-knowledge-runtime-acceptance.yml`
- Modify: `.github/workflows/ci.yml` only if broad current test jobs do not already cover the new suites.
- Modify: `.github/workflows/deploy-cloud-run.yml` for non-destructive new Picker/AI runtime config only.
- Modify: `.github/workflows/deploy-firebase-hosting.yml` only if Web build/script handling requires it.
- Create: `backend/tests/test_drive_runtime_acceptance.py` if existing workflow style uses a Python runtime probe.
- Update long-lived `life_assistantGPT` checkpoint only after runtime evidence exists.

**Interfaces:**
- Production-like acceptance uses a deliberately Picker-selected test file; it never scans whole Drive.
- Completion matrix remains Implementation / Tests / CI / Deployment / Runtime / Integration.

- [ ] **Step 1: Run full local/static suites before workflow edits**

```bash
cd backend && pytest -q
cd .. && flutter test
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Expected: PASS.

- [ ] **Step 2: Add CI/runtime acceptance**

Acceptance proves: authenticated workspace/settings; browser Picker config contains no token; Picker-selected file can be registered/read by backend; one file links to multiple Projects; detach does not delete provider file; readable file imports once to independent Note; source link returns to Drive; Tags work; AI suggestions remain pending until acceptance; AI failure does not rollback core link. Runtime workflow records live AI provider as `NOT VERIFIED` when provider is disabled or credentials/model are absent.

- [ ] **Step 3: Wire deployment configuration safely**

Cloud/Web config supplies public Web OAuth client ID, Picker API key, and app ID/project number. The Picker API key must be Google API/referrer restricted and is never treated as a substitute for OAuth. No client secret or backend token is compiled into the Web app. AI stays `disabled` unless an approved provider configuration exists; do not rotate/add production secrets without the required explicit confirmation.

- [ ] **Step 4: Commit acceptance/deployment wiring**

```bash
git add .github/scripts/verify_drive_knowledge_production.mjs .github/workflows/drive-knowledge-runtime-acceptance.yml .github/workflows/ci.yml .github/workflows/deploy-cloud-run.yml .github/workflows/deploy-firebase-hosting.yml backend/tests/test_drive_runtime_acceptance.py
git commit -m "test: add drive knowledge production acceptance"
```

- [ ] **Step 5: Follow main -> Actions -> deployment and verify exact SHA**

Record CI run IDs, Cloud Run/Firebase deployment runs/revisions, migration evidence, and deployed commit SHA. CI green alone is not completion.

- [ ] **Step 6: Execute authenticated runtime/integration acceptance**

Use a real explicitly selected test file. If browser Picker selects an account/file the backend server-side Drive token cannot read, report Integration FAIL and fix within the `drive.file` least-privilege design; do not broaden scope to `drive.readonly` as a workaround.

- [ ] **Step 7: Record completion matrix and Drive checkpoint**

```text
Implementation: PASS / FAIL / NOT VERIFIED
Tests:          PASS / FAIL / NOT VERIFIED
CI:             PASS / FAIL / NOT VERIFIED
Deployment:     PASS / FAIL / NOT VERIFIED
Runtime:        PASS / FAIL / NOT VERIFIED
Integration:    PASS / FAIL / NOT VERIFIED
Overall:        DONE / PARTIAL
```

Update the allowed `life_assistantGPT` long-lived progress/checkpoint with exact commit SHA, workflow IDs, deployment revisions, evidence, known limitations, and any GitHub-vs-Drive differences. Documentation completion never upgrades an unverified runtime layer.
