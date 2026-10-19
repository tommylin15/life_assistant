# Gmail Smart Radar V2 — local-only classification

2026-10-19, Asia/Taipei. SOURCE / 4 CI / FIXED STAGING PASS; MODEL / TRUE GMAIL E2E / PRODUCTION NOT VERIFIED.

This V2 decision supersedes the V1 classification and seven-day backfill limits only. Keep user-scoped OAuth, manual scanning, confirmation receipts, no background schedule/push, no auto-writing Tasks/Calendar/Shopping, and no full Gmail body storage.

## Architecture and constraints
- Gmail API -> FastAPI -> explicit local rules -> optional offline multilingual embedding model -> local evidence extraction -> PostgreSQL -> Life UI.
- Gmail-derived content NEVER goes to Gemini, omniAgent or third-party generative models in this scan workflow. There is no silent external fallback.
- The semantic model is optional and is ONLY loaded from an existing local folder configured using GMAIL_RADAR_LOCAL_MODEL_PATH. FastEmbed 0.9.0 loads CPU ONNX with local_files_only=true, verified files and no network on the scan path. In-process initialization and inference are serialized to cap memory.
- The standard production FastAPI image remains intentionally rules-only. Optional backend/Dockerfile.gmail-semantic packages a SHA256-verified Apache-2.0 quantized ONNX model during image build (HuggingFace Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q revision faf4aa4225822f3bc6376869cb1164e8e3feedd0). It MUST NOT fetch a model at Cloud Run startup. The opt-in Docker image passed the offline GitHub Actions container test but is NOT deployed to Life staging or production.
- Offline model acceptance #39276926718: synthetic suite and opt-in Docker passed in a no-network, 1 GiB memory-limited container; test-process peak RSS ~710 MiB, CPU p95 ~7–8 ms. Synthetic cases were used during development, NOT a blind production quality test. Before activating in Cloud Run, verify the existing service memory/CPU, real authorized owner's Gmail recall/false positives, deployment isolation and rollback.
- Local semantic similarity is an uncalibrated screening score, never a proof of urgency, sender authenticity or payment. Uncertain classification yields no automatic alert; semantic hits are labeled as review suggestions.

## API
- Existing 7-day 20-message quick-scan retained for compatibility.
- New POST /integrations/google/gmail/radar/backfill-seven-days enumerates bounded 7-day Gmail IDs (maximum 2,000) and processes 40 unchecked or old-classifier IDs per manual invocation. No scheduler.
- Existing 3-day backfill/recheck remain. Seven-day coverage is kept separate from three-day coverage with explicit count, remaining and complete flags.
- PostgreSQL classifier_version on seen IDs allows legacy false negatives to be revisited without losing existing completed/ignored rows or Life Inbox idempotency receipts.
- Local date parsing permits explicit ISO/Gregorian and clearly marked ROC dates; month/day without a year remains source text, NEVER an invented year. No inference that a charge is paid or that an email is genuine.
- No Gmail body, attachment, or AI prompt is stored or exported; do not log raw subject/snippet. IMPORTANT: the Gmail radar → Life Inbox handoff now supplies authenticated gmail_item_id; /inbox/interpret verifies user_sub and generates a LOCAL task proposal without invoking Gemini. Generic free-text Inbox remains a separate opt-in Gemini route; pasted Gmail text outside the marked handoff cannot be reliably detected automatically.

## Data change
- Alembic 20261019_0022 (additive) adds evidence fields to gmail_radar_items and classifier_version to gmail_radar_seen and seven-day counters to gmail_radar_scan_states. Prior rows and receipts remain untouched.
- Release target and Postgres integration test head need to follow this Alembic head. Destructive downgrade is prohibited.

## Acceptance gates
1. Implementation source and regression tests: source committed, CI to verify.
2. Same-SHA four CI gates including Alembic real Postgres test: PASS, #39271061902, code SHA c4560ce77d3faaefbe31896849181f60ed6da27c.
3. ONNX artifact SHA / offline synthetic quality / 1 GiB isolated Docker smoke: PASS #39276926718. Model deployment, real Gmail quality/generalization and Cloud Run capacity: NOT VERIFIED.
4. Prior rules-only staging #39271510026: PASS for that older SHA. New source requires new same-SHA Staging/0022 DB readback. Actual owner/general-user Gmail and returned classification/DB E2E: NOT VERIFIED.
5. Production promotion, rollback, Hosting readback: NOT VERIFIED; workflow explicitly skipped. No production traffic change.

The staging workflow summary prints legacy alembic=20261012_0018 even though the checked-in migration release target is 20261019_0022. Use the actual runner/DB ledger as authority; do not cite the stale summary as proof of revision. Direct DB 0022 readback is NOT VERIFIED.

No DONE status before matching runtime evidence. Rules-only improvements may be shipped as a PARTIAL subfeature if the semantic checkpoint remains unprovisioned.

## Cross-module safety repair

When a Gmail radar card is sent to Life Inbox, the browser submits an authenticated Gmail item ID. FastAPI reads only that user's persisted item and provides an unselected manual Task proposal; it does not send the originating subject, snippet or derived fields through the existing Inbox Gemini Gateway. Distinct owner/cross-user mock tests assert the Gateway was never invoked. Human real-account E2E remains NOT VERIFIED.
