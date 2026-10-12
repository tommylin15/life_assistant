# P0–P3 consolidated delivery evidence (2026-10-12)

Scope: authenticated general-account home/tasks/calendar/personalization, scoped
private notes/projects/habits/shopping, curated activity flow, UI/release.

## Delivered in source
- Existing P0 Flutter auth, tasks, calendar, personalized home/nav/logout
  and 11-card/UI implementation retained; second staging account OAuth E2E
  explicitly reported PASS by user for SHA a96f0798.
- Additive Alembic 0018 adds nullable indexed user_sub to legacy private tables,
  retaining every existing legacy NULL row. Only the configured Owner can read
  legacy NULL; all new private records carry the caller Google subject.
- Route guards cover listing, detail, mutations, note links/tags, habit history,
  shopping parent/child, project references from tasks/notes/shopping, Gmail
  project creation. Cross-tenant IDs must yield 404, not permit writes.
- Staging's approved tester can reach the four owner-scoped resources.
  Google Drive links, templates and admin remain blocked until separately
  audited. Private production access policy is unchanged.
- Audited curated listing/filters and account-owned personal actions now pass the\n  staging tester route gate, but each remains subject to feature rollout and\n  activity_access; ingestion, status and connector remain blocked.\n- Existing curated UX V3, activity DB query and personal actions remain.
  Curated event release/visibility follows the separate admin rollout policy;
  exposing common curated data in staging is not equivalent to approval.
- Existing consistent feature header cards, notes category tabs and home cards
  remain unchanged. No user data deleted, no production traffic promoted.

## Mandatory gates and evidence
1. CI: all four jobs PASS on the single combined main SHA.
2. Additive migration Job: 0018 applied and verified before staged API readback.
3. Staging: exact SHA, pinned Hosting rewrites, 401 and Google redirect PASS.
4. Tenant runtime: Owner legacy visibility; second user cannot read Owner or
   third user notes/projects/habits/shopping; personal prefs/logout and tasks
   writable/readable without cross-account leakage.
5. Curated actions: real Sheet ACK/ERROR after DB commit, dedup and Google
   Calendar/Task source links separately verified; failure remains PARTIAL.
6. Production: only explicit V3 workflow_dispatch promotion and live gates.
   CI or source changes alone do not constitute DONE.

## 2026-10-13 Staging tester curated route correction
- Registered public signed-in endpoints are `/api/v1/free-events/curated`, `/api/v1/free-events/curated/filters` and `/api/v1/free-events/curated/actions`, **not** `/api/v1/curated`. The previous staging allowlist incorrectly accepted non-existent shortened paths; authenticated secondary testers were rejected before query execution.
- Stage tester route permissions now match FastAPI route registration and constrain per-item writes to existing V3 save/task/calendar_info actions. Owner-only status, connector, batch import, admin and historical follow/reminder actions remain denied.
- Admin feature-rollout policy is still enforced independently: ordinary users need enabled/all for opportunities/explore. No production account access or beta default is broadened.
- Flutter shows distinct signed-in 401, not-enabled 403, and other fetch failures. CI+Staging readback, and authenticated user E2E remain separately verified.

## 2026-10-13｜一般帳號活動載入與遺留資料安全檢查
- User reports real staging account activity list loads successfully for fixed staging release SHA `fc9c94d216a7985b88eb6ffe494457102afea59b`; classified **PASS for authenticated page load only**. Bookmark/task/calendar action E2E remains NOT VERIFIED.
- Security review: tenant visibility for NULL legacy rows now fails closed if `ALLOWED_GOOGLE_EMAIL` is empty/missing rather than interpreting every user as Owner. Explicitly owned records continue to be accessible only to matching Google sub. Added isolated unit coverage for empty, whitespace and missing owner config.
- This does not promote the production Hosting site or weaken rollout gates; current staging verification and production promotion are independent.
