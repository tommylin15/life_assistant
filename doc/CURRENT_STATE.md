# life_assistant — Current State (2026-10-10)

**Overall PARTIAL**; release proof and runtime evidence are required beyond GitHub implementation.

Architecture: Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL. CI/CD V3: GitHub Actions → immutable public GHCR digest → Cloud Run candidate → gated Firebase Hosting.

## Active curated-activity data path

Exactly **ChatGPT-selected activities → authorized Life FastAPI `/api/v1/free-events/curated:batch` → additive PostgreSQL `curated_activities` → signed-in Flutter curated pool**. ChatGPT is responsible for upstream research; Life does not crawl sources, fetch MoC/TDX, use official Excel/Queue/ACK, run batch discovery, or apply second-stage AI recommendation.

**Implemented in current main at source level**: additive Alembic 0015, authenticated bounded batch upsert with stable identity, curated listing/status, Flutter curated UI and site navigation. New `events` feature defaults **owner-only beta** until actual acceptance; old verified-only API preserved. **Actual ChatGPT scheduled writer secret/connector/live DB readback and production deploy: NOT VERIFIED**. Do not reactivate old Sheets/Queue ChatGPT task. Read-only GCP inventory [#38012860019](https://github.com/tommylin15/life_assistant/actions/runs/38012860019) confirms the obsolete `life-assistant-free-events` Cloud Run Job still **EXISTS** (job existence alone does not prove it is scheduled). The regional Cloud Scheduler readback [#38013575831](https://github.com/tommylin15/life_assistant/actions/runs/38013575831) is **PASS** for `us-central1`: no Scheduler Job names/targets matched the retired `life-assistant-free-events` job. This is scoped negative evidence only; other regions and external invocations remain NOT VERIFIED. No deletion/pause performed.

## New activity user UX — approved design, not source implementation

[限時機會／活動探索規格](curated_activity_user_features.md) splits **user-facing entry points only**, not the curated database. Opt-in per-account follow/watchlist, todo, informative calendar marks versus booking reminders versus confirmed trips, early warnings and travel candidate links are **NOT IMPLEMENTED / NOT VERIFIED**. Existing `events` curated Flutter page is still one basic list; generic Tasks/Calendar integrations do not implement this connection. The existing direct ChatGPT intake and source-state evidence above are unchanged.

## P1 modules

**Source implemented**: feature rollout API + owner UI, versioned account-owned personal navigation & Home cards, responsive bottom/rail/drawer, partial Home task/calendar/habits/events/projects cards, internal Drive AI admin allowlist/pause, aggregate-only usage and direct rate-limited probe. Personal Google OAuth/Drive AI content consent never delegated to administrator. **Actual per-device UI / provider smoke / runtime verification: NOT VERIFIED**. Usage tokens/cost, advanced budgets/alerts and owner E2E remain partial.

## Fixed staging OAuth incident (2026-10-10)

Live read-only OAuth redirect probe [#38022456431](https://github.com/tommylin15/life_assistant/actions/runs/38022456431): **fixed staging `/auth/login` FAIL** — `redirect_uri` still points to production `/auth/callback` while the `__session=oauth:` state cookie is set on the staging hostname; this explains user-observed post-Google-login `401 Missing session` at the cross-origin callback. SHA Preview also points to the production callback and is **not a valid Google login host**. Production `/auth/login` targets production and remains PASS for redirect origin only. Anonymous Flutter homepage checks [#38022194645](https://github.com/tommylin15/life_assistant/actions/runs/38022194645) PASS for all three sites, but **do not prove login**.

The current `main` backend has `oauth_redirect_for_request` support for the fixed staging hostname; **the existing fixed staging live backend pin is not yet promoted to a version that returns this callback**, so this is a **deployment/runtime gap, not a confirmed new source-code defect**. Next gate is **staging-only** V3 pinned version release + real owner OAuth callback/session readback with production traffic and Hosting unchanged. Do not claim staging OAuth PASS, production cutover, or successful user login before those runtime results. The one-time read-only probe job was removed after the result.

## Evidence
Prior V3 historical release [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) PASS for its own previous SHA only. P0/P1 candidate CI [38009774496](https://github.com/tommylin15/life_assistant/actions/runs/38009774496) had backend, ephemeral PostgreSQL, Flutter and deployment checks PASS for SHA `19f693263bc9c546a2d81239b9fc236cc53833e3`. Subsequent implementation changes must pass CI for their **own** SHA; historical PASS is not inherited.

Current post-CI follow-up: repaired Drive AI provider selection overwriting note candidates; added fixture regression tests and a rollback-only curated 0015 live DB smoke to V3 release, with migration before Drive AI runtime check and mandatory fourth PostgreSQL CI gate. Added the optional, separately controlled fixed staging live source flow requiring valid prior version, actual pinned Hosting/API/auth version, owner OAuth E2E and rollback; this code does not mean staging has been changed. These changes require new exact-SHA CI and still do not prove any live production integration.

Full consolidated matrix: [P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md); [active TODO](todo.md). No unsupported claim of DONE.
