# Life — Active engineering TODO
Updated 2026-10-15. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

| Priority | Work / exit gate | Status |
| --- | --- | --- |
| P0-1 | Verify actual **GAS 07:30 trigger → importer Job Exit 0 → PostgreSQL event_key/content_hash readback → Sheet version-fenced ACK/ERROR** on same execution; separate `data_status=PARTIAL` from technical failure. Prevent duplicate imports. | **NOT VERIFIED**; promoted Job image aligned, execution was NOT_RUN in Release |
| P0-2 | Complete **three real-account** private-data isolation + activities/notes/tasks/shopping; test cannot cross-read/write another account. | Synthetic PG acceptance **PASS**, full real-user matrix **NOT VERIFIED** |
| P1-1 | Complete **signed Gemini through logged-in Life `/ai/text` and UI** including 429/502/503/timeout, permission/quotas and no implicit Google Drive content transfer. | Signed synthetic smoke **PASS**, UX E2E **NOT VERIFIED** |
| P1-2 | Verify activities **multi-day search, pagination during updates, old favorites, personal tracking/Task, Google Calendar actual write/readback**, including user-level isolation. | Source/CI **PASS**, full live E2E **NOT VERIFIED** |
| P1-3 | Validate **Shopping list + item edit/delete, multiline add and Task deletion** across production browser, fresh reload, secondary account and error cases. | User manual checks positive; expanded automated regression **NOT VERIFIED** |
| P1-4 | Drive AI admin/per-user consent, provider failures, **real token/cost/accounting** if introducing budget enforcement; never fabricate spend. | Partial implementation, costs/budget **NOT VERIFIED** |
| P2-1 | Investigate Cloud Run **62 retained revisions protected by tags/rollback**; review actual traffic/tag/retention dependencies before cleanup, without risking rollback. | `PARTIAL_PROTECTED` |
| P2-2 | Audit dependency/action pinning, public-repository hygiene, access to operational docs, observability, backup restoration and scheduled-job dedupe. | Risk follow-up **NOT VERIFIED** |

Release reference: [latest verified original source SHA and actions](CURRENT_STATE.md). New `main` documentation commits start a new SHA and do not inherit production evidence. A standard `main` push runs the four CI jobs and staging-only flow; production promotion has its distinct manual V3 release gate. Do not run a second importer on top of GAS without checking the execution ledger.