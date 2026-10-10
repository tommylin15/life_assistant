# /ponytail-review — activity batch, 2026-10-10

What this change does: The fixed Drive handoff imports activities with permanent keys and versioned receipts. Users browse grouped activities in two entries and choose their own private actions. Admin controls public availability; AI management improvements remain deferred.

Reviewed the importer, schema, API callers, Task ownership checks, Google adapter and token refresh, Flutter routes/cards/navigation, release migration order and related tests. Assumed a daily outbox of at most 1000 rows and the initial small user population; the importer rejects larger inputs and personal action reads have a documented 1000-row limit.

No remaining source blockers found after correcting stale receipts, canceled Calendar lifecycle IDs, zero-cost hashing, and collisions between legacy identities and handoff group keys. The fixes have regression tests. The additive migration preserves existing data; Google writes require explicit user choice and account OAuth. No import creates personal entries automatically.

Validation: full backend suite 529 tests OK (19 integration tests skipped in that run), then targeted tests for subsequent boundary fixes; separate actual local PostgreSQL concurrency, URL changes/stale versions, Task isolation and grouped pagination passed. Flutter full suite 72 passed before the final boundary fixes; card tests rerun after those fixes. Changed Flutter files had no analyzer errors/warnings (24 informational lints). Web release build passed.

Verdict: Ship source to CI/staging. Production acceptance remains a separate gate.

Follow-up review before the next commit/push: CI 38041481706 reached the namespace-collision regression and found the manually constructed legacy fixture omitted mandatory occurrence_key. Added the explicit legacy value, matching the existing schema; production code is unchanged. Other actual PostgreSQL curated tests passed. Re-run the complete CI on the corrected SHA.

Not checked: the final PostgreSQL namespace-collision regression was blocked locally by WSL network reset (WinError 64 / Wsl Service 0x8007274c); CI must run it. Its Flutter counterpart passed. Real Sheet permissions/version-qualified receipt compatibility with the exploration writer and cleaner, deployed GCP Job/Scheduler, real Calendar OAuth actions, new-SHA staging and final admin/Home acceptance remain pending. App push is not implemented; reminders use Google Calendar popup.
