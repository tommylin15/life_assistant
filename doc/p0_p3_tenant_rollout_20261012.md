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
- Existing curated UX V3, activity DB query and personal actions remain.
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
