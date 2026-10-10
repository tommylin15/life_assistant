# Life — Active TODO (2026-10-10)

**Release status PARTIAL.** P0/P1 implementation foundations are in main; production E2E acceptance is NOT VERIFIED.

| Priority | Task | Status |
|---|---|---|
| P0 | Dedicated curated table, bounded ChatGPT batch POST, HTTPS validation, idempotent upsert, signed-in GET | Implemented in source; ephemeral PG CI PASS on previous candidate; production NOT VERIFIED |
| P0 | Flutter curated UI, category/region/date/server filters, 1–5 stars, cost/benefit and registration unknowns | Basic list and city/star UI implemented; comprehensive device verification NOT VERIFIED |
| P0 | Actual approved ChatGPT scheduled connector, secret, DB + signed-in UI readback | **NOT VERIFIED / integration not configured** |
| P1 | Owner curated summary/errors and global feature rollout | Baseline source implemented; full error dashboard and controlled public rollout incomplete |
| P1 | User personal bottom/rail/drawer and Home layout/card preferences | Source implemented; real device and accessibility acceptance NOT VERIFIED |
| P1 | Drive AI admin provider allowlist/pause, health and usage | Source implemented; actual provider probes, budgets/tokens/cost and runtime NOT VERIFIED |
| Acceptance | Exact main SHA CI, V3 candidate, Preview, fixed staging true OAuth, live API/DB/UI/connector, rollback | NOT VERIFIED for new release |
| Operations | Read-only GCP old external Source Job/Scheduler status | Cloud Run Job exists per inventory #38012860019; Scheduler in `us-central1` **PASS (no matching jobs)** per #38013575831; other-region/external callers NOT VERIFIED |

| P1 product design → implementation | Split single curated pool into independent 限時機會 and 活動探索 user entries; allow overlapping activity membership; account-owned opt-in tracking, Task/Calendar dates, alerts; preserve unknowns | **APPROVED DESIGN / NOT IMPLEMENTED** — [canonical spec](curated_activity_user_features.md) |
| Future | Travel itinerary candidate handoff from curated events and accepted registrations | **DESIGN EXTENSION ONLY / NOT IMPLEMENTED** |

**CANCELLED, not pending**: MoC, TDX, EventGo/yii crawlers, official Excel/source registry, Queue/lease/ACK, old source 14-day acceptance, extra publication gate. Preserve legacy historical migrations/data non-destructively.

Follow [consolidated P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md).
