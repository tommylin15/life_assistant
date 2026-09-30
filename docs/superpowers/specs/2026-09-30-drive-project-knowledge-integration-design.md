# Drive File Manager + Project Knowledge Integration Design

Status: **Written spec pending user review**  
Date: 2026-09-30  
Repository: `tommylin15/life_assistant`  
Target branch: `main`

## 1. Purpose

Add a Google Drive workspace experience to `life_assistant` that lets the user deliberately select Drive content, reuse it inside Projects, convert selected files into independent Notes, and connect Drive documents to the existing Notes knowledge model without granting broad all-Drive access.

The feature must preserve these principles:

- Google Drive remains the source of truth for the original Drive file.
- `life_assistant` PostgreSQL is the source of truth for app-owned metadata, Project relationships, Tags, Note imports, AI suggestions, and user decisions.
- AI enrichment is optional enhancement, never a prerequisite for the core Drive/Project flow.
- Removing a Drive workspace, document registration, Project relationship, Tag, or Note relationship must not delete the original Google Drive file.
- The first version keeps least-privilege Google Drive authorization using `drive.file` and Google Picker rather than requesting whole-Drive read access.

## 2. Current-State Constraints

The current Web application already has:

- Google OAuth integration with Drive using `https://www.googleapis.com/auth/drive.file`.
- A Google integrations page and Drive Bridge compatibility action.
- Projects and Project UI.
- Notes with Markdown editing, full-text search, one optional `project_id`, Tags through the generic `tags` / `entity_tags` model, and Note-to-Note bidirectional link behavior.
- FastAPI + PostgreSQL + Alembic as the current cloud backend/data path.

The current application does **not** have:

- A Web Drive file manager.
- Configurable Drive workspaces.
- A registry of user-selected Drive documents.
- Project-to-Drive-document relationships.
- Drive-document-to-Note relationships.
- A production AI/LLM enrichment service.

## 3. Approved Product Decisions

The following decisions are fixed for v1:

1. **Drive access model: hybrid least-privilege.**
   - Keep `drive.file`.
   - Use Google Picker as the explicit selection/grant boundary.
   - Do not request `drive.readonly` in v1.

2. **Multiple Drive workspaces are supported.**
   - The user can configure multiple workspace folders.
   - Each workspace can be enabled/disabled and removed independently.
   - One workspace may be marked as the default.

3. **Workspace folder semantics are logical, not recursive authorization.**
   - Selecting/configuring a folder does not imply that `drive.file` grants automatic recursive access to every existing child file.
   - Files become managed Drive documents only after the user explicitly selects/grants them through Picker.
   - The UI must never imply that life_assistant can silently enumerate ungranted files in a configured folder.

4. **Drive -> Notes uses one-time import.**
   - Import the currently readable document text into a new Note snapshot.
   - Preserve a relationship back to the original Drive document.
   - Subsequent Note edits do not change Drive.
   - Subsequent Drive edits do not automatically overwrite the Note.
   - Automatic or bidirectional synchronization is out of scope for v1.

5. **Drive document -> Project is many-to-many.**
   - One Drive document may be related to multiple Projects.
   - One Project may have multiple Drive documents.

6. **Intelligent organization mode B.**
   - Tags: automatically generated/applied when AI enrichment is enabled.
   - Related Notes: AI proposes candidate relationships; the user must accept them before a relationship becomes authoritative.
   - No automatic high-confidence Note linking in v1.

7. **AI is provider-agnostic and non-blocking.**
   - No model provider is hard-coded into Drive domain logic.
   - If AI is disabled, unavailable, times out, or fails, the document/Project operation still succeeds.

## 4. Scope

### 4.1 In scope

- Drive workspace settings.
- Multiple logical workspaces.
- Google Picker-based document selection.
- Registry/list of selected Drive documents.
- Open original Drive document.
- Attach/detach selected Drive document to/from one or more Projects.
- Convert selected Drive document to a one-time Note snapshot.
- Preserve Note <-> Drive source/reference relationships.
- Reuse existing generic Tag system for Drive documents.
- AI-generated Drive-document Tags.
- AI-recommended Drive-document <-> Note relationships with user confirmation.
- Project UI section for related Drive documents.
- Note UI section for source/related Drive documents.
- Drive settings for AI organization behavior.
- Auditable AI enrichment status and recommendation decisions.
- Unit/API/widget/integration/runtime acceptance for the new flow.

### 4.2 Out of scope for v1

- Whole-Drive browsing via `drive.readonly`.
- Recursive background indexing of all files inside a configured Drive folder.
- Rename/move/delete of the original Google Drive file from life_assistant.
- Automatic two-way Note/Drive synchronization.
- Automatic refresh/overwrite of imported Notes.
- Automatic creation of Note links without user confirmation.
- Generic cross-system Agent orchestration.
- LangGraph/omniAgent dependency for this application-local enrichment feature.
- Replacing the existing Drive Bridge compatibility/fallback path unless separately approved.

## 5. Architecture

### 5.1 Component boundaries

#### Drive Workspace Service

Responsibilities:

- Store configured workspace folder references and user-facing names.
- Track enabled/default state.
- Never infer recursive file authorization from folder configuration.

Depends on:

- PostgreSQL.
- Authenticated application context.

#### Google Drive Selection/Read Adapter

Responsibilities:

- Integrate Google Picker in Web UI.
- Accept explicitly selected/granted Drive file IDs.
- Fetch allowed metadata and readable content through the existing Google OAuth integration.
- Return provider errors in a stable application-level error contract.

Depends on:

- Existing Google OAuth token storage/refresh behavior.
- `drive.file` scope.
- Google Drive APIs.

#### Drive Document Registry

Responsibilities:

- Persist metadata for explicitly selected Drive files.
- Deduplicate the same Google Drive file by stable provider file ID.
- Preserve `webViewLink`/equivalent original-open URL returned by Google.
- Never treat copied content as the source of truth for the original file.

Depends on:

- PostgreSQL.
- Google Drive Selection/Read Adapter.

#### Project Document Relationship Service

Responsibilities:

- Create and remove Project <-> Drive-document relationships.
- Keep relationship operations idempotent.
- Removing a relationship must not mutate the original Drive file.

#### Note Import/Relationship Service

Responsibilities:

- Create a one-time Note snapshot from readable Drive content.
- Record `source_import` relationship to the original Drive document.
- Support additional accepted/manual Drive-document <-> Note relationships.
- Do not reuse `NoteLink` for cross-entity relationships; `NoteLink` remains Note-to-Note.

#### AI Enrichment Service

Responsibilities:

- `suggest_tags(document_context)`
- `rank_related_notes(document_context, candidate_notes)`
- Return structured suggestions, confidence, short rationale, provider/model metadata, and status.

Constraints:

- Provider/model choice is behind an adapter and deployment configuration.
- No OAuth tokens, Drive permission objects, unrelated Notes, or whole-Drive context may be sent to the model.
- AI output never directly deletes or overwrites user-owned relationships/tags.
- Provider absence is a supported degraded mode; core Drive features continue to work.

This is an application-local enrichment service. It is not an Agent runtime and does not move cross-system reasoning responsibilities from omniAgent into life_assistant.

## 6. Data Model

Names below are the recommended v1 schema and should be used unless implementation evidence requires a narrowly justified adjustment in the implementation plan.

### 6.1 `drive_workspaces`

- `id` UUID/string PK
- `google_folder_id` string, required
- `name` text, required
- `web_view_link` text, nullable
- `is_enabled` boolean, default true
- `is_default` boolean, default false
- `created_at`
- `updated_at`

Constraints:

- A configured folder should not be duplicated under the same effective application account.
- At most one active workspace is default.
- Removing a workspace is an app metadata operation only.

### 6.2 `drive_documents`

- `id` UUID/string PK
- `google_file_id` string, required, unique for the effective application account
- `name` text, required
- `mime_type` string, required
- `web_view_link` text, required when Google supplies it
- `provider_modified_at` datetime, nullable
- `last_metadata_refresh_at` datetime, nullable
- `created_at`
- `updated_at`

The table stores provider identity and cached metadata, not the authoritative file contents.

### 6.3 `drive_workspace_documents`

- `workspace_id` FK -> `drive_workspaces.id`
- `drive_document_id` FK -> `drive_documents.id`
- `created_at`

Primary/unique key: `(workspace_id, drive_document_id)`.

A Drive document may appear in more than one logical life_assistant workspace without duplicating the provider file record.

### 6.4 `project_drive_documents`

- `project_id` FK -> `projects.id`
- `drive_document_id` FK -> `drive_documents.id`
- `created_at`

Primary/unique key: `(project_id, drive_document_id)`.

### 6.5 `note_drive_documents`

- `note_id` FK -> `notes.id`
- `drive_document_id` FK -> `drive_documents.id`
- `relation_type` enum/string: `source_import | related`
- `relation_origin` enum/string: `manual | ai_accepted | import`
- `created_at`

Unique key should prevent duplicate equivalent relationships.

This table provides bidirectional UI discoverability between Notes and Drive documents without changing the semantics of the existing Note-to-Note `NoteLink` model.

### 6.6 Tags

Reuse existing `tags` + `entity_tags`.

For Drive documents:

- `entity_type = "drive_document"`
- `entity_id = drive_documents.id`

No second Drive-only Tag system should be created.

### 6.7 `drive_document_enrichment_runs`

- `id` UUID/string PK
- `drive_document_id` FK
- `content_fingerprint` string, required
- `provider` string, nullable when unavailable before invocation
- `model` string, nullable when unavailable before invocation
- `status` enum/string: `succeeded | partial | failed | skipped`
- `suggested_tags_json` JSON/text, non-authoritative audit payload
- `error_code` string, nullable
- `created_at`

Do not persist raw OAuth tokens or a full duplicate of source document contents in the enrichment audit table.

### 6.8 `drive_note_link_suggestions`

- `id` UUID/string PK
- `enrichment_run_id` FK
- `drive_document_id` FK
- `note_id` FK
- `confidence` numeric
- `reason` text
- `decision` enum/string: `pending | accepted | rejected`
- `decided_at` datetime, nullable
- `created_at`

Acceptance creates/ensures the authoritative `note_drive_documents` row with `relation_origin = ai_accepted`. Rejection does not create a relationship.

## 7. Core User Flows

### 7.1 Configure Drive workspace

1. User opens `More -> Google Drive -> Settings`.
2. User adds a workspace folder through the supported Google selection surface.
3. life_assistant stores the logical workspace reference.
4. UI clearly states that files must still be explicitly selected to become managed documents.
5. User can enable/disable, set default, or remove the workspace later.

Removing a workspace must not delete Drive files. Documents that are still related through another workspace, Project, Note, or other app relationship remain registered as needed.

### 7.2 Add documents to a workspace

1. User opens a workspace and selects `Add Drive files`.
2. Google Picker opens.
3. User explicitly selects/grants one or more files.
4. Backend upserts `drive_documents` by Google file ID.
5. Backend creates/ensures `drive_workspace_documents` relationships.
6. The documents appear in the life_assistant selected-document list.

### 7.3 Add Drive document to Projects

1. User selects `Add to Project` on a Drive document.
2. User selects one or more Projects.
3. Backend idempotently creates `project_drive_documents` rows.
4. Core operation is considered successful at this point.
5. If AI enrichment is enabled, the enrichment flow runs.
6. Auto-generated Tags are applied.
7. Related Note suggestions are displayed for explicit acceptance/rejection.

AI failure after step 3 produces partial enrichment, not Project-attachment failure.

### 7.4 Convert Drive document to Note

1. User selects `Convert to Note`.
2. App reads the currently accessible text representation.
3. User may choose a Project and edit title/Tags before saving.
4. App creates a normal Note using the existing Notes domain/API semantics.
5. App creates `note_drive_documents` with `relation_type = source_import`, `relation_origin = import`.
6. The Note is thereafter independent content.
7. Note UI shows `Open original Drive file` and source metadata.

If text extraction is unsupported for a file type, do not fabricate content. The UI must explain that the file can still be related/opened but cannot be converted to a text Note through the current extractor.

### 7.5 Accept intelligent Note relationships

1. Candidate retrieval finds a bounded Note set using deterministic application data.
2. AI reranks/explains candidates.
3. UI displays at most the configured number of suggestions; v1 default is 5.
4. User accepts or rejects each suggestion.
5. Acceptance creates/ensures `note_drive_documents(relation_type=related, relation_origin=ai_accepted)`.
6. Rejection is recorded and creates no authoritative relationship.

## 8. AI Enrichment Rules

### 8.1 Tag generation

Default when enabled:

- Generate approximately 3-8 useful Tags.
- Prefer existing Tags over creating near-duplicate synonyms.
- Use document title, MIME type, selected Project context, readable document text, and existing Tag vocabulary.
- Automatically apply the resulting high-confidence Tag set.
- User may subsequently add/remove Tags manually.
- AI must never delete unrelated existing user Tags merely because a later run omits them.

### 8.2 Related Note retrieval and reranking

Do not send every Note to the model.

Stage 1: deterministic candidate retrieval using some combination of:

- same Project,
- shared Tags,
- Note title/body full-text search,
- keyword overlap,
- future semantic index if separately introduced.

Target candidate set: about 10-20 Notes.

Stage 2: model reranking:

- Determine whether the relationship is meaningful rather than a coincidental keyword match.
- Return confidence and a short user-visible reason.
- Return no more than the configured display limit; default 5.

### 8.3 Caching

Compute a stable content/context fingerprint from the content actually used for enrichment plus relevant settings/model contract inputs.

If the fingerprint has not changed and a reusable successful result exists, do not make an unnecessary repeat model call.

A user-requested `Reanalyze` action may intentionally bypass reuse when the implementation contract explicitly marks it as a fresh run.

## 9. AI Privacy and Cost Controls

Only send analysis-needed context such as:

- document title,
- MIME type,
- necessary extracted text,
- selected Project name/summary when relevant,
- bounded candidate Note titles/snippets,
- existing Tag vocabulary needed for normalization.

Never send:

- Google OAuth access/refresh tokens,
- Drive permission lists unless a future approved use case explicitly requires them,
- unrelated Notes,
- unrelated Projects,
- whole-Drive listings,
- raw PostgreSQL dumps.

The system must expose an explicit setting:

- `Allow document content to be sent for AI analysis`

When disabled:

- Drive selection works.
- Project relationships work.
- Original-file opening works.
- Manual Tags work.
- Manual Note relationships work.
- AI Tag generation and AI Note recommendations do not run.

Provider/model is deployment-configurable behind the AI Enrichment Service adapter. The Drive domain must not contain provider-specific request code.

## 10. UI Design

### 10.1 Navigation

Add a Drive experience under `More`, with a settings entry reachable from the Drive screen.

Recommended route family:

- `/more/drive`
- `/more/drive/settings`

Exact route names may follow existing Web routing conventions during implementation, but the information architecture must remain `More -> Google Drive -> Settings`.

### 10.2 Drive document list

For each selected document show at minimum:

- file type/icon,
- file name,
- known modified time when available,
- workspace context,
- Tags,
- actions: `Open`, `Add to Project`, `Convert to Note`, `More`.

Support filtering/searching across registered selected documents. This search is over life_assistant's registered document metadata; it is not presented as unrestricted whole-Drive search.

### 10.3 Workspace settings

Support:

- add workspace,
- multiple workspace list,
- enable/disable,
- set default,
- remove workspace,
- Google account/authorization status,
- reauthorize Drive,
- explanatory least-privilege text.

### 10.4 Intelligent organization settings

Support:

- `Automatic intelligent Tags`: default ON
- `Suggest related Notes`: default ON
- `Allow document content to be sent for AI analysis`: explicit user-controlled setting
- `Maximum related Note suggestions`: default 5
- `Reanalyze document` action
- last analysis time/status

Do not provide automatic high-confidence Note-link creation in v1.

### 10.5 Project UI

Add `Related documents` section showing:

- file name/type,
- Tags,
- related Note count,
- `Open in Drive`,
- `View related Notes`,
- `Remove from this Project`.

Removing from a Project only removes `project_drive_documents`; it does not delete the Drive file or unrelated relationships.

### 10.6 Note UI

Add `Source / related Drive documents` section showing:

- original/source indicator where `relation_type = source_import`,
- file name/type,
- `Open original Drive file`,
- related/reference status.

## 11. API Surface

Exact request/response schemas belong in the implementation plan, but v1 requires capability-equivalent endpoints for:

- list/create/update/remove Drive workspaces,
- register/upsert Picker-selected Drive documents,
- list/search registered Drive documents,
- refresh Drive document metadata,
- list/add/remove Project <-> Drive-document relationships,
- create Note snapshot from Drive document,
- list/add/remove Note <-> Drive-document relationships,
- list/replace Drive-document Tags using the existing generic Tag domain,
- run/read enrichment status,
- accept/reject Note-link suggestions.

Mutation endpoints must follow existing authorization, execution logging, confirmation, and idempotency conventions where applicable.

No v1 API may expose a life_assistant operation that deletes the original Google Drive file.

## 12. Error and Partial-Success Semantics

### Core operation + AI enrichment

- Project relationship success + AI success -> `PASS` enrichment.
- Project relationship success + some AI substeps fail -> core operation `PASS`, enrichment `PARTIAL`.
- Project relationship success + AI fully fails/unavailable -> core operation `PASS`, enrichment `FAIL` or `SKIPPED` as appropriate.
- Drive access/authorization failure before the requested core Drive read/registration -> core operation `FAIL`.

The UI must not roll back a successful Project relationship because enrichment fails.

### Idempotency

Repeated requests must not create duplicate:

- Drive document records for the same Google file ID,
- workspace-document relationships,
- Project-document relationships,
- Note-document relationships,
- accepted suggestion relationships.

### Provider content changes

The cached Drive metadata may become stale. Opening the original file should prefer the provider link/identity and surface provider errors honestly. Do not silently replace missing/inaccessible provider content with an old Note snapshot and present it as current Drive content.

## 13. Security and Governance

- Keep least privilege: `drive.file` + explicit Picker grants for v1.
- Do not request `drive.readonly` as part of this feature.
- Do not log OAuth tokens or raw sensitive document contents in execution logs.
- Record app-level operations and AI enrichment statuses using existing audit/execution patterns.
- Destructive Google Drive file operations are absent from this feature.
- Existing production secret handling remains authoritative; introducing/configuring a model provider secret must follow the Engineering Governance & Delivery Runbook.
- `life_assistant` owns data/API/UI/execution/integration behavior; this feature must not create a cross-system Agent reasoning loop.

## 14. Testing Strategy

### Backend unit/service tests

Cover:

- workspace CRUD semantics,
- default-workspace uniqueness,
- Drive-document upsert by Google file ID,
- relationship idempotency,
- relationship removal without Drive deletion,
- Tag reuse/normalization,
- one-time Note import semantics,
- unsupported extraction behavior,
- enrichment caching/fingerprint behavior,
- provider disabled/unavailable behavior,
- partial-success behavior,
- accepted/rejected suggestion transitions.

Mock Google and model-provider network boundaries in deterministic tests.

### API tests

Cover:

- authenticated access,
- invalid/missing Drive grants,
- duplicate mutations,
- Project multi-link behavior,
- Note source/related links,
- AI settings and suggestion decisions,
- destructive boundary: no endpoint deletes provider files.

### Flutter/Web widget tests

Cover:

- multi-workspace settings,
- Drive selected-document list/search,
- add-to-Project multi-select flow,
- Convert-to-Note flow,
- Tags rendering/editing,
- Note suggestion acceptance/rejection,
- AI-disabled state,
- partial enrichment status,
- Project related-document section,
- Note source/related-document section.

### Integration/runtime acceptance

A production-like acceptance must verify with an explicitly selected real Drive test file:

1. Drive authorization remains least-privilege.
2. Picker-selected file registers successfully.
3. Original file opens via Google-provided link.
4. One file can attach to multiple Projects.
5. Project detach does not delete the Drive file.
6. Text-capable file converts to an independent Note snapshot.
7. Imported Note opens the original Drive source.
8. Intelligent Tags appear when enabled.
9. Related Notes are suggestions until explicitly accepted.
10. Accepted relationship is visible from both Note and Drive-document views.
11. AI failure does not roll back Project attachment.
12. CI, deployment, runtime, and integration evidence are recorded with `PASS / FAIL / NOT VERIFIED` and overall delivery is not called DONE without required evidence.

## 15. Delivery Order

Recommended implementation slices after the written implementation plan is approved:

1. Data model + migrations + repository/service boundaries.
2. Drive workspaces + selected-document registry APIs.
3. Picker integration + Drive document list/settings UI.
4. Project <-> Drive-document relationships + Project UI.
5. Drive -> Note one-time import + Note source UI.
6. Generic Drive-document Tags.
7. Provider-agnostic AI enrichment service + deterministic candidate retrieval.
8. AI Tag auto-apply + Note suggestion review flow.
9. Full tests, CI, deployment, and runtime/integration acceptance.
10. Update long-lived Drive documentation/checkpoint evidence.

## 16. Acceptance Definition

The feature is functionally complete only when:

- users can configure multiple logical Drive workspaces,
- users can explicitly select files through the least-privilege selection boundary,
- selected files can be opened, related to multiple Projects, and converted to independent Notes where extraction is supported,
- Drive documents share the existing Tag vocabulary,
- intelligent Tags are auto-applied when enabled,
- related Notes are suggested with confidence/reason and require user acceptance,
- Note and Project UIs expose the resulting Drive relationships,
- disabling AI leaves all non-AI core Drive flows usable,
- removing app relationships never deletes the provider file,
- tests/CI/deployment/runtime/integration evidence satisfy the project governance rules.

Until those layers are verified, status must remain `PARTIAL` with each layer reported as `PASS / FAIL / NOT VERIFIED`.
