# life_assistant

**Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL.** GitHub `main` is the current code and release source of truth. Cloud deployment uses GitHub Actions → public GHCR immutable digest → Cloud Run V3, with each production release independently validated.

## Documentation

- **[Project document index](doc/README.md)** — canonical navigation.
- **[Current state and exact PASS/FAIL evidence](doc/CURRENT_STATE.md)** — current source/runtime PASS/FAIL/NOT VERIFIED.
- **[Approved product architecture](doc/CURRENT_PRODUCT_ARCHITECTURE.md)** — direct ChatGPT → curated pool; planned independent 限時機會／活動探索 user entries, Life AI admin and per-user navigation.
- [Project rules](doc/PROJECT_RULES.md) · [Delivery order](doc/phase1_delivery_order.md) · [Active TODO](doc/todo.md) · [Acceptance ledger](doc/acceptance.md).
- [V3 release policy](doc/ci_cd_ghcr_release_policy.md) · [Deployment runbook](doc/deployment_runbook.md).

The direct curated API, shared Flutter curated list, administrative feature rollout and customized Home/nav have a **source implementation baseline**; staging/production/runtime acceptance is not implied. The newly approved [two activity user features](doc/curated_activity_user_features.md) and their task/calendar/reminder actions are **design only**. Life no longer operates event collectors, MoC/TDX sources, Queue or official-site Excel; ChatGPT submits curated events directly via authenticated API. Do not crawl EventGo or yii.tw. Historical checkpoints, old Cloud Build policies and legacy Bridge designs are archived under [doc/archive/](doc/archive/README.md); forbidden Superpowers drafts were removed from the current working tree but remain in Git history.
