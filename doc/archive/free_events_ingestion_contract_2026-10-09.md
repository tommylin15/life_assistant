# Free / High-value event candidate ingestion contract (2026-10-09)

Status: DESIGN / NOT DEPLOYED. This is an additive contract for implementation; it does not imply a live endpoint.

## Existing integration points
- PostgreSQL Alembic 20261009_0011–0013: free_event_sources, organizers, events, sessions, registration_opportunities, evidence, ingestion_leases, source_observations.
- backend/app/services/free_events_ingest.py: transactional deduplication and source authorization checks.
- GET /api/v1/free-events: verified-only read endpoint; do not weaken its existing trust gate.
- ChatGPT scheduled discovery is transitional and has no authenticated direct database write capability.

## New write endpoint (implementation target)
POST /api/v1/internal/free-events/candidates:batch
- Machine-to-machine authenticated identity with explicit ingest role; never public, never accept caller-provided verified=true.
- Bounded <=100 events per request; JSON schema validation, HTTPS canonical original URLs, source registry allowlist, rate limits, audit IDs, idempotency key.
- Upsert via existing ingestion service, not direct task/calendar/note APIs. Return accepted/duplicate/rejected IDs and reasons. Unverified candidates remain internal until independently verified.
- Require source URL, organizer/official URL where available, retrieved_at, event/session date, provenance and evidence; missing registration times remain null.
- Never enable fetching a source whose terms/license have not been reviewed. Never assume an external ChatGPT task can directly call a private Cloud Run API.

## Value model (additive migration required)
- payment_required_twd, refundable_deposit_twd, refund_conditions, nonrefundable_cost_twd, guaranteed_benefit_value_twd, benefit_valuation_basis, valuation_verified_at, value_ratio, value_assessment_status.
- Only guaranteed redeemable benefits with independently verifiable comparable prices count. Exclude sweepstakes and conditional coupons without certain redemption.
- High value iff nonrefundable_cost_twd > 0 and guaranteed_benefit_value_twd >= 3 * nonrefundable_cost_twd, and valuation evidence is verified. Free candidates follow existing rules.
- Do not use existing free-only verification constraints to mislabel paid opportunities as free; extend the schema and read API explicitly.

## Required tests and release gates
1. Migration additive and reversible; existing free records unchanged.
2. Authentication 401/403, source license deny, malformed URL, duplicate and concurrent upsert, repeated scans, no fabricated price/registration times.
3. Guaranteed value boundary 299/100 fails, 300/100 passes; refundable deposit tracked separately; service fee included.
4. No calendar/task/note mutation or personal notifications; only shared candidate tables.
5. CI, production migration, live API write/readback, Flutter paid/free cards, scheduler integration all require separate evidence before PASS.

## Delivery decision
Preferred durable pipeline: reviewed source adapter -> authenticated Cloud Run batch -> PostgreSQL -> verified-only read API -> Flutter. ChatGPT 06/18 task remains a discovery-only transitional channel until authenticated bridge ingestion is actually available. Never claim scheduled ChatGPT outputs automatically reached life_assistant before live readback.

## 2026-10-10 — Internal queue implementation vs external write API

An internal reviewed-source normalized candidate queue has been implemented at `free_event_candidate_queue` (Alembic 0014) and connected to the official Ministry of Culture batch; deterministic normalization and PostgreSQL catalog ingestion remain the only execution path for that source. This is **not** the separately planned authenticated `POST /api/v1/internal/free-events/candidates:batch` endpoint. That endpoint, TDX and aggregator authorization/ingestion, high-value paid opportunity expansion and live production queue readback remain separate work. No public write method or AI escalation is enabled as part of P0–P2.
