# Life — Release Checklist (2026-10-10)

A *working CI* or a *successful V3 GHCR release* is **not** proof that the entire Life product is DONE. Earlier 189-line gate checklist and its unchecked historical states are available in [archive/release_checklist_through_2026-10-09.md](archive/release_checklist_through_2026-10-09.md).

## Mandatory release gates (per changed product scope)

- [ ] GitHub main exact full SHA pinned to CI and immutable public GHCR digest, backend & Flutter tests, migration tests, permission/security tests.
- [ ] 0%-traffic Cloud Run candidate health/ready/auth and changed API acceptance; exact SHA Firebase Preview and rewrite/matched backend candidate.
- [ ] PostgreSQL additive migration real target version, idempotency/rollback strategy, schema consistency without Base.metadata DDL from live API.
- [ ] Approved V3 promotion, controlled traffic/rollback, live OAuth redirects, real account read/write where relevant, strict backend role/owner isolation.
- [ ] Source Jobs/retries/Queue row counts verified independently (no Job success → persisted events assumption), no unapproved source crawl, no cross-product data mutation.
- [ ] Personal Google/Drive OAuth and consent isolated; global Life AI settings cannot override user consent; no token leakage or secret in UI/log.
- [ ] Responsive user-facing Flutter UI, enabled/disabled feature access, navigation/Home preferences, stale/empty/error states and required real E2E.
- [ ] Exact logs/links recorded as **PASS / FAIL / NOT VERIFIED**; any missing mandatory gate stays PARTIAL, not DONE.

Current snapshot: [CURRENT_STATE.md](CURRENT_STATE.md) and [acceptance ledger](acceptance.md). Historic Calendar/Tasks/other signed-off package scopes retain their original evidence and are not silently reopened or weakened by new requests.
