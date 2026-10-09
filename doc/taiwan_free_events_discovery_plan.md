# Taiwan Free/Value Events V2 — Current Product / Engineering Contract

**Approved 2026-10-10; implementation PARTIAL.** Supersedes the old M0–M4 'aggregate → immediate catalog → strict verified-only → formal publication' flow and EventGo/yii site crawler plan. Historical full design: [archive/taiwan_free_events_plan_2026-10-09.md](archive/taiwan_free_events_plan_2026-10-09.md). Detailed backlog [Issue #10](https://github.com/tommylin15/life_assistant/issues/10).

## Actual target data flow

1. Official structured **MoC + individually approved TDX** sources → deterministic safe normalization, versioned fingerprint, dedup → PostgreSQL durable **intake Queue only**. TDX remains disabled until access conditions and API/credential/rate-limit review PASS; EventGo and yii.tw no automated crawling, data.gov.tw general directory deferred.
2. **Daily user-managed ChatGPT Chat task** reads a bounded page of pending Queue items via auth API (**read-only**). It may also check a reviewed allowlist of **official organizer sites** in an Excel/Sheet with explicit permission, freshness and stable link identity. Existing permitted source links yield new items to the same ingestion/curation path.
3. AI makes pragmatic semantic initial choices `selected` or `skipped`, with reasons and visible uncertainty fields. **Every analyzed item needs a submitted decision**, including skipped; a GET alone must not mark it processed. Do not assert exact price, free status, guaranteed benefit or booking window without evidence.
4. Life curation POST checks caller, queue_id, source, exact content fingerprint/version, and idempotency. **Atomically** upsert selected into the user-facing candidate pool (or record skipped decision), then ACK / transition Queue state. Ingestion errors leave items pending for later retries; stale content or concurrent results cannot ACK newer versions. Queue state is never directly writable by ChatGPT.
5. **Terminal product output: user-selected browsing pool.** No second stage 'official recommendation', 'registration-ready', manual publish or automatic calendar/task/reminder creation. Unknown venue/date/fee fields are labeled; exclude obvious stale, canceled, unsafe or duplicate items; slight inaccuracies acceptable and corrigible. Users decide whether to open original official link, search/filter/save independently.

## Current code discrepancy and remaining work

- Current `20261009_0014` normalized Queue exists and MoC producer uses it, but `run_free_events_moc_batch.py` **also immediately claims it and writes `free_events`**. Change to Queue-only, preserving existing source lease/observations and additive migrations.
- Existing `GET /api/v1/free-events` is verified-only (older UI). Need separate Queue read, curation result write, selected-pool read + Flutter screen, idempotent ACK, and source license control. Need real ChatGPT task / connector invocation proof; don't assume arbitrary private API calls work in Tasks.
- Latest V3 release [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) PASS, but source activation [37958755189](https://github.com/tommylin15/life_assistant/actions/runs/37958755189) FAIL at MoC Job digest update; production Queue figures NOT VERIFIED.

## Acceptance

Auth 401/403; source permission revocation; fixed safe official URLs; duplicate source/cross-source identities; selected pool upsert+ACK and skip-only ACK; stale fingerprint refusal, version-change requeue, concurrent/replayed task; failure leaves pending; unknown fee/date display; no unapproved crawler, no private Calendar/task/note writes; real PostgreSQL counts and authenticated UI; V3 CI/deploy/runtime. Quality metrics and 14-day freshness can be observed after initial selected pool goes live; do not synthesize timestamps or make an unnecessary secondary publication gate.
