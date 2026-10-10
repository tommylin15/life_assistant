# Life — Active TODO (2026-10-10)

**Release status PARTIAL.** P0/P1 implementation foundations are in main; production E2E acceptance is NOT VERIFIED.

| Priority | Task | Status |
|---|---|---|
| P0 | Dedicated curated table, bounded ChatGPT batch POST, HTTPS validation, idempotent upsert, signed-in GET | Implemented in source; ephemeral PG CI PASS on previous candidate; production NOT VERIFIED |
| P0 | Flutter curated UI, category/region/date/server filters, 1–5 stars, cost/benefit and registration unknowns | Basic list and city/star UI implemented; comprehensive device verification NOT VERIFIED |
| P0 | Drive 交接表 READY → Life GCP Job 讀取 → event_key/content_hash PostgreSQL upsert → Sheet ACKED/ERROR、30天保留、owner/Flutter readback | **APPROVED / NOT VERIFIED**；既有 direct API 僅相容 |
| P1 | Owner curated summary/errors and global feature rollout | Baseline source implemented; full error dashboard and controlled public rollout incomplete |
| P1 | User personal bottom/rail/drawer and Home layout/card preferences | Source implemented; real device and accessibility acceptance NOT VERIFIED |
| P1 | Drive AI admin provider allowlist/pause, health and usage | Source implemented; actual provider probes, budgets/tokens/cost and runtime NOT VERIFIED |
| Acceptance | Exact main SHA CI, V3 candidate, Preview, fixed staging true OAuth, live API/DB/UI/connector, rollback | NOT VERIFIED for new release |
| Operations | Read-only GCP old external Source Job/Scheduler status | Cloud Run Job exists per inventory #38012860019; Scheduler in `us-central1` **PASS (no matching jobs)** per #38013575831; other-region/external callers NOT VERIFIED |

| P1 product | One-parent event card grouping distinct offers/sessions; two user entries 限時機會／活動探索 with overlapping membership, evidence-aware advance-opening display and original links | **APPROVED DESIGN / NOT IMPLEMENTED** — [canonical spec](curated_activity_user_features.md) |
| P1 data/API contract | Map current URL+occurrence_key identity to parent/offer grouping; add opening times, evidence/conflict, refundable deposit conditions only via backwards-compatible additive migration and tests if needed | **GAP CONFIRMED / NOT IMPLEMENTED** |
| P1 personal actions | Opt-in account-owned watchlist, Task, Calendar information marks versus registration reminders versus confirmed schedule; group duplicate alerts and keep users isolated | **APPROVED DESIGN / NOT IMPLEMENTED** |
| Future | Travel itinerary candidate handoff from curated events and accepted registrations | **DESIGN EXTENSION ONLY / NOT IMPLEMENTED** |

**CANCELLED, not pending**: Life 端 MoC/TDX/EventGo/yii 來源 crawler、舊來源 Excel scanner、Queue/claim/lease、第二輪 AI、舊來源14天驗收、額外發布閘。**新 Sheet ACKED 是匯入回執，不是舊 Queue ACK。** 保留 legacy migrations/data。

Follow [consolidated P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md).
