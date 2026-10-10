# Life P0/P1 consolidated delivery and acceptance matrix (2026-10-10)

**Current status: PARTIAL; do not declare DONE from commits or a green CI.** This document distinguishes a passing build from a new SHA's runtime and connector integration.

## Scope and implementation evidence
- P0 direct ChatGPT-curated intake: `backend/app/api/curated.py`, `backend/app/models/curated.py`, additive Alembic `20261010_0015`; bearer-only bounded 40-item POST, URL safety, stable URL+occurrence dedup/upsert, atomic DB write and audit; no source crawler or Queue.
- P0/P1 consumer Flutter: `lib/web/curated_events_page.dart` with original links, city/star filters and unknown price/date/registration indicators. Legacy events GET remains backward compatible. New curated rollout defaults to owner-only beta pending genuine end-to-end acceptance.
- P1 management: governed feature rollout by owner; private revision-fenced user UI preferences; bottom/rail/drawer layout and Home card selection; Drive AI nonsecret platform pause/provider allowlist, health probe (harmless fixture, single provider, owner-only, one call per provider per 15-minute bucket), honest usage counts and **cost/tokens unknown unless instrumented**. All Google Drive AI consent and OAuth remain the account owner's choice.
- P1 Home: tasks/due dates, bounded next-calendar preview, verified API activity preview and habit quick-check-in. Unknown/disconnected states are not fabricated.
- Replaced retired official-source collection with exactly one: ChatGPT selects -> Life authenticated direct write -> PostgreSQL curated pool -> Flutter read. No 14-day source acceptance / MoC / TDX / queue gate.

## Required acceptance, not yet implied by code
| Gate | Required check | Recorded state |
|---|---|---|
| Code/schema | Approved main SHA; additive 0015 head, no destructive schema | Source implemented; release DB NOT VERIFIED |
| API security | no token/invalid token 401 or absent config 503, 401/403 for nonowner, owner-only policies | Contract tests; production NOT VERIFIED |
| Database | real PostgreSQL idempotent POST, splitting same source by occurrence, atomic transaction, version conflict, cross-user isolation | CI ephemeral PostgreSQL PASS on prior candidate; release workflow now includes **rollback-only 0015 smoke** before traffic promotion; production NOT VERIFIED |
| Flutter | flutter analyze/test, mobile/desktop navigation, consumer cards and Home responsive build | CI results must match final SHA |
| Internal AI | personal consent OFF, global OFF, per-provider allowlist, owner-only direct probe, direct health vs fallback and cost limits | Real provider & budget NOT VERIFIED |
| ChatGPT connector | Provision separate `LIFE_CURATED_INGEST_TOKEN` (>=32 secret bytes; Secret Manager or secret bundle), bind approved connector capability, run real scheduled POST to exact backend and owner authenticated readback | **NOT VERIFIED**; disabled old queue task must stay disabled |
| Staging/production V3 | exact SHA CI, public GHCR digest, candidate, SHA preview pinned rewrites, fixed staging owner Google OAuth, live API/DB/UI and rollback | Gated fixed-staging source + rollback added, `publish_staging=false` by default; **runtime NOT VERIFIED** for this release |
| Legacy resources | read-only inspect residual Cloud Run source Job / Cloud Scheduler triggers; do not delete without explicit confirmation | NOT VERIFIED |

**Release safety**: New feature **events** defaults to owner-only beta. Production rollout to all users requires the separately controlled non-secret `LIFE_CURATED_PUBLIC_ROLLOUT_APPROVED=1` runtime flag, set **only after** exact-SHA V3, real ChatGPT connector, owner OAuth and database readbacks pass. Without it, the owner/admin public enable operation fails with HTTP 409. The flag is not set by these code changes, and a public toggle by itself is insufficient. Do not bypass this lock to claim P0 DONE. Preserve previous live Hosting and Cloud Run traffic if any gate is unknown.

## Known incomplete pieces
- The actual ChatGPT scheduled connector cannot inherit user browser Google OAuth, and current GitHub changes do not inject a production connector secret.
- Real staging Google callback and end-to-end production API/owner DB readback remain external prerequisites; a local/CI sidecar is not production. The fixed staging publishing script now aborts on invalid prior live baseline, bad /api/** or /auth/** pins, missing exact SHA or failed owner OAuth, and restores prior staging Hosting version when safe; these recovery cases are code/test evidence only. The GitHub connector currently has no workflow_dispatch mutation capability, so no V3 run was triggered here.
- AI request budget/tokens/cost measurement and a verified safe public curated rollout are not complete. 2026-10-10 post-CI review also found and corrected **Drive AI provider-chain variable shadowing note candidates** and added mocked execution regression tests; this fix requires a new green CI. V3 release must require all four main SHA jobs (including PostgreSQL), migrate to 0015 before Drive AI consent checks, and run the rollback-only curated readback test. Candidate-only (`promote=false`) still has no production traffic cutover. Provider direct-health tests must be executed explicitly by an authorized owner.
- UI feature rollout and preferences require authenticated live-browser device regression (responsive, keyboard, cache, deep links), not only Flutter build.
- Existing historical free event rows/migrations are intentionally retained; no destructive cleanup is allowed.

## Execution
Keep the implementation commits in main and repeat CI as needed for defects. For final acceptance run a **single exact-SHA gated V3 release**, only when every prerequisite is met. Record its run URL, source SHA, GHCR digest, migration revision and row readbacks, candidate/Hosting pins, rollback baseline and OAuth/connector evidence. Record each PASS/FAIL/NOT VERIFIED separately.
