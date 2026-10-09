# life_assistant — Documentation Index

**Updated 2026-10-10**. This is the only current documentation entrypoint. GitHub implementation / CI / deployment / runtime evidence outrank historic document assertions. Only the following documents are active; all point-in-time checkpoints / old V2 plans are in [archive](archive/README.md).

## Start here

| Purpose | Authoritative active document |
|---|---|
| Governance, project boundaries | [PROJECT_RULES.md](PROJECT_RULES.md), [project_boundary.md](project_boundary.md) |
| Current observable status & known FAIL | [CURRENT_STATE.md](CURRENT_STATE.md), [acceptance.md](acceptance.md) |
| Current approved product / privacy / UI | [CURRENT_PRODUCT_ARCHITECTURE.md](CURRENT_PRODUCT_ARCHITECTURE.md), [decisions.md](decisions.md) |
| Next work only | [phase1_delivery_order.md](phase1_delivery_order.md), [todo.md](todo.md), [progress.md](progress.md) |
| V3 deployment, staging, release checklist | [ci_cd_ghcr_release_policy.md](ci_cd_ghcr_release_policy.md), [deployment_runbook.md](deployment_runbook.md), [release_checklist.md](release_checklist.md) |

## Active detail, read only when needed

- Product & UI: [spec.md](spec.md), [ui.md](ui.md), [design_system.md](design_system.md), [design_system_checkpoint_v0_2.md](design_system_checkpoint_v0_2.md), [future_product_enhancements.md](future_product_enhancements.md).
- Architecture, engineering & data: [architecture.md](architecture.md), [project_structure.md](project_structure.md), [data_model.md](data_model.md), [migration_spec.md](migration_spec.md), [error_handling.md](error_handling.md), [security.md](security.md), [permissions.md](permissions.md), [testing_strategy.md](testing_strategy.md), [coding_rules.md](coding_rules.md).
- Google, AI and Bridge: [integrations.md](integrations.md), [ai_provider_policy.md](ai_provider_policy.md) (the old SQLite-first Bridge/sync designs are in archive).
- Activities (ChatGPT direct write only): [taiwan_free_events_discovery_plan.md](taiwan_free_events_discovery_plan.md), [free_events_candidate_ingestion_contract.md](free_events_candidate_ingestion_contract.md), [GitHub #10](https://github.com/tommylin15/life_assistant/issues/10).
- Admin internal AI: [GitHub #11](https://github.com/tommylin15/life_assistant/issues/11); feature rollout, individual navigation and Home: [GitHub #12](https://github.com/tommylin15/life_assistant/issues/12).
- Infrastructure asset history: [v3_cleanup_and_cutover_inventory.md](v3_cleanup_and_cutover_inventory.md); [historical document archive](archive/README.md).

Do not maintain parallel completion counts or old CI/CD policies here. The actual code/runtime remain source of truth; Drive `life_assistantGPT` is separate formally approved governance/research, not current runtime proof. Archived documents do not become current instructions just because linked.
