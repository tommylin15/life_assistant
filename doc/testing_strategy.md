# Life — Current Testing & Verification Strategy (2026-10-10)

All tests must correspond to existing implementation and actual changed behavior. **CI PASS does not mean production or provider PASS**. Never mark a feature DONE without sufficient independent evidence; classify implementation/tests/CI/deployment/runtime/integration as **PASS / FAIL / NOT VERIFIED**.

## Local + CI

1. Backend: Python unit/API/security tests, sanitized error handling, schema validation and replay; real ephemeral PostgreSQL 16 for Alembic migration, transactions, concurrency and uniqueness; no production writes from tests.
2. Flutter: analyzer, widget/route/responsive tests and production build; cover loading/empty/error/disconnected, deep links, role/availability route denial, keyboard/drag reorder and Home card preferences when implemented.
3. Deployment scripts/workflows: syntax/contract tests for immutable GHCR digest, 0%-traffic candidate, preview/backend parity, WIF least privilege, migration before cutover, rollback, old revisions/Job pin and deterministic env metadata.

## Runtime / user integration

- Exact full SHA CI → candidate health/ready/401 → migration/DB schema readback → production traffic/rollback → real Google OAuth/Calendar/Drive scope and direct provider health where relevant; verify both backend and frontend release SHA.
- Free Events: No Life source crawler/Queue. Test direct ChatGPT-selected POST with auth, duplicate replay, unknown fee/date, safe URL, atomic PostgreSQL upsert and final selected-pool Flutter readback. Mocked connector is insufficient for real ChatGPT scheduled E2E.
- Admin / personalization: real user cannot mutate/see owner-only settings; one user cannot read/write another user's preferences; a globally hidden feature denies deep-link/API; each user's Drive content-consent OFF prevents provider access regardless of admin toggles.
- Record run IDs, commit/digest, real source data scope, failure category, state transitions, per-layer PASS/FAIL/NOT VERIFIED. A job workflow success alone never proves a PostgreSQL row count or end-user availability.

## Legacy

Historic SQLite local-folder sync, native biometric/PIN and old Drive Bridge action tests remain subject to their actual implementation and future scoped release, not a reason to reintroduce old CI/CD V2 or require all mobile-native features as current Web release blockers. See [archive](archive/README.md), [release_checklist](release_checklist.md) and [CURRENT_STATE.md](CURRENT_STATE.md).
