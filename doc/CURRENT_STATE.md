# life_assistant — Current State

**Observed 2026-10-10; point-in-time evidence, not a live dashboard.** Current GitHub main and runtime decide actual completion. Overall product: **PARTIAL**.

## Current architecture

Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL. GitHub `main` → Actions complete CI → public GHCR immutable digest → Cloud Run via V3. Production: https://gen-lang-client-0593591102.web.app/ ; fixed staging site: https://life-assistant-v3-stage-tl15.web.app/ (real fixed staging OAuth and safe rollback still require separate evidence).

## Verified release and remaining blockers

| Scope / gate | Status | Evidence |
|---|---|---|
| CI for SHA `ca23bedaa015988356b721330edd2da1fdbc43ce` (backend, Flutter, deploy scripts, real PG16) | **PASS** | [37958755185](https://github.com/tommylin15/life_assistant/actions/runs/37958755185) |
| V3 Cloud Run release of that SHA | **PASS** (workflow conclusion, not every product feature) | [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) |
| Free Events one-shot post-release source Job pin | **FAIL** at `Pin existing MoC source Job to promoted immutable GHCR digest` | [37958755189](https://github.com/tommylin15/life_assistant/actions/runs/37958755189) |
| Other official MoC observation workflow | **PASS** for execution; **NOT VERIFIED** for true latest Queue row counts | [37960798513](https://github.com/tommylin15/life_assistant/actions/runs/37960798513) |
| Owner-authenticated production Free Events Queue/selected pool readback, TDX, ChatGPT task E2E | **NOT VERIFIED** | No passing evidence available |
| Admin UI, feature rollout settings, custom navigation, real Home dashboard | **NOT IMPLEMENTED** | `lib/web/app_shell.dart` and `lib/web/web_app.dart` still hardcode navigation; `/today` placeholder |

**Important old/new design difference:** current `backend/scripts/run_free_events_moc_batch.py` enqueues and *immediately drains* the candidate Queue into the legacy free_event catalog; this **does not** yet implement the approved Queue-only → ChatGPT Chat curation → user-selected pool flow. Backend only has verified-only `GET /api/v1/free-events` and owner-only `/status`, not the proposed ChatGPT batch read/write APIs.

**AI / privacy:** Life internal provider routing exists in `backend/app/services/ai_enrichment_provider.py`; production multi-provider direct-health/cost and admin controls are **NOT VERIFIED**. Per-user Drive consent and Google OAuth are keyed by `user_sub` in code; cross-account live E2E must still be evidenced.

Past test/acceptance evidence is retained in [historical archive](archive/README.md); consult [acceptance.md](acceptance.md) for up-to-date evidence gates. No new deployment or data modification follows from this file.
