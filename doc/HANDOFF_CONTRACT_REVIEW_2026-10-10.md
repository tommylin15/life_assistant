# Handoff contract review — 2026-10-10

What this change does: Life follows the actual handoff Sheet rather than requiring the producer to use Life's private hash encoding. It stores source fields, checks unchanged business content in PostgreSQL, writes the specified bare receipts, and displays source details in activity cards.

Looks good. Ship the code; runtime release acceptance remains separate.

Checked the importer, every HandoffItem/upsert caller, database model and unique key, personal Calendar payloads, both activity-card consumers, fixtures and PostgreSQL concurrency tests. Same-key imports use a transaction lock and a durable unique key. Same hash with changed business content is rejected. All ACKED rows still verify the database. Unknown costs and date-only registration times remain unknown or date-only; reminders cannot invent midnight. No source business data, source hash or exploration document was changed.

The daily workflow reuses the production revision's verified immutable GHCR image, WIF and existing Job. It shares the release lock. It stays disabled until LIFE_CURATED_HANDOFF_ENABLED=true is set after real acceptance and production promotion, so the old production importer cannot run against the new Sheet automatically.

Validation: backend 535 tests OK, 19 environment-dependent tests skipped; focused importer/actions 17 tests PASS after fixture correction; Flutter card 3 tests PASS; targeted Flutter analyze has no issues; workflow YAML parses and extracted shell passes bash -n; git diff --check PASS.

Expected load: one fixed outbox, at most 1000 rows, daily or manually triggered. No new dependency, paid resource, schema change or authentication bypass was added.

Not checked: current-diff CI PostgreSQL tests, real Job apply/ACK, new-version external Chrome acceptance and production promotion. Google Sheets has no atomic conditional cell write; concurrent source row movement can produce PARTIAL and requires the next import to recheck the database and repair receipts.
