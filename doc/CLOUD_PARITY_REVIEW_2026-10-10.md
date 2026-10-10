# /ponytail-review — cloud parity acceptance

What this change does: The isolated core CRUD runner no longer depends on admin
rollout choices for Projects, Notes, Habits and Shopping. It keeps real routes,
PostgreSQL writes and exact-ID cleanup. User-facing policy enforcement is unchanged
and remains a separate real-browser acceptance requirement.

Root cause evidence: execution `life-assistant-core-acceptance-lhb9z` returned
HTTP 403 on Note A creation. Read-only execution `life-assistant-core-acceptance-5ckfw`
and external Chrome admin readback confirmed notes `enabled/owner` and habits
`hidden/all`. No feature policy rows were changed.

Checked: runner callers in release workflows; four scoped dependency overrides;
exception cleanup; no authentication override outside this isolated test process;
HTTP diagnostics omit response bodies; no DB schema or application route change.
Expected load is one release runner per serialized release.

Validation: full backend suite 532 tests PASS, 19 PostgreSQL cases skipped locally;
focused runner and rollout regression suite 16 PASS after final scope restriction.

Looks good. Ship.

Follow-up /ponytail-review: CI 38043827949 exposed newer FastAPI lazy included
routers. Replace route introspection with the same four explicitly registered
gate references from `app.main`; core router authorization remains unchanged.
Updated three route contract fixtures. Focused runner, feature gate, Notes,
Habits, Shopping and confirmation-policy suite: 69 PASS. Checked the final diff
and identity cleanup after failure. Verdict: Ship.

Not checked: corrected runner in the release image, current-SHA real browser and
production acceptance remain pending and must not be inferred from unit tests.
