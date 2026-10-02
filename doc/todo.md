# life_assistant — Active TODO

最後更新：2026-10-02

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #2 — Project-wide Design System / UI Style Checkpoint

狀態：**IN PROGRESS — read-only design audit / direction checkpoint**。

目前 gate：

- 核准單一全站視覺 source of truth；目前 `doc/design_system.md` 定義 Warm Knowledge，但 `app_theme.dart` 同時保留未使用的 `AppTheme.clean`，需消除雙軌漂移。
- 將 color / typography / spacing / radius 擴充成可實際驅動產品 UI 的 token baseline。
- 補 responsive / layout tokens；目前 App Shell 使用 `840` breakpoint、Tasks 使用 `720`，頁面 spacing / max-width 仍有局部硬編碼。
- 定義共用 component baseline：buttons、inputs、cards、chips/tags、dialogs/bottom sheets、loading/empty/error states、navigation。
- 固定 mobile / desktop acceptance 規則與最低可存取性要求。
- 設計 checkpoint 核准後，才進 implementation / adoption；不先逐頁零散美化。

## Just Closed

### #1 — Finish Task 6：shared Drive / Notes Tag system

狀態：**DONE / PASS**。

封板 evidence：

- Notes production UI E2E GREEN，含雙向 link / unlink。
- Project↔Drive Runtime Acceptance #12 GREEN。
- release SHA `9a540a55baaf32a33e7376cab4183f998f596685`。
- CI #450 PASS。
- Deploy Cloud Run #322 PASS。
- Drive closure tracker 已更新為 `1/11 = 9.1%`。

## Next

1. #3 — Task 7：provider-agnostic AI enrichment。
2. #4 — Task 8：智能整理 review UI。
3. #5 — Task 9：Drive Knowledge production delivery + acceptance。
4. #6–#9 — Habits / Shopping / Calendar / Activity + Integrations productization。
5. #10 — Integration / foundation tail closure。
6. #11 — Phase 1 final Release Gate / 封板 checkpoint。

## Non-blocking backlog

以下仍需完成，但只有在成為直接 dependency 或進入對應工作包時才提升優先級：

- Attachment central storage/reference strategy。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。

## Product DONE 規則

使用者功能至少要依工作包需求具備：

1. implementation
2. tests
3. CI
4. deployment
5. runtime / integration
6. UI entry + 可操作 flow
7. mobile / desktop UX acceptance

Backend-only PASS 可標 foundation PASS，但不能等同產品功能 DONE。
