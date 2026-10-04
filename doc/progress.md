# 生活助理 App v0.1 — 開發進度摘要

最後更新：2026-10-04

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

- **Completed packages：4 / 11**
- **Closure progress：36.4%**
- **Current package：#5 — Task 9 — Drive Knowledge 正式交付與 production acceptance**
- **Current state：NOT STARTED — 依使用者指示，Task 8 封板與文件回寫後停止，尚未開始 Task 9。**
- **Next checkpoint：#5 DONE 後 = 5/11 = 45.5%**

| # | 工作包 | 狀態 | DONE 條件 / 目前 gate |
|---|---|---|---|
| 1 | 完成 Task 6 — Drive / Notes 共用 Tag | ✅ DONE | Notes production UI E2E GREEN（含雙向 link/unlink）；Project↔Drive Runtime Acceptance #12 GREEN；release SHA `9a540a55baaf32a33e7376cab4183f998f596685`；CI #450、Cloud Run #322 PASS |
| 2 | 全專案 Design System / UI Style Checkpoint | ✅ DONE | Warm Knowledge 單一正式視覺基線已核准；Home / Tasks / Project 三張完工樣板已回存 Drive；semantic tokens、shared components、responsive contract 已落 GitHub；release SHA `567511c62fb70b0d8c40b54e2a9d0f4500bcfcf9`；CI #459、Firebase Hosting #277、Cloud Run #329 PASS |
| 3 | Task 7 — provider-agnostic AI enrichment | ✅ DONE | provider abstraction、privacy/consent/cache、shared Tag、候選 Notes、accept/reject relation、partial-success semantics；release SHA `cd2fdcd5645a9f73141c7824b59a8349d15bb86c`；CI #463、Cloud Run #335、Drive AI Runtime #3 PASS |
| 4 | Task 8 — 智能整理 review UI | ✅ DONE | 獨立 Drive review/settings UI、provider-neutral presentation、explicit consent、Note suggestion accept/reject、force re-analysis、partial/failed/skipped fallback、desktop/mobile production acceptance；release SHA `78cdb43645f606d63b8a6171e53babec9f26de10`；CI #482、Firebase #300、Notes/Drive UI Acceptance #65 PASS；backend/runtime 沿用相同產品碼基線 Cloud Run #352 + Post-deploy Runtime #17 PASS |
| 5 | Task 9 — Drive Knowledge 正式交付與 production acceptance | ⬜ NOT STARTED | CI、migration、Firebase、Cloud Run、authenticated runtime、真實 Drive integration evidence PASS；目前未啟動 |
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
- provider-agnostic Drive AI enrichment foundation：explicit consent、stable cache、shared Tag、bounded Note suggestions、accept/reject authoritative relation 與 partial-success semantics。
- Drive 智能整理 review UI：獨立 review/settings surface、provider-neutral status、consent UX、suggestion decision、force re-analysis、manual/degraded fallback、responsive production acceptance。

上述「平台能力存在」不等於所有產品 UI 已完成；各項真正完成狀態仍以 `acceptance.md` 與對應 checkpoint/runtime evidence 的證據層級為準。

## Package #1 封板 evidence — 2026-10-02

- Notes production UI acceptance：GREEN；雙向 link / unlink 已通過，刪除 nested-navigator regression 已補測。
- Project↔Drive runtime acceptance：run #12 / workflow run `36953736081`，GREEN。
- 修正 release SHA：`9a540a55baaf32a33e7376cab4183f998f596685`。
- CI #450：PASS。
- Deploy Cloud Run #322 / run `36952320601`：PASS。

## Package #2 封板 evidence — 2026-10-02

- 正式視覺方向：**Warm Knowledge**；不再允許第二套正式 theme track。
- GitHub implementation / spec release SHA：`567511c62fb70b0d8c40b54e2a9d0f4500bcfcf9`。
- semantic token baseline、shared components、responsive contract 已落地。
- CI #459 / run `36985802044`：PASS。
- Firebase Hosting #277 / run `36986034878`：PASS。
- Deploy Cloud Run #329 / run `36985912899`：PASS。

## Package #3 封板 evidence — 2026-10-02

- 範圍：Task 7 provider-agnostic AI enrichment backend foundation；不包含 Task 8 review UI，也不宣稱 Task 9 true Drive / external-AI production integration 已完成。
- final release SHA：`cd2fdcd5645a9f73141c7824b59a8349d15bb86c`。
- Provider abstraction、privacy / consent、stable cache、shared Tag、bounded Note candidates、accept/reject persistence、partial-success semantics 已落地。
- Alembic head：`20261002_0009`。
- CI #463 / run `36994280896`：PASS；backend **315/315 tests PASS**。
- Firebase Hosting #281 / run `36994497368`：PASS。
- Deploy Cloud Run #335 / run `36994497260`：PASS。
- Drive AI Enrichment Runtime Acceptance #3 / run `36997713417`：PASS。
- 詳細 checkpoint：`doc/drive_ai_enrichment_checkpoint_v0_1.md`。
- Concrete external provider / true Drive production delivery 留在後續工作包，不阻塞 #3 foundation closure。

## Package #4 封板 evidence — 2026-10-04

- 狀態：**DONE / PASS — Task 8 智能整理 review UI。**
- Scope 僅封板 review UI，不宣稱 Task 9 的 true Drive / external-AI production delivery 已完成。
- Design/spec：`docs/superpowers/specs/2026-10-02-intelligent-organization-review-ui-design.md`。
- Implementation plan：`docs/superpowers/plans/2026-10-02-intelligent-organization-review-ui.md`。
- Flutter：新增 Drive API facade、`DrivePage`、`DriveSettingsPage`、`/more/drive` 與 `/more/drive/settings` navigation。
- UX contract：provider-neutral；explicit content consent；`succeeded / partial / failed / skipped` 狀態；cache indication；related Note suggestion accept/reject；force re-analysis；AI failure 不遮蔽 core Drive documents。
- Final UI acceptance release SHA：`78cdb43645f606d63b8a6171e53babec9f26de10`。
- CI #482 / run `37168408452`：PASS；backend、deployment scripts、Flutter Analyze、Drive navigation test、完整 Flutter tests、Web build、branding verify 全 PASS。
- Firebase Hosting #300 / run `37168500908`：PASS；build、release stamp、deploy、Hosting verify、Task production UI、Project production UI 全 PASS。
- Notes UI Acceptance #65 / run `37168620482`：PASS；exact release SHA 驗證後，Notes production acceptance PASS；Drive desktop review provider-neutral、accept suggestion、force re-analysis、settings consent save、mobile review controls、mobile settings 全 PASS；`drive_ui_acceptance=PASS`。
- Backend/runtime product code在最後兩個 acceptance-only commits 未變；已驗證基線：Deploy Cloud Run #352 / run `37130495284` PASS，Post-deploy Runtime Acceptance #17 / run `37132443415` PASS。
- Acceptance locator follow-up commits `0fbd3807ef8df4de29b4ed5ffffb0aa701af4652` 與 `78cdb43645f606d63b8a6171e53babec9f26de10` 僅修改 `.github/scripts/verify_drive_ui_production.mjs`，不改 Flutter/Backend product behavior；其中後者修正 Flutter Web merged ARIA semantics 的 production E2E 定位。
- 詳細 checkpoint：`doc/drive_intelligent_organization_review_ui_checkpoint_v0_1.md`。
- 因此 Package #4 計入 DONE；全案封板進度更新為 **4/11 = 36.4%**。

## 文件與 evidence 分工

- `phase1_delivery_order.md`：目前執行順序。
- `progress.md`：人類可讀的 rollup + 11 包全案封板進度表。
- `todo.md`：active / next backlog。
- `acceptance.md`：Phase 1 completion truth；若舊條目未即時同步，最新 GitHub/runtime evidence 與專項 checkpoint 優先，並在後續 final release gate 收斂。
- `release_checklist.md`：Phase 1 final release gate。
- `wbs.md`：scope decomposition，不代表排程。
- `doc/design_system.md`：Design System 核心設計原則與 token 基礎。
- `doc/design_system_checkpoint_v0_2.md`：Package #2 checkpoint。
- `doc/drive_ai_enrichment_checkpoint_v0_1.md`：Package #3 checkpoint。
- `doc/drive_intelligent_organization_review_ui_checkpoint_v0_1.md`：Package #4 checkpoint。
- 歷史 batch progress 文件：保留稽核價值，不再當 current status。

## 下一步

依使用者指示，本輪在 Task 8 封板與文件回寫後停止：

1. 下一工作包為 #5 — Task 9：Drive Knowledge 正式交付與 production acceptance。
2. **Task 9 目前 NOT STARTED，本輪不執行任何 Task 9 implementation / deployment。**
3. 後續重新開始時，先以當時 GitHub `main` / runtime evidence 重新確認 Task 9 gate，再繼續。