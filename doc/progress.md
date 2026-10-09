# 生活助理 App v0.1 — 開發進度摘要

最後更新：2026-10-09（Calendar #8 exact-SHA CI/V3/Firebase/真實 Google read-list/desktop-mobile UI 完整封板；下一軌 M0）

目前狀態：**Phase 1 = PARTIAL。**

> 本檔只提供人類可快速閱讀的 rollup，不取代 `acceptance.md`、CI、deployment 或 runtime evidence。最新 PASS / FAIL / NOT VERIFIED 與 release evidence 仍以 GitHub `main` + runtime evidence 為準；目前開發先後順序請以 `phase1_delivery_order.md` 為準。

## CI/CD V3、AR/GCS 清理最新進度（獨立於 Phase 1 功能封板）

- **V3 GitHub Actions → 公開 GHCR → Cloud Run：PASS**。最新已驗證的正式 release SHA `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7`，[V3 run 37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014)：固定 GHCR digest、100% promotion、health/ready/auth/DB、rollback rehearsal/restore、API latest-10 revision retention PASS。歷史 `life-assistant-api-00183-hax` / `sha256:b06254...` 為**先前** release evidence，不再當成最新服務狀態。
- **舊 Cloud Build 5 個 Triggers 全部 disabled=true：PASS**（兩個 life-assistant、Janus 一個、OmniAgent 兩個）。Trigger 定義仍存在，狀態是停用而非刪除。
- **舊 CI/CD GCS Bucket 清理：PASS**。Bucket 數 8 → 5；兩個 `cloudbuild` Buckets 及 `run-sources-gen-lang-client-0593591102-us-central1` 均不存在；舊 CI/CD Bucket 逐一 404 readback。保留五個 `dev-*` Buckets，不碰應用／備份／研究資料。
- **AR 舊 Docker Repository 清理：PASS**。AR repository 數 4 → 1；`cloud-run-source-deploy`, `janusai-poc`, `omniagent` 不存在。唯一保留的 `janus-postgres/postgres:16.15` 含 **1 Digest**；us-central1 Cloud Run 未發現引用，但 VM/資料庫容器依賴 **NOT VERIFIED**，因此不刪。
- **最終 runtime/GCP inventory：PASS**：[run 37867249614](https://github.com/tommylin15/life_assistant/actions/runs/37867249614)。過去 58 個 AR Digest / 77 個 GCS source objects 為**清理前候選估算**，不能當成逐項 delete 事件紀錄；現況以 Bucket/Repository 缺席與 1 Digest readback 為準。
- **舊 CI/CD 指定資產清理 = DONE/PASS**；但「所有 AR 清空」不是 DONE（剩 `janus-postgres`）。最新 V3 run 37882875014 證實 **life-assistant-api** retention = 10 PASS；其他 Cloud Run services 即時數量與 VM 非 Cloud Run 依賴仍 **NOT VERIFIED**。**Phase 1 全案 PARTIAL，功能封板 8/11**。
- 詳細證據、完整清單與差異：[`v3_cleanup_and_cutover_inventory.md`](v3_cleanup_and_cutover_inventory.md)。

## Phase 1 全案封板進度表 — 剩餘 11 個工作包

### 百分比規則

- 封板進度 = `已 DONE 工作包 / 11`。
- 只有完整通過該工作包 exit condition 才打 ✅ 並納入百分比。
- `IN PROGRESS`、`PARTIAL`、`NOT VERIFIED` 都不算完成。
- 每完成 1 個工作包，封板進度增加約 **9.1%**。
- 這個 11 包百分比衡量的是 **2026-10-01 checkpoint 之後的剩餘 Phase 1 封板工作**，不是整個專案從第一天開始的歷史投入比例。

### 目前總覽


- **Completed packages：8 / 11**
- **Closure progress：72.7%**
- **Just closed：#8 — Calendar 完整產品化（DONE / PASS）**
- **Current priority（已核准）：台灣免費活動探索 M0 觀測與 M1 資料核心並行，均 PARTIAL。** M0 Registry / 離線品質 8 tests [CI #37892185617](https://github.com/tommylin15/life_assistant/actions/runs/37892185617) PASS；M1 六表 0011 migration、正規化、去重/安全、離線 manifest、文化部 Adapter 及不對外開放的原子 PostgreSQL upsert service 已實作，[CI #37895465333](https://github.com/tommylin15/life_assistant/actions/runs/37895465333) 全 PASS；M2 唯讀 verified-only API/Flutter 更多入口與離線 widget tests 也已提交，最新完整 CI、正式 PostgreSQL runtime 與瀏覽器驗收仍 NOT VERIFIED，詳見 `free_events_m1_checkpoint.md`。正式來源/14 天觀測/DB migration/online batch 仍 NOT VERIFIED / NOT IMPLEMENTED。原 Phase 1 工作包仍 **8/11**。
- **Next remaining original Phase 1 package：#9 Activity / Execution Log + Integrations（按核准順序暫排在活動探索 MVP 後）。**
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
| 8 | Calendar 完整產品化 | ✅ DONE / PASS | release `5c8d2fca8c9b`：CI 37882690249、V3 37882875014、Firebase 37885328134、真實 Calendar read/list 37885330178、desktop/mobile UI 37885544932、Bootstrap 37882690327 全 PASS；詳見 Calendar checkpoint |
| 9 | Activity / Execution Log + Integrations 完整產品化 | ⬜ NOT STARTED | 使用者可理解的 Activity / Integration UI + 所需 runtime/integration evidence |
| 10 | Integration / Foundation 尾項收尾 | ⬜ NOT STARTED | Attachment strategy；Bridge/MCP contract；true provider failure / partial-success；Calendar true-account read/list 重驗；historical SQLite migration 僅在 source 存在時執行 |
| 11 | Phase 1 Final Release Gate / 封板 checkpoint | ⬜ NOT STARTED | Implementation / Tests / CI / Deployment / Runtime / Integration / UI flow / mobile+desktop acceptance 證據完整；Drive checkpoint 回寫；Phase 1 才標 DONE |

### #8 — Calendar 最終封板證據（2026-10-09）

- Source / release SHA: `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7` (同一完整 SHA 綁定 CI / V3 / Firebase / Calendar UI / Google read-list)。
- **Implementation / tests / CI — PASS:** [CI #37882690249](https://github.com/tommylin15/life_assistant/actions/runs/37882690249) backend tests、Flutter analyze/widgets/Drive nav/Web build、deployment scripts；全天日期 `start_date/end_date` 保持 Google `end.date` exclusive；對話框 `dialogContext` 修復巢狀 Navigator。
- **V3 GHCR → Cloud Run + runtime — PASS:** [V3 #37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014) immutable digest、Trivy、0%-traffic candidate、健康/資料庫/Auth、Preview、真實 pre-promotion integration、100% promotion/live、rollback rehearsal/restore、`life-assistant-api` 最新 **10 revisions** retention PASS。
- **Firebase Hosting — PASS:** [#37885328134](https://github.com/tommylin15/life_assistant/actions/runs/37885328134) exact-SHA release file, Flutter Web production, Task/Project UI regression gates。
- **真實 Google Calendar 授權 read/list（唯讀）— PASS:** [#37885330178](https://github.com/tommylin15/life_assistant/actions/runs/37885330178) 已有 owner-scoped Cloud Run Job runtime 成功結果；不宣稱曾對真實使用者行程執行 create/update/delete。
- **正式桌面／手機 Calendar UI（mocked Google responses）— PASS:** [#37885544932](https://github.com/tommylin15/life_assistant/actions/runs/37885544932) log: `month_list_allday`、`create_tz`、`update`、`confirmed_delete`、`all_day_edit`、`mobile_navigation_controls` 與 `calendar_ui_acceptance=PASS`。刪除驗證含「取消時無 mutation」及明示確認 header；此 UI 模擬不等同真實 Google mutation E2E。
- **Bootstrap E2E orchestration — PASS:** [#37882690327](https://github.com/tommylin15/life_assistant/actions/runs/37882690327) 逐步驗證 V3 + Firebase + Calendar UI + True Account gates，同 SHA 全成功。
- **特定界線：** #8 Calendar 依核准的 read/list 真實帳號 + mocked browser mutation 流程驗收封板；尚未以正式 Google 帳號執行真實 create/update/delete（風險較高的外部寫入），這不冒充已驗證。Drive Knowledge Gemini/OpenRouter 歷史 #63/#70 failure 仍是獨立跨功能 health backlog，不隨 Calendar 封板自動消失。

**結論：Package #8 DONE/PASS，總進度 8/11 = 72.7%；Phase 1 最終 Release Gate 仍 PARTIAL。**

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

### CI/CD V2 runtime identity correction (2026-10-08)

- Commit `3a6941bddd7a2ba658240a1e74e255b5ee27da15` real push build `e95cee5e-2c91-44b3-ad81-baa2da1979ad` FAILED before tests: Cloud SDK image has no `python3` on PATH. No deployment executed.
- User approved and applied only deployer Service Account User on existing `omniagent-codex-life-client`, and that caller Secret Accessor on `life-assistant-bundle`. No default Compute impersonation grant.
- Candidate/API and the three existing Life Assistant jobs use this dedicated identity on the next release; shared provider checks metadata email and requests the audience-bound identity token directly. Existing live revision remains unchanged until acceptance.
- V2 remains OPEN; Push CI, release and all mandatory live gates still require real PASS evidence.

### Real Push CI evidence (2026-10-08)

- SHA `02a43ebf4de5209d720506f9da165ad93f8bfe8a`, regional build `cc710f32-0e32-48f6-9471-90399e771f63`: **SUCCESS**, 04:51:46.864–04:58:35.557 UTC (408.693 seconds).
- GCP Backend 403 tests PASS; Flutter 63 tests PASS; analyze completed with existing 109 info diagnostics and unchanged no-fatal-infos policy; Web build and branding checks PASS. Alembic verification reached `20261007_0010`.
- No Docker push, migration job, Cloud Run deployment or Firebase publication in Push CI. Full-SHA manual Release and live gates remain pending.
- Worker list-price estimate: 6.8116 minutes × $0.006 = **$0.04087**, before shared free allowance; not an invoice. Public standard GitHub runner remains $0 runner cost under its existing policy. V2 is not claimed cheaper. Failed build time and release/job/log costs must also be counted.
- Earlier build `29f9f507-64d5-4a92-a0fe-3bc9350c3eba` failed on official Flutter manifest URL 404; corrected root verified against official manifest and 3.47.3 checksum.

### Manual Release attempt evidence (2026-10-08)

- Latest SHA `09e89ccd59d71a2b5d561e0b079dd863e5b3e32c`: Push CI `c84b3516-20ec-4db3-ad7f-1b3fe8af1993` SUCCESS (125.993 seconds; worker list-price $0.01260).
- Manual candidate-only Release `b4ca14a1-c29a-44cb-9a02-ecd9fd83f5ac` FAILED at Scheduler baseline readback: deployer lacks `cloudscheduler.jobs.list`. Backend 403 / Flutter 63 tests and Web/Docker build passed; no migration, candidate deployment or Firebase Preview occurred.
- Immutable image: `us-central1-docker.pkg.dev/gen-lang-client-0593591102/cloud-run-source-deploy/life-assistant-backend@sha256:d882d80ad30f5dc898c3b306a7c0bdacb3a68872bf0cb1526c2ebaf80d9460ff`.
- Release worker runtime 556.119 seconds (9.26865 min), list-price $0.05561 before shared allowances; failed releases cost worker time too. Cloud Run Job costs not incurred by this attempt. This is an estimate, not billing-export evidence.
- Existing user credential readback: us-central1 Scheduler `janus-ingestion-daily`, `30 * * * *`, Asia/Taipei, ENABLED; untouched. Life Assistant jobs remain the same three existing names. This does not satisfy automated deployer readback.
- Auto-review rejected the additional Scheduler Viewer IAM grant because previous approvals did not include it. Exact read-only grant requested separately; no bypass or gate removal.
- Candidate/live revision, Preview/live publication, true UI/Provider/Integration acceptance and cleanup remain pending. **V2 OPEN / NOT CLOSED**.

### CI/CD V2 暫停 checkpoint — 2026-10-08

狀態：**PAUSED BY USER / OPEN / NOT CLOSED**。以下為真實 runtime evidence，不代表完整 Release PASS。

- Release source SHA：`09e89ccd59d71a2b5d561e0b079dd863e5b3e32c`；Push CI `c84b3516-20ec-4db3-ad7f-1b3fe8af1993` SUCCESS。
- 使用者核准後已套用 deployer 的 `roles/cloudscheduler.viewer`；本輪 deployer Scheduler/Jobs baseline readback PASS。排程未修改，未執行生活總排程或每小時監控。
- Manual candidate-only Build `af461348-13ee-4f43-833a-428f06f4e813` 已依使用者「先暫停」取消，讀回 **CANCELLED**。執行時間 2026-10-08 13:34:12–14:00:06 Asia/Taipei（1554.286 秒）；worker 牌價估算 US$0.15543，未扣共用免費額度、不含 Jobs/Logs/Registry，非帳單。
- Migration `life-assistant-db-migrate-m2jcx` PASS：pre/post `20261007_0010`，`verify-current`，沒有重複 schema migration。
- Candidate `life-assistant-api-00174-luw` 0% 流量；正式 `life-assistant-api-00173-gpf` 保持 100%。Candidate digest：`sha256:53d9a712e7a5262ce5c8a9f452d6e9cc531f38e78922fcd40f40712247b1a201`。
- Candidate health/readiness/database、未登入 401、OAuth redirect、single-user owner allowlist PASS；這不等於全部 Auth/owner/live gates 已完成。
- Cloud domain parity PASS：`life-assistant-core-acceptance-jgz2t`；Checklist PASS：`life-assistant-core-acceptance-d67jw`；idempotency PASS：`life-assistant-core-acceptance-mhbmk`。
- 取消時已啟動的 Google failure execution `life-assistant-core-acceptance-h65nm` 讓它完成清理；後續唯讀 readback succeededCount=1、runningCount=0（PASS）。Cloud Build 已取消，不把此結果寫成整輪 Release PASS。
- Firebase Preview/Live 均未發布；既有 live Hosting baseline version `7269b54b36337ed6`。尚缺 SQLite backfill success/failure、真實 HTTPS Google/DB/browser、POST/Drive/Calendar/Shared Codex/External Provider、Preview/Live UI/integration、post-deploy readback 與安全 image cleanup。
- Provider 既有 Gemini/OpenRouter FAIL 保持獨立 blocker；本輪尚未執行 Provider gate，沒有新增 Provider PASS 證據。Image 沒有實體刪除，沒有新 GCS evidence bucket。
- 舊 Actions 自動部署入口已改 manual；main 文件 push 只會觸發 CI，不恢复 Release。恢復前先讀回殘留 executions/traffic/Hosting、確認 main 完整 SHA、適用 CI/Ready gate；不得重跑正在執行的資料寫入型 Job或自動 downgrade DB。
