# life_assistant — Active TODO

最後更新：2026-10-02

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #3 — Task 7：provider-agnostic AI enrichment

狀態：**NOT VERIFIED — READY NEXT（NOT STARTED）**。

目前 gate：

- 先以 GitHub `main` 盤點既有 AI/provider abstraction、privacy / consent / cache 與 Notes / Tag linkage 契約，不假設 Drive 規格已實作。
- 以 TDD 固定 provider-agnostic backend contract，避免 UI 或 domain code 綁死單一模型供應商。
- 完成智能 Tag、候選 Notes、雙鏈建議所需的 domain / API / persistence 契約。
- 明確處理 privacy、consent、cache、provider failure / partial-success semantics。
- backend tests、CI 與必要 runtime evidence GREEN 才能進下一 gate。
- 若 Task 7 需要新增 UI，直接使用已封板的 Warm Knowledge tokens / shared components / responsive contract，不另開第二套視覺規則。

## Just Closed

### #2 — Project-wide Design System / UI Style Checkpoint

狀態：**DONE / PASS**。

封板 evidence：

- Warm Knowledge 已成為單一正式視覺基線。
- Drive `life_assistant Design System — Final UI Reference` 已實際保存 Home / Dashboard、Tasks、Project 三張完工樣板。
- release SHA `567511c62fb70b0d8c40b54e2a9d0f4500bcfcf9`。
- semantic tokens：spacing、radius、breakpoints/window classes、layout、motion、44px touch target。
- shared components：`AppPageFrame`、`AppSectionCard`、`AppStatusChip`、`AppStatePanel`。
- responsive contract：`<600` compact、`600–839` medium、`840–1199` expanded、`>=1200` roomy；page actions `720`；content max width `1040`。
- CI #459 / run `36985802044` PASS：backend、Flutter Analyze/Test/Web build、branding verify 全 PASS。
- Firebase Hosting #277 / run `36986034878` PASS：Hosting verify、Task production acceptance、Project production acceptance PASS。
- Deploy Cloud Run #329 / run `36985912899` PASS：migration、deploy、health/readiness、cloud-domain、Checklist、idempotency、Google provider failure-path、SQLite success/failure、image retention 全 PASS。
- `progress.md` closure commit：`43fddeb504dc307ec0299bf796f102b9ec623278`；全案封板進度提升為 `2/11 = 18.2%`。

## Next

1. #4 — Task 8：智能整理 review UI。
2. #5 — Task 9：Drive Knowledge production delivery + acceptance。
3. #6–#9 — Habits / Shopping / Calendar / Activity + Integrations productization。
4. #10 — Integration / foundation tail closure。
5. #11 — Phase 1 final Release Gate / 封板 checkpoint。

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
