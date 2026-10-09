# Life — Coding Rules (2026-10-10)

1. Read [AGENTS.md](../AGENTS.md) and [PROJECT_RULES.md](PROJECT_RULES.md) before modifying Life. Never load or apply forbidden Superpowers skills. Implement only currently approved scope; conflicts follow user decisions, actual code/runtime and [decisions.md](decisions.md).
2. Use existing Flutter Material 3 design tokens and Riverpod/go_router where currently appropriate. UI interacts with **FastAPI through API clients/repositories**, not directly with PostgreSQL, SQLite DAOs, Google API or secret storage.
3. FastAPI validates user identity/owner/admin roles, schema, source permission, per-user consent and idempotency. Treat provider/model and ChatGPT outputs as untrusted; no AI final permission or numeric publication authority.
4. Versioned Alembic for schema changes; no production data drop or fake timestamps. Preserve `user_sub` tenant isolation, request/execution logs with no raw secrets/private content, verified error semantics and safe rollback.
5. GitHub Actions main push runs CI; audited V3 full-SHA release uses public GHCR digest, 0% candidate, real migrations, auth/readiness and Preview/production gates. Do not use old Cloud Build V2 for new deployment.
6. Check existing callers before changing a shared contract; add bounded backend, PostgreSQL and Flutter regression tests for affected behavior. Avoid decorative abstraction layers, silent fallback, unbounded crawling/model calls and fabricated PASS results.

**Definition of Done**: implementation + tests + CI + deployment + runtime/integration evidence required by the change, with **PASS / FAIL / NOT VERIFIED** per layer; missing mandatory evidence means PARTIAL. Update [CURRENT_STATE.md](CURRENT_STATE.md), [acceptance.md](acceptance.md) and [todo.md](todo.md) when facts actually change. Do not alter non-Life projects.
