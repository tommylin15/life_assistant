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

**2026-10-10 follow-up — V3 [#38023532632 attempt 2](https://github.com/tommylin15/life_assistant/actions/runs/38023532632/attempts/2):** candidate, database acceptance, Preview, and fixed-staging preflight **PASS**. A new staging Hosting version `36b7a8ddcf919c04` was temporarily published, but the subsequent post-publish check exited 1 **before** `staging_oauth_canary=ACTIVE`. Its precise failing subcheck is **NOT VERIFIED** because the old script logged no failure layer. The staging-only rollback reported **PASS**, restoring version `e3a6dd23aec06848`. Real owner Google OAuth remains **NOT VERIFIED**; do not retry the old release SHA as if fixed.

Following this evidence, `scripts/v3_fixed_staging_release.sh` on `main` adds bounded 24-attempt post-publish live readback (5-second spacing), explicit failed-gate phase markers, strict failure on REST version/rewrites/API 401, and visible canary-activation logging. These are **source fixes only** until current-SHA CI and a new staging-only release prove runtime PASS. Production Hosting and traffic remain outside this staging task.

Live read-only OAuth redirect probe [#38022456431](https://github.com/tommylin15/life_assistant/actions/runs/38022456431): **fixed staging `/auth/login` FAIL** — `redirect_uri` still points to production `/auth/callback` while the `__session=oauth:` state cookie is set on the staging hostname; this explains user-observed post-Google-login `401 Missing session` at the cross-origin callback. SHA Preview also points to the production callback and is **not a valid Google login host**. Production `/auth/login` targets production and remains PASS for redirect origin only. Anonymous Flutter homepage checks [#38022194645](https://github.com/tommylin15/life_assistant/actions/runs/38022194645) PASS for all three sites, but **do not prove login**.

The current `main` backend has `oauth_redirect_for_request` support for the fixed staging hostname; **the existing fixed staging live backend pin is not yet promoted to a version that returns this callback**, so this is a **deployment/runtime gap, not a confirmed new source-code defect**. Next gate is **staging-only** V3 pinned version release + real owner OAuth callback/session readback with production traffic and Hosting unchanged. Do not claim staging OAuth PASS, production cutover, or successful user login before those runtime results. The one-time read-only probe job was removed after the result.

## Fixed staging OAuth callback repair (2026-10-10, source only)

New staging release [#38027300562](https://github.com/tommylin15/life_assistant/actions/runs/38027300562) failed with `staging_google_redirect=FAIL wrong_callback` after exact live Hosting version, release SHA, pinned `/api/**` + `/auth/**`, and unauthenticated API 401 all **PASS**. Rollback to `e3a6dd23aec06848` **PASS**. This proves the old OAuth host-header heuristics are insufficient for actual Firebase Hosting → Cloud Run requests. Production release/traffic were not promoted.

Repair in `backend/app/api/auth.py`, `lib/web/login_page.dart` and `scripts/v3_fixed_staging_release.sh`: fixed staging Flutter calls the explicit `/auth/staging/login` backend entrypoint, which always uses the **constant allowlisted** staging Google callback, stores staging provenance in the existing HttpOnly/Secure `__session` OAuth state and authenticated session, and reads that provenance on callback, `/auth/me`, and Google incremental authorization. Production keeps normal `/auth/login` and production callback. No dynamic user-supplied callback URL. In `v3-release-ghcr.yml`, the Preview must now prove `/auth/staging/login` sets state cookie and emits the fixed staging redirect **through the real Hosting rewrite**, before any fixed staging mutation. Tests cover missing forwarded headers, OAuth callback, wrong state, verified session and owner E2E evidence. The failure stage remains fail-closed with staging rollback.

**Status: source implementation complete; full exact-SHA CI, preview smoke, fixed staging live, true owner Google login and session readback: NOT VERIFIED until independent runtime evidence is observed.** Do not ask the owner to rerun the old release, and do not present the restored staging as repaired.

## Evidence
Prior V3 historical release [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) PASS for its own previous SHA only. P0/P1 candidate CI [38009774496](https://github.com/tommylin15/life_assistant/actions/runs/38009774496) had backend, ephemeral PostgreSQL, Flutter and deployment checks PASS for SHA `19f693263bc9c546a2d81239b9fc236cc53833e3`. Subsequent implementation changes must pass CI for their **own** SHA; historical PASS is not inherited.

Current post-CI follow-up: repaired Drive AI provider selection overwriting note candidates; added fixture regression tests and a rollback-only curated 0015 live DB smoke to V3 release, with migration before Drive AI runtime check and mandatory fourth PostgreSQL CI gate. Added the optional, separately controlled fixed staging live source flow requiring valid prior version, actual pinned Hosting/API/auth version, owner OAuth E2E and rollback; this code does not mean staging has been changed. These changes require new exact-SHA CI and still do not prove any live production integration.

Full consolidated matrix: [P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md); [active TODO](todo.md). No unsupported claim of DONE.
