# life_assistant 文件索引與治理

最後更新：2026-09-28

> 這份文件是 `doc/` 的入口與角色說明。它不取代 implementation/runtime evidence；目前程式、API、schema、migration、CI/CD、deployment、infra、bug 與實際完成狀態仍以 GitHub `main` + runtime evidence 為 Source of Truth。

## 建議閱讀順序

1. `PROJECT_RULES.md`：專案治理、Source of Truth、完成判定與高風險操作。
2. `decisions.md` + `project_boundary.md`：已確認架構方向與 life_assistant / omniAgent 邊界。
3. `phase1_delivery_order.md`：**目前唯一的後續執行順序來源**。
4. `acceptance.md`：各功能目前 PASS / FAIL / NOT VERIFIED 與 evidence。
5. `release_checklist.md`：Phase 1 Release Gate。
6. 需要特定領域細節時，再讀 architecture / data / migration / integration / UI / security 等專題文件。

## 文件角色

### A. 治理與決策 — 長期有效

- `PROJECT_RULES.md`：最高層專案治理規則。
- `decisions.md`：已確認產品與架構決策。
- `project_boundary.md`：life_assistant / omniAgent 責任邊界。
- `coding_rules.md`：開發規則與 Definition of Done。
- `permissions.md`、`security.md`：權限、安全、隱私與敏感操作規則。

### B. 現況、順序與 Release Gate — 日常最常讀

- `phase1_delivery_order.md`：目前執行順序；若 `todo.md` / `wbs.md` 的排列不同，以本檔為準。
- `acceptance.md`：目前驗收狀態與 evidence truth。
- `release_checklist.md`：Phase 1 最終 release gate。
- `todo.md`：精簡 active backlog；只鏡射目前執行重點，不再維護另一套優先順序。
- `progress.md`：人類可快速閱讀的進度摘要；詳細 run / revision / runtime evidence 不重複抄寫，以 `acceptance.md` 為準。
- `wbs.md`：工作範圍分解，不是排程，也不是目前執行順序。

### C. 產品、架構與資料規格

- `spec.md`：產品與功能規格。
- `architecture.md`：系統架構與模組邊界。
- `project_structure.md`：Flutter Web / Backend 專案結構。
- `data_model.md`：目標資料模型。
- `migration_spec.md`：SQLite → PostgreSQL migration 規格。
- `sync_spec.md`：既有/未來同步行為與資料交換規格。
- `error_handling.md`：錯誤語意與 API error contract。
- `testing_strategy.md`：測試策略。

### D. UI / Product UX

- `ui.md`：UI 流程與畫面需求。
- `design_system.md`：設計系統與視覺/互動規範。
- `future_product_enhancements.md`：Phase 1.5 / Phase 2 候選能力；不得自動變成 Phase 1 blocker。

### E. Integrations / Bridge / MCP

- `integrations.md`：Google / Drive / Bridge / MCP 整合總覽。
- `bridge_schema.md`：既有 Bridge schema / compatibility reference；若與目前 Backend/API contract 或最新治理文件衝突，以目前 implementation + `PROJECT_RULES.md` / `project_boundary.md` / `decisions.md` 為準。

### F. 專案批次與驗收歷史

以下文件保留可追溯 evidence，但不作為新的執行順序來源：

- `cloud_domain_parity_design.md`
- `cloud_domain_parity_progress.md`
- `sqlite_postgres_backfill_progress.md`
- `ci_cd_artifact_strategy.md`

`cicd_artifact_strategy.md` 為舊重複檔名，已改成 redirect/stub；CI/CD artifact 策略只維護 `ci_cd_artifact_strategy.md`。

## 文件優先層級

發生衝突時依下列規則處理：

1. **目前 implementation / runtime evidence**：GitHub `main`、CI、deployment、runtime、integration evidence。
2. **治理 / approved direction**：`PROJECT_RULES.md`、`decisions.md`、`project_boundary.md`。
3. **目前執行順序**：`phase1_delivery_order.md`。
4. **完成判定**：`acceptance.md`、`release_checklist.md`。
5. **領域規格**：architecture / data / migration / integration / UI / security 等專題文件。
6. **歷史進度/批次文件**：只用來追溯，不得覆蓋較新的實作或決策。

如果文件與 GitHub/runtime 不一致：指出差異、更新文件；不得用文件文字覆蓋實際實作狀態。

## 維護規則

- 新的開發順序只更新 `phase1_delivery_order.md`，不要再在多個文件維護不同順位。
- 新的 runtime evidence 優先回寫 `acceptance.md`；`progress.md` 只維護摘要。
- `todo.md` 只保留目前 active / next / non-blocking backlog，不再長期累積歷史完成清單。
- WBS 只描述 scope decomposition，不承擔狀態與優先順序。
- 已完成的大型批次可保留獨立 progress/evidence 文件，但必須在標題或開頭明確標示其用途。
- 不因文件整理刪除仍具稽核價值的歷史 evidence。
- `docs/superpowers/` 為歷史內容，不是本專案目前的 active engineering workflow。
