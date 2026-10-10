# Life Direct ChatGPT → Curated Pool API (2026-10-10)

**EXISTING API IMPLEMENTED IN GITHUB MAIN / RUNTIME NOT VERIFIED; COMPATIBILITY PATH, NOT NEW DEFAULT IMPORT.** 最新以 [獨立 Drive「交接資料」Job 契約](curated_sheet_job_ingestion.md) 為準；舊 Queue／來源 crawler 取消。

| Endpoint (source implemented) | Responsibility |
|---|---|
| POST /api/v1/free-events/curated:batch | Approved ChatGPT caller submits selected activities only; backend validates, dedups and upserts into curated pool. No Queue reference, no selected/skip ACK. |
| GET /api/v1/free-events/curated | Authenticated users browse selected entries, basic filter, link to original source and unknown fee/date labels. |

Actual `CuratedBatchIn` accepts `items` (1–40). Each `CuratedItemIn` requires `title` (2–400 chars) and `original_url` (public HTTPS only); optional `occurrence_key` (default `main`, allows splitting child sessions with the same URL), `summary`, `city`, `category`, `starts_on` and `ends_on`, `fee_kind` (`free`/`paid`/`conditional_free`/`unknown`), `fee_amount`, `benefit_value`, `on_site_spending`, `importance` (1–5), `registration_required`, `registration_status` (`unknown`/`upcoming`/`open`/`full`/`closed`), `limited_offer`, and timezone-aware `registration_deadline`. Invalid date ranges, non-HTTPS/host IP/private sources, credentials in URL, free admission with a positive fee, unsupported keys and oversize inputs fail validation. Date/fee unknown remains unknown, not fake "verified".

URL canonicalization strips tracking query parameters and sorts the remaining query; `identity_key` is SHA-256 of normalized URL + occurrence key. PostgreSQL `ON CONFLICT` updates stable identity atomically, records sanitized batch execution audit in the same transaction, and does not fetch arbitrary source URLs. Cross-URL semantic/event dedup remains ChatGPT upstream responsibility; the backend cannot guarantee that two unrelated URLs describe the same event. The signed-in GET supports `city`, `category`, `starts_from`, `min_importance`, `limit` and `offset` filters.

**Security:** POST requires `Authorization: Bearer <separate connector token>` matching `LIFE_CURATED_INGEST_TOKEN` (minimum 32 characters); missing/misconfigured token fails closed HTTP 503 and invalid token HTTP 401. Never copy a user's Google browser cookies into ChatGPT Tasks. Store the token outside code in an approved secret mechanism. New curated reads default owner-beta via global feature policy; public release requires verified V3 acceptance plus runtime flag `LIFE_CURATED_PUBLIC_ROLLOUT_APPROVED=1` before owner can enable all-user rollout. ChatGPT scheduled connector availability, credentials, integration and live DB readback are NOT VERIFIED.

**Scope boundary:** This is the current implemented direct-write / browse API contract, **not** the future two-entry user API. Its `registration_deadline` is not a registration opening time, and `importance` is not a category. User-specific tracking/calendar/task/reminder endpoints and schema are not implemented; [approved product semantics](curated_activity_user_features.md) must be separately designed and tested. Do not silently extend existing batch fields or imply deployed capabilities.

**Legacy:** Existing GET /api/v1/free-events is verified-only and preserved temporarily for compatibility. Existing Alembic 0011–0014 and previously ingested records remain. No destructive schema deletion, Cloud Run/GCP resource deletion or new source/Queue worker. Tests and acceptance: [P0/P1 consolidated matrix](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md). No second publish/registration gate.

## Dedicated Sheet handoff (approved; implementation gap)

New default input is [台灣活動｜交接資料](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) tab `交接資料` (30 columns), **not** the 45-column `精選活動` tab. Life needs READY/ERROR consumer, permanent event_key/content_hash identity and version-checked ACKED/ERROR writeback. Earlier `spreadsheets.readonly` and URL+occurrence identity cannot satisfy this contract without deliberate source changes. The bearer endpoint remains compatible; new Sheet E2E and production are NOT VERIFIED. See [curated_sheet_job_ingestion.md](curated_sheet_job_ingestion.md).
