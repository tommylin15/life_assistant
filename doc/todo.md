# Life — Active TODO (2026-10-10)

Canonical order: [phase1_delivery_order.md](phase1_delivery_order.md). See [CURRENT_STATE.md](CURRENT_STATE.md) for exact run status and [archive](archive/README.md) for the previous lengthy task list.

| Priority | Active work | Implementation | Runtime |
|---|---|---|---|
| P0 | Diagnose [MoC Job pin failure 37958755189](https://github.com/tommylin15/life_assistant/actions/runs/37958755189); owner-authenticated Queue counts and source digest readback | PARTIAL | FAIL/NOT VERIFIED |
| P1 | Refactor official MoC fetch to **Queue-only**; keep revoked/denied sources off; TDX gated | Existing Queue PASS; new flow not done | NOT VERIFIED |
| P2 | ChatGPT Queue read-only API; atomic select/skip decision ingest API with idempotent version ACK and retry | NOT IMPLEMENTED | NOT VERIFIED |
| P3 | Persist/show **selected user pool** (source link, unknown fields, filter/save); update Flutter from verified-only old list | NOT IMPLEMENTED | NOT VERIFIED |
| P4 | Build owner-only Life Admin Center sources/Queue, batch outcomes and operations, audit/permission boundaries | NOT IMPLEMENTED | NOT VERIFIED |
| P5 | Platform Life AI Provider settings + health/budget (separate from user's Drive consent and ChatGPT) [#11](https://github.com/tommylin15/life_assistant/issues/11) | Provider route exists; admin controls not done | NOT VERIFIED |
| P6 | Admin feature rollouts; per-user adaptive navigation and Home cards [#12](https://github.com/tommylin15/life_assistant/issues/12) | Existing hardcoded shell only | NOT VERIFIED |
| P7 | TDX approved API + official-site workbook + actual ChatGPT scheduled E2E, with legally reviewed access | NOT IMPLEMENTED | NOT VERIFIED |
| P8 | Joint CI/V3/staging/live/PostgreSQL/Google account acceptance and original unfinished Phase 1 gate readback | PARTIAL | NOT VERIFIED |

**Removed from active TODO:** EventGo/yii crawler, generalized data.gov.tw directory activation, extra 'officially recommended/registrable' publication gate, Cloud Build V2, completed historical package checklists. Do not use a documentation edit to claim production work done.
