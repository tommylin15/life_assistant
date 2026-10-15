# life_assistant

Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL.

**Current implementation and releases:** [GitHub main](https://github.com/tommylin15/life_assistant) and exact-SHA GitHub Actions/runtime evidence. Documents describe rules or snapshots, not automatic proof of completed deployment.

## Start here

- [Current state and evidence](doc/CURRENT_STATE.md) — last verified SHA, separate CI/deployment/runtime outcomes and remaining gaps.
- [Active TODO](doc/todo.md) — only active execution priorities; previous batch plans are historical.
- [Risk register](doc/RISK_REGISTER.md) — ranked engineering, security, integration and operating risks.
- [Documentation index](doc/README.md) — governing rules, product contracts and archived history.
- [Project rules](doc/PROJECT_RULES.md) · [V3 release policy](doc/ci_cd_ghcr_release_policy.md) · [Deployment runbook](doc/deployment_runbook.md).

**Activity data:** Drive curated pool → independent handoff Sheet → scheduled Life GCP importer Job → PostgreSQL → Flutter; the older direct-write bearer API remains a compatibility endpoint, **not** the canonical importer. Discovery/source crawling belongs to Drive exploration, not Life's backend. See [handoff contract](doc/curated_sheet_job_ingestion.md) and [user-facing activity features](doc/curated_activity_user_features.md).

No historical green check transfers to a later SHA. User-facing OAuth login E2E is no longer a mandatory manual release gate, but automated OAuth redirect/session checks remain mandatory.