# life_assistant — Current State (2026-10-10)

**Overall PARTIAL.** Actual GitHub main + runtime evidence outrank this snapshot.

Architecture: Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL. Deployment: GitHub Actions → public GHCR digest → Cloud Run V3; previous release [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) PASS for prior SHA.

## New simplified activity path

Only **ChatGPT (research/selection) → Life authenticated curated-items API → PostgreSQL → Flutter user curated pool**. All Life activity upstream (MoC/TDX/official Excel, source registry, Queue, source batch/scheduler, extra publication gate) CANCELLED. Previous ChatGPT task writing Google Sheets/Queue disabled.

Code cleanup [10335187](https://github.com/tommylin15/life_assistant/commit/10335187e3e2a338eed5c76b4d61bd2c18a605e3) removed old GitHub source workflows/crawlers and replaced MoC source-job Python entrypoint with fail-closed stub. **Legacy Alembic 0011–0014, historical DB data and legacy GET /api/v1/free-events are retained.** New direct POST/GET and Flutter pool have **NOT** been implemented or deployed. Existing Cloud Run Job configuration/scheduler runtime needs a separate readback; deletion of GitHub cron does not stop any independent GCP trigger.

Historical MoC activation [37958755189](https://github.com/tommylin15/life_assistant/actions/runs/37958755189) FAIL remains honest historical evidence but not a current release blocker. Main cleanup CI/run must be verified separately. Life Drive AI admin [#11](https://github.com/tommylin15/life_assistant/issues/11) and per-user feature/navigation/Home [#12](https://github.com/tommylin15/life_assistant/issues/12) remain independent and NOT IMPLEMENTED.