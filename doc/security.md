# Life — Current Security & Privacy Contract (2026-10-10)

**Operational source of truth:** GitHub `main` and current runtime, not legacy SQLite mobile assumptions. Current architecture: Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL. Earlier local-first phone/PIN/SQLite notes are historical Git revisions and apply only to a future native offline app when explicitly scoped.

## Auth & ownership

- Authenticate every protected FastAPI API; allow Google Sign-In with verified identity / scoped OAuth where implemented. GoogleConnection and Drive records use `user_sub`; user owns and chooses own Drive/Gmail/Calendar grants and AI document-content consent. Test actual cross-user denial in live E2E before marking multiuser isolation PASS.
- Admin is a distinct backend-enforced permission/allowlist, not a hidden client route or an arbitrary email string. Admin may view sanitized system aggregates, approved source policy, job status, internal Life AI Provider config and UI feature rollout but **not** other users' email, Drive documents, AI prompts, calendar records, OAuth tokens or personal UI preferences.
- Feature rollout policy and personal preferences are separate. Hiding a feature cannot delete stored user data, grant new role/Google scope, disable a background collector by accident, or bypass API permission checks.

## Tokens / secrets / external AI

- Encrypt OAuth credentials in persistence and do not log/export any refresh/access token, API key, database password, private Google document body or service-account credential. Runtime secrets via Secret Manager/GitHub masked settings/short-lived WIF, no long-lived deploy SA JSON keys.
- Life Drive AI provider usage requires user's explicit content-consent (default OFF); admin enabling provider globally never overrides it. Provider responses are untrusted, schema validated and may fail partially; fallback is not evidence that direct primary model passed.
- ChatGPT directly submits selected activity rows through a bounded, separately authorized Life API. Life validates HTTPS provenance, stable dedup and permitted fields, then upserts curated pool. No Life event Queue, source crawler, or user calendar auto-writes. No direct LLM DB access.

## Data / operations

- PostgreSQL schema changes only via Alembic migration, preserve current production records; destructive migration, major IAM change, production credential rotation, force-push/history rewrite or broad production resource deletion require explicit approval.
- Validate original/official source domains and allowlisted access before any background fetch; no anti-bot bypass or crawling EventGo/yii.tw. Protect intake APIs against SSRF, duplicate events, expired leases, stale versions, unbounded batch size and replay.
- Explicit confirmation for destructive user actions (Calendar/Project delete, backup overwrite). Activity logs record sanitized actor/action/request ID and error category, not personal content or credentials.

## Required tests

401/403, owner-vs-user boundaries, Google consent OFF=zero content sent to AI, source license revoke, Queue write isolation, idempotent exact-fingerprint ACK, retained records on feature disable, per-user layout separation, secret redaction and PII-safe logging; confirm tests/CI/deployment/runtime independently. See [PROJECT_RULES.md](PROJECT_RULES.md), [permissions.md](permissions.md), [CURRENT_STATE.md](CURRENT_STATE.md).
