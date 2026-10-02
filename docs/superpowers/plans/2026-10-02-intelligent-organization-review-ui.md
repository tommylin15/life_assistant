# Task 8 — Intelligent Organization Review UI Implementation Plan

> Execute with `superpowers:executing-plans`; use strict TDD for product code.

**Goal:** Close package #4 by exposing the existing provider-agnostic enrichment backend through a Warm Knowledge Flutter review/settings workflow without expanding into Picker/workspace/import scope.

**Spec:** `docs/superpowers/specs/2026-10-02-intelligent-organization-review-ui-design.md`

## Task 1 — Define the Flutter boundary with RED tests

**Create:**
- `lib/web/drive_api.dart`
- `test/drive_page_test.dart`
- `test/drive_settings_page_test.dart`

**Modify later in GREEN:**
- `lib/web/api_client.dart`

RED tests must pin:

- document list renders independently of enrichment state
- content-consent OFF banner and settings path
- status mapping for no run / succeeded / partial / failed / skipped
- suggested Tags render without vendor identity
- Note suggestions resolve Note titles when available
- accept/reject call the decision endpoint contract and update the visible decision
- re-analysis uses `force=true`
- one document enrichment failure does not hide other documents
- settings defaults/values render and save all four fields
- max suggestions remains within `1..20`
- settings save failure is visible and does not claim success

Run focused tests and verify RED because `DriveApi`, pages, and routes do not yet exist.

## Task 2 — Implement API facade and review/settings pages to GREEN

**Create:**
- `lib/web/drive_api.dart`
- `lib/web/drive_page.dart`
- `lib/web/drive_settings_page.dart`

**Modify:**
- `lib/web/api_client.dart`

`DriveApi` interface:

```dart
Future<List<Map<String, dynamic>>> getDocuments();
Future<Map<String, dynamic>> getEnrichmentSettings();
Future<Map<String, dynamic>> updateEnrichmentSettings(Map<String, dynamic> body);
Future<Map<String, dynamic>?> getEnrichment(String documentId);
Future<Map<String, dynamic>> runEnrichment(String documentId, {bool force = false});
Future<Map<String, dynamic>> decideNoteSuggestion(String suggestionId, String decision);
```

Use `noteApiProvider.getNotes()` only for display identity; do not change the backend enrichment schema merely to add UI-only Note titles.

Implement the minimum code required for focused tests to pass. Provider/model values from backend responses must not appear in visible UI or be required to make UI decisions.

## Task 3 — Wire navigation under More with RED -> GREEN coverage

**Modify:**
- `lib/web/web_app.dart`
- `test/web_app_shell_test.dart` or add a focused route test if authentication routing makes that separation clearer.

Add:

- `/more/drive`
- `/more/drive/settings`
- More entry `Google Drive`

Keep App Shell top-level destinations unchanged; Drive remains under More.

## Task 4 — Full local/CI-quality verification

Run through CI-equivalent checks:

```bash
flutter test
flutter analyze --no-fatal-infos
flutter build web --target=lib/main_web.dart
```

Because this execution environment cannot clone `github.com`, use GitHub Actions as the authoritative executable environment. The RED commit is safe because Firebase and Cloud Run deploy only after successful CI `workflow_run`.

## Task 5 — Production acceptance

After GREEN commit reaches `main`:

- verify CI success for exact release SHA
- verify Firebase Hosting deployment success for the same release SHA
- verify Cloud Run remains GREEN (backend unchanged but release pipeline evidence must not regress)
- add/extend browser acceptance to verify the Drive review route and settings route under authenticated production conditions
- verify compact/mobile viewport behavior

Do not mark package #4 DONE if browser/mobile acceptance remains NOT VERIFIED.

## Rulings / scope corrections

- The 2026-09-30 broad Drive implementation plan listed Picker/workspace UI before later package slicing. Current `doc/progress.md` is more specific and is authoritative for execution order: Task 8 is the intelligent-organization review UI only.
- Task 7 is already DONE at 3/11; this plan starts package #4 and must not reopen Task 7 backend closure without evidence of regression.
- True external provider integration is Task 9/future evidence, not a hidden prerequisite for Task 8.
