# Life Direct ChatGPT → Curated Pool API (2026-10-10)

**PROPOSED API, NOT YET IMPLEMENTED.** See [activity scope](taiwan_free_events_discovery_plan.md). Queue and source-crawler APIs are cancelled.

| Proposed endpoint | Responsibility |
|---|---|
| POST /api/v1/free-events/curated:batch | Approved ChatGPT caller submits selected activities only; backend validates, dedups and upserts into curated pool. No Queue reference, no selected/skip ACK. |
| GET /api/v1/free-events/curated | Authenticated users browse selected entries, basic filter, link to original source and unknown fee/date labels. |

Minimum input: stable source/original HTTPS URL, title, optional category, city, datetime or date, fee and terms (unknown allowed), short description. Bound batch size, field size, strict schema; reject invalid URL and unsupported write credentials. Canonical identity must be stable across retry; use unique key/upsert transaction rather than blindly inserting. Log sanitized batch/run metadata, never private secrets.

**Security:** Use app/connector-specific authenticated writer with least privilege, not open POST or copy user Google cookies into ChatGPT tasks. ChatGPT scheduled connector availability, credentials, integration and live DB readback are NOT VERIFIED.

**Legacy:** Existing GET /api/v1/free-events is verified-only and preserved temporarily for compatibility. Existing Alembic 0011–0014 and previously ingested records remain. No destructive schema deletion, Cloud Run/GCP resource deletion or new source/Queue worker. No second publish/registration gate.