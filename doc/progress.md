# 生活助理 App v0.1 — 開發進度摘要

最後更新：2026-10-02

目前狀態：**Phase 1 = PARTIAL。**

> 本檔只提供人類可快速閱讀的 rollup，不取代 `acceptance.md`、CI、deployment 或 runtime evidence。最新 PASS / FAIL / NOT VERIFIED 與 release evidence 仍以 GitHub `main` + runtime evidence 為準；目前開發先後順序請以 `phase1_delivery_order.md` 為準。

## Phase 1 全案封板進度表 — 剩餘 11 個工作包

### 百分比規則

- 封板進度 = `已 DONE 工作包 / 11`。
- 只有完整通過該工作包 exit condition 才打 ✅ 並納入百分比。
- `IN PROGRESS`、`PARTIAL`、`NOT VERIFIED` 都不算完成。
- 每完成 1 個工作包，封板進度增加約 **9.1%**。
- 這個 11 包百分比衡量的是 **2026-10-01 checkpoint 之後的剩餘 Phase 1 封板工作**，不是整個專案從第一天開始的歷史投入比例。

### 目前總覽

- **Completed packages：2 / 11**
- **Closure progress：18.2%**
- **Current package：#3 — Task 7 — provider-agnostic AI enrichment**
- **Current state：NOT VERIFIED — READY NEXT（NOT STARTED）**
- **Next checkpoint：#3 DONE 後 = 3/11 = 27.3%**

| # | 工作包 | 狀態 | DONE 條件 / 目前 gate |
|---|---|---|---|
| 1 | 完成 Task 6 — Drive / Notes 共用 Tag | ✅ DONE | Notes production UI E2E GREEN（含雙向 link/unlink）；Project↔Drive Runtime Acceptance #12 GREEN；release SHA `9a540a55baaf32a33e7376cab4183f998f596685`；CI #450、Cloud Run #322 PASS |
| 2 | 全專案 Design System / UI Style Checkpoint | ✅ DONE | Warm Knowledge 單一正式視覺基線已核准；Home / Tasks / Project 三張完工樣板已回存 Drive；semantic tokens、shared components、responsive contract 已落 GitHub；release SHA `567511c62fb70b0d8c40b54e2a9d0f4500bcfcf9`；CI #459、Firebase Hosting #277、Cloud Run #329 PASS |
| 3 | Task 7 — provider-agnostic AI enrichment | ⬜ NOT STARTED | 智能 Tag、候選 Notes、雙鏈建議、privacy/consent/cache/provider abstraction，backend tests GREEN |
| 4 | Task 8 — 智能整理 review UI | ⬜ NOT STARTED | 建議檢視、接受/拒絕、AI 狀態、consent UX、manual fallback，Flutter suite / Web build GREEN |
| 5 | Task 9 — Drive Knowledge 正式交付與 production acceptance | ⬜ NOT STARTED | CI、migration、Firebase、Cloud Run、authenticated runtime、真實 Drive integration evidence PASS |
| 6 | Habits 完整產品化 | ⬜ NOT STARTED | 完整 vertical slice：implementation、tests、CI、deployment/runtime、可操作 UI、mobile/desktop acceptance |
| 7 | Shopping 完整產品化 | ⬜ NOT STARTED | 完整 vertical slice：implementation、tests、CI、deployment/runtime、可操作 UI、mobile/desktop acceptance |
| 8 | Calendar 完整產品化 | ⬜ NOT STARTED | 一般使用者 read/list/create/update/delete UX + true-account verification + 完整 vertical-slice evidence |
| 9 | Activity / Execution Log + Integrations 完整產品化 | ⬜ NOT STARTED | 使用者可理解的 Activity / Integration UI + 所需 runtime/integration evidence |
| 10 | Integration / Foundation 尾項收尾 | ⬜ NOT STARTED | Attachment strategy；Bridge/MCP contract；true provider failure / partial-success；Calendar true-account read/list 重驗；historical SQLite migration 僅在 source 存在時執行 |
| 11 | Phase 1 Final Release Gate / 封板 checkpoint | ⬜ NOT STARTED | Implementation / Tests / CI / Deployment / Runtime / Integration / UI flow / mobile+desktop acceptance 證據完整；Drive checkpoint 回寫；Phase 1 才標 DONE |

### 固定回報格式

之後只要問「做到哪裡」，固定回報：

1. `Completed packages: X/11`
2. `Closure progress: Y%`
3. `Current package: #N — 名稱`
4. `Current state: PASS / FAIL / PARTIAL / NOT VERIFIED`
5. `Next concrete gate`

### 已完成但不重複計入這 11 包的歷史主線

以下已在較早 checkpoint 關閉，不重複放入 11 包分母：

- Idempotency
- Authorization / minimum-permission + destructive policy core
- Checklist Cloud
- App Shell
- Task complete UX
- Project UX
- Notes / full-text-search baseline
- Drive Knowledge Task 1–5

## 已建立的主要平台能力

目前 `main` 已具備並經不同層級驗證的核心基線包括：

- Firebase Hosting → Flutter Web / PWA。
- Cloud Run FastAPI Backend。
- PostgreSQL operational source of truth。
- Google identity / protected API baseline。
- Task Cloud CRUD + Web interaction path。
- Project Cloud CRUD、relation guard 與 Gmail → Project。
- Note / Habit / Shopping / Template Cloud API + persistence baseline。
- Gmail metadata + Gmail → Task / Calendar / Project。
- Calendar read/create/update/delete API。
- Drive Bridge ensure compatibility path。
- unified error envelope + request id。
- execution / activity log、failure / partial-success semantics。
- SQLite → PostgreSQL deterministic backfill tooling與 synthetic success/failure runtime gate。
- Calendar destructive confirmation baseline。
- action-id idempotency implementation baseline。
- shared immutable backend image / Artifact Registry cleanup strategy baseline。
- Warm Knowledge Design System semantic tokens / shared component / responsive contract baseline。

上述「平台能力存在」不等於所有產品 UI 已完成；各項真正完成狀態仍以 `acceptance.md` 的 evidence 層級為準。

## Package #1 封板 evidence — 2026-10-02

- Notes production UI acceptance：GREEN；雙向 link / unlink 已通過，刪除 nested-navigator regression 已補測。
- Project↔Drive runtime acceptance：run #12 / workflow run `36953736081`，GREEN。
- Project↔Drive 前一個 exit-code 28 根因：acceptance script 使用舊 FastAPI `detail` 錯誤格式；production 已統一為 shared `error.message` envelope。功能 delete guard 本體未壞。
- 修正 release SHA：`9a540a55baaf32a33e7376cab4183f998f596685`。
- CI #450：PASS。
- Deploy Cloud Run #322 / run `36952320601`：PASS；migration、deploy、health、readiness、401 protection、cloud-domain、checklist、idempotency、Google failure-path、SQLite success/failure、image retention 全 PASS。

## Package #2 封板 evidence — 2026-10-02

- 正式視覺方向：**Warm Knowledge**；不再允許第二套正式 theme track。
- Drive 正式視覺基準：`life_assistant Design System — Final UI Reference`（file ID `1QnKn-UbAadpCY58EYdatvbxkRLOWKHC8V4rTYoEXLy8`），實際嵌入 Home / Dashboard、Tasks、Project 三張完工樣板。
- GitHub implementation / spec release SHA：`567511c62fb70b0d8c40b54e2a9d0f4500bcfcf9`。
- semantic token baseline：spacing、radius、breakpoints、window classes、layout、motion、44px minimum touch target。
- shared component baseline：`AppPageFrame`、`AppSectionCard`、`AppStatusChip`、`AppStatePanel`；barrel `lib/app/design_system/design_system.dart`。
- responsive contract：compact `<600`、medium `600–839`、expanded `840–1199`、roomy `>=1200`；page-action breakpoint `720`；content max width `1040`。
- CI #459 / run `36985802044`：PASS；backend、deployment scripts、Flutter Analyze、Test、Web build、branding verify 全 PASS。
- Firebase Hosting #277 / run `36986034878`：PASS；Hosting runtime verify、Task production acceptance、Project production acceptance PASS。
- Deploy Cloud Run #329 / run `36985912899`：PASS；migration、backend deploy、health、readiness、401 protection、authenticated cloud-domain、Checklist、idempotency、Google provider failure-path、SQLite backfill success/failure、image retention 全 PASS。
- 此工作包封的是 Design System 基線與 adoption contract；既有頁面逐頁 pixel-level 重構屬後續 UI adoption，不另開第二套設計系統。
- Drive long-lived closure tracker 應同步為 `2/11 = 18.2%`，Current package = #3。

## 文件與 evidence 分工

- `phase1_delivery_order.md`：目前執行順序。
- `progress.md`：人類可讀的 rollup + 11 包全案封板進度表。
- `todo.md`：active / next backlog。
- `acceptance.md`：逐項 completion truth 與 release evidence。
- `release_checklist.md`：Phase 1 final release gate。
- `wbs.md`：scope decomposition，不代表排程。
- `doc/design_system.md`：Design System 核心設計原則與 token 基礎。
- `doc/design_system_checkpoint_v0_2.md`：Package #2 核准後的 responsive / component / adoption implementation contract。
- 歷史 batch progress 文件：保留稽核價值，不再當 current status。

## 下一步

目前固定下一步：

1. 工作包 #3：Task 7 — provider-agnostic AI enrichment。
2. 先依目前 GitHub implementation 盤點既有 AI/provider abstraction、privacy/consent/cache 與 Notes/Tag linkage 契約，再進 TDD。
3. 完成智能 Tag、候選 Notes、雙鏈建議與 provider-agnostic backend contract；backend tests / CI GREEN 後再進下一 gate。
4. Design System #2 已封板；所有新 UI 直接採 Warm Knowledge 共用 tokens / components，不再重新討論第二套主風格。
