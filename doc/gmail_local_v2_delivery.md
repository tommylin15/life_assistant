# Gmail Smart Radar V2 — local-only classification

2026-10-19, Asia/Taipei. SOURCE / 4 CI / FIXED STAGING PASS; MODEL / TRUE GMAIL E2E / PRODUCTION NOT VERIFIED.

This V2 decision supersedes the V1 classification and seven-day backfill limits only. Keep user-scoped OAuth, manual scanning, confirmation receipts, no background schedule/push, no auto-writing Tasks/Calendar/Shopping, and no full Gmail body storage.

## Architecture and constraints
- Gmail API -> FastAPI -> explicit local rules -> optional offline multilingual embedding model -> local evidence extraction -> PostgreSQL -> Life UI.
- Gmail-derived content NEVER goes to Gemini, omniAgent or third-party generative models in this scan workflow. There is no silent external fallback.
- The semantic model is optional and is ONLY loaded from an existing local folder configured using GMAIL_RADAR_LOCAL_MODEL_PATH. SentenceTransformer uses offline mode, local_files_only and trust_remote_code=false.
- The production FastAPI image does NOT ship SentenceTransformers or model assets. For a benchmark-only offline runner, install backend/requirements-local-semantic.txt and supply an approved, revision-pinned multilingual checkpoint on disk. Until provisioned, the scan runs safe rules-only and cannot be advertised as semantic AI delivered.
- Before provisioning model to Cloud Run, record model license, SHA, benchmark quality with deidentified/hypothetical Traditional Chinese and English messages, p95, startup memory, concurrency and cost. Never fetch a checkpoint at the first user request.
- Local semantic similarity is an uncalibrated screening score, never a proof of urgency, sender authenticity or payment. Uncertain classification yields no automatic alert; semantic hits are labeled as review suggestions.

## API
- Existing 7-day 20-message quick-scan retained for compatibility.
- New POST /integrations/google/gmail/radar/backfill-seven-days enumerates bounded 7-day Gmail IDs (maximum 2,000) and processes 40 unchecked or old-classifier IDs per manual invocation. No scheduler.
- Existing 3-day backfill/recheck remain. Seven-day coverage is kept separate from three-day coverage with explicit count, remaining and complete flags.
- PostgreSQL classifier_version on seen IDs allows legacy false negatives to be revisited without losing existing completed/ignored rows or Life Inbox idempotency receipts.
- Local date parsing permits explicit ISO/Gregorian and clearly marked ROC dates; month/day without a year remains source text, NEVER an invented year. No inference that a charge is paid or that an email is genuine.
- No Gmail body, attachment, or AI prompt is stored or exported; do not log raw subject/snippet.

## Data change
- Alembic 20261019_0022 (additive) adds evidence fields to gmail_radar_items and classifier_version to gmail_radar_seen and seven-day counters to gmail_radar_scan_states. Prior rows and receipts remain untouched.
- Release target and Postgres integration test head need to follow this Alembic head. Destructive downgrade is prohibited.

## Acceptance gates
1. Implementation source and regression tests: source committed, CI to verify.
2. Same-SHA four CI gates including Alembic real Postgres test: PASS, #39271061902, code SHA c4560ce77d3faaefbe31896849181f60ed6da27c.
3. Optional local semantic checkpoint installed, accuracy / p95 / RAM measurements: NOT VERIFIED.
4. Staging SHA / static Hosting / API 401 / OAuth redirect / migration runner: PASS, #39271510026. Actual owner/general-user Gmail and returned classification/DB E2E: NOT VERIFIED.
5. Production promotion, rollback, Hosting readback: NOT VERIFIED; workflow explicitly skipped. No production traffic change.

The staging workflow summary prints legacy alembic=20261012_0018 even though the checked-in migration release target is 20261019_0022. Use the actual runner/DB ledger as authority; do not cite the stale summary as proof of revision. Direct DB 0022 readback is NOT VERIFIED.

No DONE status before matching runtime evidence. Rules-only improvements may be shipped as a PARTIAL subfeature if the semantic checkpoint remains unprovisioned.
