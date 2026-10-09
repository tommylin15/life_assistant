# Life — Current Approved Product Architecture (2026-10-10)

**Product direction approved; unimplemented features must not be called deployed.** GitHub code/runtime are Source of Truth: [current state](CURRENT_STATE.md).

## Architecture

Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL. Life owns Data + UI + API + Execution + Integration, not general agent reasoning.

**One and only one activity data path:** ChatGPT independently finds/selects events → Life authenticated direct intake API → PostgreSQL **curated pool** → Flutter list/cards. Life does not ingest MoC/TDX, inspect official-site Excel, run a source crawler or Queue, or apply a second AI/recommendation/publication layer. User freely browses, filters and chooses. [Activity contract](taiwan_free_events_discovery_plan.md), [GitHub #10](https://github.com/tommylin15/life_assistant/issues/10).

**Minimal Life admin modules:** curated items and inbound processing errors (not source/Queue operators); system health; internal Life Drive AI providers/models/quotas [#11](https://github.com/tommylin15/life_assistant/issues/11); global feature release toggles [#12](https://github.com/tommylin15/life_assistant/issues/12).

**Each user's own settings:** Google Gmail/Calendar/Drive consent, Drive AI content processing consent, navigation bottom/left favorites/order and homepage cards. Backend auth applies separately. Admin may never read other users' Drive private content or OAuth secrets.

**Flutter UI:** Keep Material 3 responsive mobile bottom nav and desktop left rail. Per-user Home cards: tasks, schedule, attention, habits, projects and (after new API release) curated event previews; optional notes, shopping, consented Drive AI.

**Current code gap:** previously added PostgreSQL source/catalog/Queue migrations 0011–0014 remain for history; legacy verified-only events API/UI still exists. New ChatGPT direct write/curated read/Flutter cards and scheduled connector E2E are NOT IMPLEMENTED/NOT VERIFIED. Deleting GitHub workflows does not verify removal of external GCP Cloud Scheduler triggers.