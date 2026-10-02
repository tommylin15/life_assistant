# Task 8 — Intelligent Organization Review UI Design

**Date:** 2026-10-02  
**Status:** implementation design derived from already-approved Drive Project Knowledge product decisions  
**Current package:** #4 / 11  
**Target checkpoint:** #4 DONE -> 4 / 11 = 36.4%

## Goal

Expose the Task 7 provider-agnostic Drive AI enrichment foundation as a safe, reviewable Flutter Web workflow. Users must be able to see enrichment status, review suggested related Notes, explicitly accept or reject those suggestions, control content-analysis consent, and retry analysis without making AI availability a dependency of core Drive/Project behavior.

## Source contracts

This design does not reopen product decisions from `docs/superpowers/specs/2026-09-30-drive-project-knowledge-integration-design.md`. It narrows the current package to the UI closure required by `doc/progress.md`.

Backend contract already present on `main`:

- `GET /api/v1/drive/documents`
- `GET /api/v1/drive/enrichment/settings`
- `PUT /api/v1/drive/enrichment/settings`
- `GET /api/v1/drive/documents/{document_id}/enrichment`
- `POST /api/v1/drive/documents/{document_id}/enrichment`
- `POST /api/v1/drive/note-suggestions/{suggestion_id}/decision`

The UI must preserve Task 7 semantics: provider-agnostic, explicit content consent, bounded Note suggestions, accept/reject authority, stable cache visibility, and partial-success/non-blocking behavior.

## Scope

### In scope

1. Add a Drive-specific Flutter API facade instead of coupling widgets directly to HTTP details.
2. Add `/more/drive` as the intelligent-organization review surface.
3. Add `/more/drive/settings` for AI settings and explicit content-analysis consent.
4. Show registered Drive documents and each document's latest enrichment result.
5. Show suggested Tags as informational output; do not imply user acceptance is required for auto-tag behavior already defined by settings.
6. Show related-Note suggestions with enough Note identity to support a meaningful decision, including Note title lookup from the existing Notes API.
7. Accept or reject pending suggestions explicitly and refresh the visible result after the decision.
8. Allow manual re-analysis with `force=true`.
9. Render `succeeded`, `partial`, `failed`, and `skipped` as distinct user-readable states.
10. If content consent is OFF or AI is unavailable, explain that core Drive/Project functionality remains usable and offer a settings/manual path instead of presenting a core-feature failure.
11. Use the approved Warm Knowledge shared components and responsive contract.
12. Add a `Google Drive` entry under More and keep provider/model vendor identity out of the Flutter domain contract.

### Out of scope for Task 8

- Google Picker / GIS token bridge.
- Workspace CRUD UI.
- Drive file registration UI.
- Drive -> Note import UI.
- Project attachment UI expansion.
- New external AI provider credentials or vendor-specific UI.
- Provider-file mutation (rename/move/delete).
- Task 9 production integration closure.

Those remain separate work. Their absence must not be hidden by calling Task 8 a full Drive File Manager delivery.

## UX architecture

### `/more/drive`

The page uses `AppPageFrame`, `AppSectionCard`, `AppStatusChip`, and `AppStatePanel`.

Top section:

- Title: `Google Drive 智能整理`
- concise provider-neutral explanation
- `智能整理設定` action
- a consent banner when document-content analysis is disabled

Document section:

- document name and MIME-derived secondary text
- latest enrichment status chip
- last-run cache indicator when applicable
- suggested Tag chips
- related-Note suggestion cards
- `重新分析` action

Suggestion cards show Note title when it can be resolved from the existing Notes list, otherwise a stable fallback using the Note ID. Each pending suggestion exposes `接受` and `拒絕`; decided suggestions are read-only and display their decision.

The page loads document metadata first. Enrichment lookup failures are isolated per document so a provider/AI failure cannot make the whole Drive document list disappear.

### `/more/drive/settings`

Settings expose:

- `自動套用建議標籤`
- `建議相關筆記`
- `允許將文件內容送交 AI 分析`
- maximum related-Note suggestions, constrained to backend contract `1..20`

The consent setting must include clear text that document content may be sent to the configured AI analysis provider. It defaults to OFF according to the backend contract.

Saving sends only the current settings fields. Failure leaves the form state visible and reports the error without silently assuming persistence.

## State semantics

- `succeeded`: analysis completed.
- `partial`: some enrichment stages failed; successful results remain valid.
- `failed`: enrichment failed; Drive/Project core state is not rolled back.
- `skipped`: analysis intentionally did not run, including disabled/unavailable/consent-gated conditions.
- no run: `尚未分析`.

Provider and model fields may exist in the backend response for audit/cache purposes but are not rendered or required by Flutter business logic.

## Manual fallback

When AI cannot run, the UI must not dead-end. It keeps the registered document visible, preserves links to existing Notes/Drive surfaces, and explains that intelligent organization is optional. This package does not invent new manual relationship APIs; it routes users to existing Notes/Drive management surfaces and preserves existing relationships.

## Error handling

- document-list failure -> page-level error with retry.
- settings load/save failure -> settings-level error with retry/save available.
- per-document enrichment read/run failure -> document-level status/message; other documents remain usable.
- suggestion decision failure -> keep the suggestion pending and surface the error.
- no fabricated success state after any failed mutation.

## Verification / DONE gate

Task 8 may be marked DONE only when all applicable evidence is present:

- implementation PASS
- focused Flutter widget/unit tests PASS
- full Flutter test suite PASS
- `flutter analyze --no-fatal-infos` PASS
- Flutter Web build PASS
- GitHub CI PASS
- Firebase deployment PASS
- browser production acceptance PASS for navigation, consent/status rendering, and review controls
- compact/mobile viewport acceptance PASS

Task 8 does not require true external-provider credentials; disabled/unavailable mode remains a supported provider-agnostic state. True Drive/external-AI integration evidence remains Task 9.
