# Life Free Events V2 — API and Candidate ACK Contract

**APPROVED DESIGN / NOT YET IMPLEMENTED** (2026-10-10). Supersedes prior [2026-10-09 contract](archive/free_events_ingestion_contract_2026-10-09.md) and associated strict verified-only publication requirement. Full [Issue #10](https://github.com/tommylin15/life_assistant/issues/10); new [V2 product](taiwan_free_events_discovery_plan.md).

| API (proposal, versioned) | Authorization | Intended behavior |
|---|---|---|
| `GET /api/v1/internal/free-events/queue?state=pending&limit=...&cursor=...` | Explicit limited ChatGPT/task read capability | Bounded, stable pagination; safe normalized fields with `queue_id`, `source_id`, `content_fingerprint`, source URL; **no mutation on GET** |
| `POST /api/v1/internal/free-events/curations:batch` | Distinct rate-limited curator write capability | Accept `selected` or `skipped`, reason and known/unknown fields; **Life server** checks exact version and atomically stores decision / selected pool and updates Queue. Returns per-item accepted/duplicate/stale/retry status |
| `POST /api/v1/internal/free-events/official-site-intake:batch` (if needed) | Permissioned official-source intake capability | Origin registry allowlist, HTTPS canonical event link, bounded validation and cross-source dedup; no arbitrary target URL fetch/SSRF |
| `GET /api/v1/free-events/candidates` | Signed-in user | Final curated-pool cards; filter/search/save, visible uncertainties and original source link. Does **not** claim official verified registration availability |
| Existing `GET /api/v1/free-events` | Current signed-in user | Preserve backward-compatible **legacy verified-only** read, not the final V2 pool |

Queue currently has `pending/processing/done/retry/failed` CHECK constraint; intentional AI `skipped` cannot be stored in that enum without an additive migration. Safer option: persist selected/skipped in a separate curation decisions table and ACK existing `done` for both, retain explicit reason; never misuse `failed` for skipped. Preserve original source ID, fingerprint, audit timestamp, model/rules version, idempotency and backoff. ChatGPT cannot write Queue directly.

Server rejects `verified=true`, `publish=true`, fabricated sources and overly confident fee/registration claims. No second publication gate, no user calendar/task/notes side effects. Tests: real PG atomic select/skip + ACK, POST replay, schema validation, 401/403, stale version, concurrent upsert, denied source, fee/date unknown, no GET ACK, API timeout/retry and real scheduled ChatGPT integration; actual E2E **NOT VERIFIED**.
