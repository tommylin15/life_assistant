# Life — Active Delivery Order (2026-10-10)

**Activity scope simplified; all upstream cancelled.** Previous P0–P2 MoC/TDX→Queue Job, 14-day source observations, official workbook scanner and Queue ACK tasks are **removed from the active backlog**, not deferred. Previous failures remain historical records.

1. **Direct curated intake [#10](https://github.com/tommylin15/life_assistant/issues/10):** Additive curated pool table; protected ChatGPT batch POST with dedup/upsert; signed-in GET and minimal Flutter curated list. Do not build a queue/source collector.
2. **Real ChatGPT integration:** configure an approved connector with separate credentials and prove one actual ChatGPT scheduled write + database/readback. The old Sheets/Queue task is disabled.
3. **Independent product modules:** small curated-pool admin/batch summary (no source control), Life internal Drive AI Provider admin [#11](https://github.com/tommylin15/life_assistant/issues/11), feature availability + user nav/Home [#12](https://github.com/tommylin15/life_assistant/issues/12).
4. **Normal gated V3 release:** tests/PostgreSQL/CI, Cloud Run candidate, Hosting, OAuth, runtime/API/UI; existing Phase 1 releases and privacy gates remain independent.

Existing source-job Cloud Run resources are not deleted. Do not restore removed GitHub source cron. [Current state](CURRENT_STATE.md).