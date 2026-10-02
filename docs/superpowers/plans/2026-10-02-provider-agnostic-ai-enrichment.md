# Provider-Agnostic AI Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Task 7 as a backend foundation for provider-agnostic Drive-document AI enrichment with explicit consent, reusable cache fingerprints, additive Tags, bounded related-Note suggestions, auditable decisions, and non-blocking provider failure semantics.

**Architecture:** Keep Drive core operations independent from AI. Add persistence for user enrichment settings, enrichment runs, and Note-link suggestions; place provider-specific behavior behind an async provider protocol; orchestrate enrichment in a Drive-domain service that can be exercised with fake providers and defaults to a disabled provider until a concrete adapter is configured. Expose only backend API contracts needed by Task 8 review UI and Task 9 production delivery.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2 async, PostgreSQL, Alembic, unittest/pytest-compatible CI.

**Spec:** `docs/superpowers/specs/2026-09-30-drive-project-knowledge-integration-design.md`

## Global Constraints

- AI enrichment is optional and non-blocking; core Drive/Project success is never rolled back because enrichment fails.
- Provider/model choice must stay behind an adapter and deployment configuration.
- `Allow document content to be sent for AI analysis` is explicit persisted consent and defaults OFF.
- When consent is OFF, AI Tag generation and Note recommendations do not run.
- Never send or persist Google OAuth tokens, Drive permission lists, unrelated Notes/Projects, whole-Drive listings, PostgreSQL dumps, or duplicate raw source content in enrichment audit rows.
- Tags are additive: AI may add useful Tags but never delete existing user Tags because a later run omits them.
- Related Notes are suggestions only; only explicit acceptance creates an authoritative `note_drive_documents` row with `link_source = ai_accepted`.
- Cache reuse applies only to a successful run with the same stable content/context fingerprint; explicit reanalysis may bypass reuse.
- Candidate Notes are bounded before provider invocation; default displayed suggestions remain 5.
- This package is backend foundation only. Review UI belongs to Task 8.

## Review Focus

- Consent OFF must make zero provider calls and yield an auditable skipped outcome.
- One provider stage failing after the other succeeds must produce `partial`, preserve the successful output, and not raise a core-operation error.
- Fingerprints must be deterministic for equivalent ordered/unordered context and change when relevant content/settings change.
- Acceptance/rejection decisions must be idempotent and acceptance alone creates the authoritative Drive↔Note relation.
- AI-generated Tags must reuse existing case-insensitive Tag vocabulary and never delete pre-existing Drive-document Tags.

---

### Task 1: Lock the RED contract

**Files:**
- Create: `backend/tests/test_drive_ai_enrichment.py`

**Interfaces:**
- Consumes: current Drive models/routes and existing `Tag` / `EntityTag` / `NoteDriveDocument` contracts.
- Produces: failing tests defining model, schema, provider, fingerprint, partial-failure, consent, and route expectations.

- [ ] Write the contract tests.
- [ ] Push the test-only commit to `main` and verify CI fails for the expected missing enrichment symbols/routes.

### Task 2: Add enrichment persistence and consent settings

**Files:**
- Create: `backend/alembic/versions/20261002_0009_drive_ai_enrichment.py`
- Modify: `backend/app/models/drive.py`
- Modify: `backend/app/models/drive_schemas.py`

**Interfaces:**
- Produces: `DriveEnrichmentSettings`, `DriveDocumentEnrichmentRun`, `DriveNoteLinkSuggestion`, plus settings/run/suggestion API schemas.

- [ ] Implement settings with defaults `auto_tags_enabled=true`, `note_suggestions_enabled=true`, `allow_document_content=false`, `max_related_note_suggestions=5`.
- [ ] Implement run statuses `succeeded | partial | failed | skipped` and suggestion decisions `pending | accepted | rejected` with DB checks.
- [ ] Add versioned migration after `20261001_0008` without rewriting prior migrations.

### Task 3: Add the provider-agnostic domain contract

**Files:**
- Create: `backend/app/services/ai_enrichment_provider.py`

**Interfaces:**
- Produces: `AIEnrichmentProvider`, `DocumentEnrichmentContext`, `RelatedNoteCandidate`, `TagSuggestion`, `RelatedNoteSuggestion`, `AIProviderError`, `UnavailableAIEnrichmentProvider`, `compute_enrichment_fingerprint()`, `execute_provider_enrichment()`.

- [ ] Implement two async provider methods: `suggest_tags(document_context)` and `rank_related_notes(document_context, candidate_notes)`.
- [ ] Keep provider metadata structured and ensure errors carry stable non-secret error codes.
- [ ] Implement deterministic SHA-256 fingerprinting over the exact bounded enrichment context and relevant settings/contract version.
- [ ] Implement stage-independent execution so one stage may succeed while the other fails, producing `partial`; disabled stages produce `skipped` only when neither stage runs.

### Task 4: Add Drive enrichment orchestration and API contracts

**Files:**
- Create: `backend/app/services/drive_enrichment.py`
- Modify: `backend/app/api/drive.py`

**Interfaces:**
- Produces API routes:
  - `GET /api/v1/drive/enrichment/settings`
  - `PUT /api/v1/drive/enrichment/settings`
  - `POST /api/v1/drive/documents/{document_id}/enrichment`
  - `GET /api/v1/drive/documents/{document_id}/enrichment`
  - `POST /api/v1/drive/note-suggestions/{suggestion_id}/decision`

- [ ] Persist/read consent settings by authenticated `user_sub`.
- [ ] Build bounded candidate Notes from same Project/shared Tags and deterministic keyword overlap, capped before provider invocation.
- [ ] Reuse existing generic `Tag` / `EntityTag(entity_type='drive_document')`; add AI Tags only.
- [ ] Reuse a prior successful matching fingerprint unless `force=true`.
- [ ] Persist non-authoritative suggestions and audit status without storing raw source content.
- [ ] Make suggestion decision idempotent; accepted creates/ensures `NoteDriveDocument(relation_type='related', link_source='ai_accepted')`, rejected does not.
- [ ] Return enrichment failure/partial/skipped as a normal structured enrichment outcome, not as rollback of a successful core Drive relation.

### Task 5: GREEN verification and delivery evidence

**Files:**
- Modify only if verification exposes defects.

- [ ] Push the minimal implementation commit to `main`.
- [ ] Verify backend test job and full CI GREEN.
- [ ] Verify Alembic/deployment workflow applies the migration successfully.
- [ ] Verify Cloud Run health/readiness and authenticated enrichment settings/runtime contract where available.
- [ ] Record implementation/tests/CI/deployment/runtime/integration as PASS/FAIL/NOT VERIFIED; do not mark package DONE unless the evidence required by Task 7 is complete.
