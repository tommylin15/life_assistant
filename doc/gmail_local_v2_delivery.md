# Gmail Smart Radar V2 — local-only classification

2026-10-20, Asia/Taipei. RULES API CI/STAGING + DB GATE PASS; ISOLATED PRIVATE ONNX CLOUD RUN CANDIDATE / CLOUD RUN SYNTHETIC JOB / IAM READBACK PASS. Gmail-authenticated Life Staging E2E, ONNX-in-Life API cutover and production release NOT VERIFIED.

This V2 decision supersedes the V1 classification and seven-day backfill limits only. Keep user-scoped OAuth, manual scanning, confirmation receipts, no background schedule/push, no auto-writing Tasks/Calendar/Shopping, and no full Gmail body storage.

## Architecture and constraints
- Gmail API -> FastAPI -> explicit local rules -> optional offline multilingual embedding model -> local evidence extraction -> PostgreSQL -> Life UI.
- Gmail-derived content NEVER goes to Gemini, omniAgent or third-party generative models in this scan workflow. There is no silent external fallback.
- The semantic model is optional and is ONLY loaded from an existing local folder configured using GMAIL_RADAR_LOCAL_MODEL_PATH. FastEmbed 0.9.0 loads CPU ONNX with local_files_only=true, verified files and no network on the scan path. In-process initialization and inference are serialized to cap memory.
- The standard production FastAPI image remains intentionally rules-only. Optional backend/Dockerfile.gmail-semantic packages SHA256-verified Apache-2.0 quantized ONNX during image build (Qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q revision faf4aa4225822f3bc6376869cb1164e8e3feedd0), without runtime model download. This ONNX image IS deployed to an isolated private synthetic-only Cloud Run canary, NOT to the user-facing Life staging/production FastAPI service.
- Offline model acceptance #39276926718: synthetic suite and opt-in Docker passed in a no-network, 1 GiB memory-limited container; test-process peak RSS ~710 MiB, CPU p95 ~7–8 ms. Actual Cloud Run runtime acceptance now PASS in isolated 2Gi/2vCPU synthetic-only candidate + Job #39349455587. Synthetic cases were used during development, NOT a blind real Gmail quality test. Before integrating into Life user-facing staging, validate real authorized owner's Gmail recall/false positives, full FastAPI memory and latency, and rollback.
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
1. Implementation and regression tests: PASS at source SHA 3ad6b7768642fb8580027aa5460c5d2b4430d62f.
2. Same-SHA four CI gates (backend, Flutter, PostgreSQL, deployment scripts): PASS [#39278270473](https://github.com/tommylin15/life_assistant/actions/runs/39278270473), source SHA 3ad6b7768642fb8580027aa5460c5d2b4430d62f.
3. ONNX model hash, offline runner + isolated container: PASS #39276926718; independent GCP candidate service 2Gi/2vCPU/private internal ingress/1 concurrency and Cloud Run Job: PASS #39349455587; follow-up IAM check: PASS #39350332042. User-facing Life API ONNX integration and real Gmail generalization: NOT VERIFIED.
4. Same-SHA staging [#39343836610](https://github.com/tommylin15/life_assistant/actions/runs/39343836610): PASS for Hosting version/static SHA, API unauthorized-401, OAuth callback, and fail-closed read-only Gmail V2 schema acceptance Job step (checks Alembic 20261019_0022, three tables/columns, per-user message unique constraint). The job runner exit is verified, not a raw SQL result included in the workflow log. Fixed hosting version sites/life-assistant-v3-stage-tl15/versions/433b1bc1b2014576. Real owner/general-user Gmail + result DB E2E: NOT VERIFIED.
5. Production promotion, rollback, Hosting readback: NOT VERIFIED; workflow explicitly skipped. No production traffic change.

The migration workflow step label still says 'Apply additive 0018' (historical label), but migration runner target and new read-only DB acceptance script check Alembic 20261019_0022. DB validation Job step PASS in #39343836610; do not infer a full SQL transcript from the job's success status.

No DONE status before matching runtime evidence. Rules-only improvements may be shipped as a PARTIAL subfeature if the semantic checkpoint remains unprovisioned.

## Cross-module safety repair

When a Gmail radar card is sent to Life Inbox, the browser submits an authenticated Gmail item ID. FastAPI reads only that user's persisted item and provides an unselected manual Task proposal; it does not send the originating subject, snippet or derived fields through the existing Inbox Gemini Gateway. Distinct owner/cross-user mock tests assert the Gateway was never invoked. Human real-account E2E remains NOT VERIFIED.

## 2026-10-20 Cloud Run private ONNX candidate acceptance

**Scope boundary:** This is NOT a life-assistant-api revision and has no Gmail API, OAuth, user input, database or external Gemini access. Service life-assistant-gmail-onnx-candidate serves internal synthetic/health endpoints only. The service routes 100% of its OWN private traffic, but 0% of the real Life API production traffic.

- Same-SHA four CI checks: [#39349455453](https://github.com/tommylin15/life_assistant/actions/runs/39349455453) PASS, source SHA b3ea92b6e11865d82887d4aa6a16b00285a63553.
- Private candidate workflow: [#39349455587](https://github.com/tommylin15/life_assistant/actions/runs/39349455587) PASS. Revision life-assistant-gmail-onnx-candidate-00002-l9b; 2GiB RAM, 2 vCPU, concurrency=1, min instances=0, max instances=1, ingress=internal. Verified revision's GHCR digest sha256:f69b3f84cf10f829de8fe4e6522c388ebcd8f7b5e5944b9150e490b9e4543c31.
- Actual isolated Cloud Run Job life-assistant-gmail-onnx-smoke-57qqm: PASS. Executed same pinned digest with 2Gi/2vCPU; synthetic quality/performance gate and process exit successful. Exact Cloud Run process RSS/p95 have NOT yet been independently read from Job logs into this document; GitHub runner synthetic baseline ~710MiB.
- Same workflow verified original Life production service's nonzero weighted traffic revision/percent before/after: PASS/unchanged. First attempt [#39348720730](https://github.com/tommylin15/life_assistant/actions/runs/39348720730) FAILED on overly strict comparison of unrelated zero-percent tags; model and Cloud Run smoke had both passed. Corrected weighted comparison passed.
- Deploy logged a warning when setting IAM policy, even though service creation succeeded. Separate read-only [IAM/ingress audit #39350332042](https://github.com/tommylin15/life_assistant/actions/runs/39350332042) PASS: internal ingress, invoker IAM check enabled, no allUsers or allAuthenticatedUsers Invoker binding, external unauthenticated probe was not HTTP 200. No existing IAM binding was changed by the audit.
- No scheduled ONNX inference, no personal Gmail processed, no production Life deployment, no public endpoint and no external Gemini escalation.
- **Private candidate deployment + Cloud Run synthetic execution + IAM privacy = DONE. Entire Gmail V2 feature = PARTIAL.**

### Required before entire Gmail V2 can be called DONE

1. **P0 user-facing Staging integration:** deploy ONNX-enabled full Life FastAPI as a digest-pinned 0%-production-traffic candidate, preserve authentication, test full FastAPI CPU/startup/RSS/p95, fallback, rollback.
2. **P0 real Gmail E2E:** authenticated Owner and general user on Staging: seven-day batches, past false negatives, settled/no-action mails, evidence dates, completed/ignored dedupe, Gmail-to-Inbox local-only, cross-user isolation. Never publish real mail content to logs or GitHub.
3. **P1 production:** same SHA CI, real Staging E2E, live revision/digest and rollback rehearsal, controlled promotion and matching Hosting SHA, real user readback.
4. **Separate governance:** past real-mail fields may still be present in public Git commit history. Current tests are synthetic. Rewriting main history is destructive and requires explicit user approval; no history rewrite was attempted.

