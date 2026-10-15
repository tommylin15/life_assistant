# life_assistant — Documentation index
Updated 2026-10-15 (Asia/Taipei). **GitHub main and runtime evidence govern implementation state; Drive-approved discovery specifications govern exploration design.** Historical documents and older dates never supersede current code/evidence.

| Question | Canonical current reference |
| --- | --- |
| How to develop safely? | [PROJECT_RULES](PROJECT_RULES.md), [AGENTS](../AGENTS.md), [project_boundary](project_boundary.md) |
| What is running/verified? | **[CURRENT_STATE](CURRENT_STATE.md)** |
| What should be worked on next? | **[todo](todo.md)** |
| What could go wrong? | **[Risk register](RISK_REGISTER.md)** |
| What are the product and account rules? | [CURRENT_PRODUCT_ARCHITECTURE](CURRENT_PRODUCT_ARCHITECTURE.md), [decisions](decisions.md), [spec](spec.md) |
| Where is the activity importer contract? | [curated_sheet_job_ingestion](curated_sheet_job_ingestion.md); [exploration/Life boundary](taiwan_free_events_discovery_plan.md) |
| What do users see/do with activities? | [curated_activity_user_features](curated_activity_user_features.md) |
| How are UI and personal settings designed? | [life_navigation_personalization_v2](life_navigation_personalization_v2.md), [ui_visual_system](ui_visual_system.md), [design_system](design_system.md) |
| How is V3 released? | [ci_cd_ghcr_release_policy](ci_cd_ghcr_release_policy.md), [deployment_runbook](deployment_runbook.md), [release_checklist](release_checklist.md) |
| How to test/secure data? | [testing_strategy](testing_strategy.md), [security](security.md), [permissions](permissions.md), [migration_spec](migration_spec.md) |
| Where are prior decisions/acceptances? | [archive](archive/README.md), [acceptance](acceptance.md) |

Other domain-specific references remain in this directory and should be opened only for work affecting that domain. [progress](progress.md) and [phase1_delivery_order](phase1_delivery_order.md) are compatibility navigation links, **not independent status or backlog sources**. The [direct curated API contract](free_events_candidate_ingestion_contract.md) documents an existing **legacy compatibility path**, not the approved Sheet importer.

**Drive boundary:** only `life_assistantGPT` is the approved Drive work area; preserve the six current exploration Markdown specs (README + 01–05), operational sheets, snapshots and append-only daily logs. Historic duplicates are not active instructions.