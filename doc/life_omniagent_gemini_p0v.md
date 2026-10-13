# Life → omniAgent Gateway → Gemini Flash-Lite | P0-V

2026-10-13 narrow cross-project integration. **Current source path is server-side only, read-only and OFF by default.** This is not a migration of Drive AI, activity discovery, personal notes or the existing provider priority/fallback rules.

## Contract and ownership

- Life owns authenticated Google user sessions and derives the existing stable project-scoped \`codex_owner_uuid(user["sub"])\`; the browser cannot select ownerId, project, requestId or model.
- Life \`POST /api/v1/ai/text\` accepts only \`{"prompt":"..."}\`. It performs one explicit, bounded text request. No document read, DB mutation, Drive permission change, cache write, background job, retry or automatic prompt generation. The caller must separately consent under existing Drive AI flows before any Drive contents can be sent; this isolated text endpoint never collects Drive contents.
- A Life Cloud Run backend must **itself** run as \`omniagent-codex-life-client@gen-lang-client-0593591102.iam.gserviceaccount.com\`. Metadata \`email\` is checked for an exact match and \`identity?audience=<canonical Gateway>&format=full\` mints a Google ID token. CI impersonation of the identity does not prove the actual Life runtime has this service account.
- Private Gateway audience: \`https://omniagent-agent-gateway-2oo7qbkd5q-uc.a.run.app\`. A candidate tagged URL may be used only for fenced acceptance, but the token audience is still canonical. Gateway checks its exact service-account-to-\`life-assistant\` mapping and Cloud Run Invoker IAM. No Gemini key in Life.
- Model fixed to \`gemini-3.5-flash-lite\`. Prompt <=8192 UTF-8 bytes; response text nonempty and <=32000 chars. Caller validates \`status=completed\`, ownerId, project, requestId and model. Provider errors and identity mismatches fail closed with sanitized codes; an uncertain timeout is not retried.

## Feature flag and staged validation

- \`GEMINI_GATEWAY_TEXT_ENABLED=false\` by default, including formal production and ordinary staging releases. An explicit candidate override may set it \`true\` with \`GEMINI_GATEWAY_URL\` pointing at the verified omniAgent 0%-traffic pilot; never enable production or change traffic merely because CI passes.
- Non-interactive acceptance: exact SHA four-job CI; immutable GHCR/V3 0%-traffic Life candidate and staging release readback; unauthorized Life endpoint 401 and feature-disabled authorized endpoint 503; real Life runtime identity and ID token; live owner-authorized Life API -> Gateway -> Gemini result (matched IDs and nonempty text), and negative IAM/cross-project tests. Each gate independently PASS / FAIL / NOT VERIFIED.
- This endpoint supplies the smallest text-only API return, **not** a Drive enrichment result or app chat UI. Before routing real Drive documents or persisting outputs, separately verify user consent, bounded context, existing fingerprints/caches, structured schema validation and owner-scoped DB writes. No activity AI belongs here.

## Operational safety

Never publish the Gateway Gemini pilot's tagged revision as normal production routing without Gateway-owned approval; its formal serving revision may still have the route disabled. Do not rewrite the existing V3 release policy, staging Hosting pins, production traffic or OAuth validation. A full end-to-end pass requires a real Life backend-origin signed request and an authenticated Life app/API reply—not a CI-generated IAMCredentials token.

## 2026-10-13 signed smoke dispatch repair

The initial `workflow_run` after an automatically dispatched V3 release did not produce a
Signed Smoke run. The staging release itself was dispatched by GitHub Actions'
`GITHUB_TOKEN`; chaining on its completion is not a dependable bootstrap.
The source of truth is now an **explicit** `workflow_dispatch` from a successful,
non-promoting V3 staging release. The independent smoke checks that V3 source
run is successful and tied to current main/CI, then inspects dedicated runtime
identity, immutable Life image, private 0%-traffic Gateway pilot, and real
Gemini result. One tightly bounded `push` bootstrap can exercise the
already-successful staging release `38363418508` for SHA `20e709a9d151691390f449cea4e5a8be839ef503`;
it must be the immediate parent of the change to run. Later pushes cannot
replay that bootstrap, and neither trigger changes production traffic.
**A dispatched workflow is not evidence of a passing signed smoke.**

