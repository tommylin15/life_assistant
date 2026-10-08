# 生活助理 App v0.1 — 開發進度摘要

最後更新：2026-10-07

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

- **Completed packages：7 / 11**
- **Closure progress：63.6%**
- **Current package：#8 — Calendar 完整產品化（IN PROGRESS）**
- **Current state：PARTIAL — Calendar backend CRUD exists；Flutter UI、tests 與 production acceptance candidate 正在推進；CI / deployment / live Google account 尚待新 evidence。**
- **Next checkpoint：#8 Calendar implementation → CI → Firebase / Cloud Run → desktop/mobile production UI → true-account Calendar read/list → closure。**
- **#8 gating rule：Gemini / OpenRouter #63/#70 failure is a separate known regression, not a Calendar-specific gate. Calendar still needs its own genuine provider and production evidence.**
- **Independent cross-feature health：historical Drive Knowledge #63 / run `37625447402` exit `91` = Gemini-only；newer #70 / run `37702785541` exit `93` = Gemini + OpenRouter (Groq not in mask)。diagnostic candidate `8dedf655` / CI #574 PASS；new deployment / runtime still NOT VERIFIED。Regression remains OPEN / FAIL, without undoing Shopping #7 DONE.**

| # | 工作包 | 狀態 | DONE 條件 / 目前 gate |
|---|---|---|---|
| 1 | 完成 Task 6 — Drive / Notes 共用 Tag | ✅ DONE | Notes production UI E2E GREEN（含雙向 link/unlink）；Project↔Drive Runtime Acceptance #12 GREEN；release SHA `9a540a55baaf32a33e7376cab4183f998f596685`；CI #450、Cloud Run #322 PASS |
| 2 | 全專案 Design System / UI Style Checkpoint | ✅ DONE | Warm Knowledge 單一正式視覺基線已核准；Home / Tasks / Project 三張完工樣板已回存 Drive；semantic tokens、shared components、responsive contract 已落 GitHub；release SHA `567511c62fb70b0d8c40b54e2a9d0f4500bcfcf9`；CI #459、Firebase Hosting #277、Cloud Run #329 PASS |
| 3 | Task 7 — provider-agnostic AI enrichment | ✅ DONE | provider abstraction、privacy/consent/cache、shared Tag、候選 Notes、accept/reject relation、partial-success semantics；release SHA `cd2fdcd5645a9f73141c7824b59a8349d15bb86c`；CI #463、Cloud Run #335、Drive AI Runtime #3 PASS |
| 4 | Task 8 — 智能整理 review UI | ✅ DONE | 獨立 Drive review/settings UI、provider-neutral presentation、explicit consent、Note suggestion accept/reject、force re-analysis、partial/failed/skipped fallback、desktop/mobile production acceptance；release SHA `78cdb43645f606d63b8a6171e53babec9f26de10`；CI #482、Firebase #300、Notes/Drive UI Acceptance #65 PASS；backend/runtime 沿用相同產品碼基線 Cloud Run #352 + Post-deploy Runtime #17 PASS |
| 5 | Task 9 — Drive Knowledge 正式交付與 production acceptance | ✅ DONE | historical closure release `2d08118a13c71c6fec97e8bfba0857b861eefd1e` / #47 PASS；latest health release `3b75e9e288be0d2179cd381281b55210a14ad875` / Drive Knowledge #59 PASS；Picker / live external AI / 真實 Drive / production UI 全 PASS |
| 6 | Habits 完整產品化 | ✅ DONE | release SHA `02eda1124885846f41ca32ca185d9e1a5a5ebfe1`；CI #558、Firebase #376、Cloud Run #430、Habits UI Acceptance #7、Post-deploy Runtime #96 全 PASS；Habit list/create/update/complete/history、週期/提醒 UI、mobile/desktop production acceptance 與真實 PostgreSQL runtime evidence 完整 |
| 7 | Shopping 完整產品化 | ✅ DONE | release SHA `1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d`；CI #566、Firebase #384、Cloud Run #438、Shopping UI #4、Post-deploy Runtime #104 PASS；list/create item/toggle、分類/進度、mobile navigation、真實 PostgreSQL cloud-domain persistence evidence 完整 |
| 8 | Calendar 完整產品化 | 🟡 IN PROGRESS | 一般使用者 read/list/create/update/delete UX + true-account verification + 完整 vertical-slice evidence |
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

## Package #5 closure evidence — 2026-10-07

- 狀態：**DONE / PASS**；全案 closure **5/11 = 45.5%**。
- Production release `2d08118a13c71c6fec97e8bfba0857b861eefd1e`；ready revision `life-assistant-api-00154-xrt`。
- CI #551、Firebase #369、Notes UI run `37568672137`、Drive Knowledge #47 / run `37568734572` final mandatory gate：PASS。
- Cloud Run #423 / run `37568479305`：PASS；ready revision、core persistence、checklist、action-id、Google failure-path 與 synthetic SQLite backfill / failure-path 回歸驗收全 PASS。
- Picker、synthetic runtime、真實 Drive、Gemini → Groq → OpenRouter 免費路由、production desktop/mobile UI：PASS。
- Runtime 僅讀 `life-assistant-bundle:latest`；新 version `7` enabled、舊 versions `1–6` destroyed。完整 execution / model / fixture / secret evidence 見 `acceptance.md`、`integrations.md`。

## Package #6 closure evidence — 2026-10-07

- 狀態：**DONE / PASS**；全案 closure **6/11 = 54.5%**。
- Final release SHA：`02eda1124885846f41ca32ca185d9e1a5a5ebfe1`。
- Product implementation：Habits Web API facade、`/more/habits` 正式入口、list/create/update、週期/提醒、append-only completion history、完成操作、loading/empty/error state、responsive UI。
- Accessibility / interaction follow-up：`28f1bddc34f0e87c8eb757ce446ad8d9e54ec7c4` 隔離 completion/history action semantics；final acceptance 以 Flutter pointer event 驗證真實操作。
- CI #558 / run `37577319168`：PASS；backend tests、deployment-script syntax、Flutter Analyze、完整 widget tests、Web build、branding verify 全 PASS。
- Firebase Hosting #376 / run `37577494901`：PASS；exact release deploy、Hosting verify、Task/Project production regression 全 PASS。
- Habits UI Acceptance #7 / run `37577765718`：PASS；desktop list/create/edit/complete/history 與 mobile navigation/controls 全 PASS。
- Deploy Cloud Run #430 / run `37577494982`：PASS；migration、deploy、health、DB readiness、401 protection、authenticated cloud-domain、checklist、idempotency、Google failure-path、SQLite backfill success/failure、image cleanup 全 PASS。
- Post-deploy Runtime Acceptance #96 / run `37579244566`：PASS；Notes、Project Drive、Drive AI enrichment regression 全 PASS。
- Habit backend runtime 由 authenticated cloud-domain acceptance 真實走 PostgreSQL，涵蓋 habit create/update/complete/completions/activity persistence。
- 因此 Package #6 計入 DONE；下一工作包為 **#7 Shopping 完整產品化**。
- **Cross-feature regression closure：**Habits release `02eda112...` 的 Drive Knowledge Runtime Acceptance #54 / run `37578066375` 曾因 live external AI production acceptance FAIL。後續 commits `89d54011` / `a44617bc` / `668aa0db` / `3b75e9e2` 加入 transient retry、provider failure mask 與測試；release `3b75e9e288be0d2179cd381281b55210a14ad875` 的 CI #562、Firebase #380、Cloud Run #434、Post-deploy Runtime #100 與 Drive Knowledge Runtime Acceptance #59 / run `37595859159` 均 PASS，latest-release Drive Knowledge health 已恢復全綠。

## Package #7 closure evidence — 2026-10-07

- 狀態：**DONE / PASS**；全案 closure **7/11 = 63.6%**。
- Final release SHA：`1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d`。
- Product implementation：`/more/shopping` 正式入口、Shopping API facade、清單建立、品項新增、分類、完成狀態 toggle、清單完成進度、loading / empty / error state、responsive mobile/desktop UI。
- Initial product commit：`6884d9baadec0702ac8976edda07ac79068c6020`；provider-container test isolation fix：`a99a11ff980df16442b28876b4efe113d8721363`；production semantics hardening：`a88e7acc23c701c22b27b3419a10e8b61492a238`；mobile merged-semantics navigation fix：`1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d`。
- CI #566 / run `37621843816`：**PASS**；backend、deployment scripts、Flutter Analyze、完整 tests、Web build、branding verify 全 PASS。
- Firebase Hosting #384 / run `37622140411`：**PASS**；exact release deploy/verify、Task 與 Project production UI regression PASS。
- Shopping UI Acceptance #4 / run `37622504893`：**PASS**；`list_category_progress`、`create_list`、`create_item`、`toggle_item`、`mobile_navigation_controls` 全 PASS。
- Habits UI #15 / run `37622504844`、Notes UI #149 / run `37622504904`：**PASS**，同 release UI regression 未發現新破壞。
- Deploy Cloud Run #438 / run `37622140547`：**PASS**；migration、deploy、health、DB readiness、401 protection、authenticated cloud-domain、checklist、action-id idempotency、Google failure-path、SQLite success/failure 與 image cleanup 全部通過。Authenticated cloud-domain acceptance 真實走 FastAPI + PostgreSQL，涵蓋 Shopping list/item persistence。
- Post-deploy Runtime Acceptance #104 / run `37624483194`：**PASS**。
- 因此 Shopping #7 的 DONE 條件（implementation / tests / CI / deployment / runtime / UI entry + 操作 flow / mobile+desktop acceptance）均有直接 evidence，Package #7 計入 DONE。
- **不相關但必須保留的 latest-release health issue：**Historical Drive Knowledge #63 / run `37625447402` task exit `91` 為 Gemini-only；newer #70 / run `37702785541` exit `93` 為 Gemini bit `1` + OpenRouter bit `2`，Groq not failed in mask。其它 production config、synthetic runtime、real Drive fixture、exact Firebase release、OAuth、UI gates PASS。Diagnostic candidate `8dedf655` adds independent two-provider reason codes; CI #574 PASS, new deployment/live still NOT VERIFIED。Provider regression **OPEN / FAIL**，不降級驗收門檻。

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

1. #7 Shopping 已 **DONE / PASS**；封板進度 **7/11 = 63.6%**。
2. 依使用者指示，本對話停在 #7；**#8 Calendar 尚未開始**，留待新對話。
3. Drive Knowledge historical #63 exit `91`（Gemini only），newer #70 exit `93`（Gemini + OpenRouter）；待 provider-specific diagnostics live evidence，維持 **OPEN / FAIL**。
4. Phase 1 整體仍 **PARTIAL**；#8–#11 尚未完成。
# CI/CD V2 checkpoint — 2026-10-08

**IMPLEMENTING / NOT CLOSED**. Synced main `a9a570cf29f2dd28d79c5936a18cad54a9f6b22f`;
existing us-central1 GitHub connection/repository is COMPLETE, trigger absent
at baseline. Added Cloud Build pipeline, immutable candidate/preview sequence,
preserved runtime/UI gates, and real HTTPS/Google/DB/browser acceptance runner.
Local contract validation is separate from actual main-push/live acceptance.
Exact minimal deployer IAM grants approved/applied; extra GCS evidence removed.
Push CI trigger `70ca60f2-8519-40c4-9422-5ac78f1b355f`, manual Release trigger
`892a893e-173f-49b2-9055-d5a9adc21496`, both us-central1/2nd Gen. Per additional
user policy, Actions automatic deployments changed to manual recovery entries.
No production cutover or physical image deletion yet.
See `deployment_runbook.md`; product closure count is unchanged by CI/CD work.
