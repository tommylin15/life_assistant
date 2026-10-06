# life_assistant — Active TODO

最後更新：2026-10-06

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #5 — Task 9：Drive Knowledge 正式交付與 production acceptance

狀態：**PARTIAL**。

目前 exact release SHA：`8c1527ecc93709cf49eada00257183483b706eb6`。

已通過：
- CI #547。
- Deploy Cloud Run #419。
- Deploy Firebase Hosting #365。
- Notes UI Acceptance #130。
- Post-deploy Runtime Acceptance #84。
- Drive Knowledge synthetic backend runtime、exact Firebase release、OAuth redirect、production UI。
- CI/CD stuck-recovery hardening 已有 runtime evidence：Cloud Run acceptance 每 30 秒 heartbeat、660 秒 hard bound、PASS/TIMEOUT/FAIL diagnostics、deploy outer timeout 90 分鐘；workflow-run concurrency 已隔離 ineligible run，避免不合格 workflow_run 取消有效部署。

仍阻塞 Task 9 封板：
- Picker production config：FAIL；Task exit `96` = developer key + app id 缺少。
- Live external AI：FAIL；Task exit `107` = provider + model + API key 未完成 production config。
- Real Google Drive integration fixture：NOT VERIFIED；`DRIVE_ACCEPTANCE_USER_SUB` / `DRIVE_ACCEPTANCE_GOOGLE_FILE_ID` 尚未配置。

下一 concrete gate：只處理上述三個 external production gates，不重做已 PASS 的 CI / Cloud Run / Firebase / synthetic runtime。production secret / credential 變更必須先取得使用者明確確認。

## Just Closed

### #4 — Task 8：智能整理 review UI

狀態：**DONE / PASS**。

封板 evidence：

- final UI acceptance release SHA `78cdb43645f606d63b8a6171e53babec9f26de10`。
- 獨立 `DrivePage` / `DriveSettingsPage`、Drive API facade、`/more/drive` / `/more/drive/settings` navigation 已落地。
- provider-neutral presentation、explicit content consent、cache state、related Note suggestion accept/reject、force re-analysis、partial/failed/skipped fallback 與 manual/degraded behavior 已落地。
- CI #482 / run `37168408452` PASS：backend、deployment scripts、Flutter Analyze、Drive navigation、完整 Flutter tests、Web build、branding verify 全 PASS。
- Firebase Hosting #300 / run `37168500908` PASS：build、release stamp、deploy、Hosting verify、Task UI、Project UI production acceptance PASS。
- Notes UI Acceptance #65 / run `37168620482` PASS：Notes production UI PASS；Drive desktop provider-neutral review、suggestion accept、force re-analysis、settings consent save、mobile review controls、mobile settings 全 PASS；final `drive_ui_acceptance=PASS`。
- Backend/runtime product code在最後兩個 acceptance-only commits 未變；已驗證基線 Deploy Cloud Run #352 / run `37130495284` PASS，Post-deploy Runtime Acceptance #17 / run `37132443415` PASS。
- 專項 checkpoint：`doc/drive_intelligent_organization_review_ui_checkpoint_v0_1.md`。
- Closure progress 已更新為 **4/11 = 36.4%**。

## Next

1. #5 — Task 9：Drive Knowledge production delivery + acceptance（**PARTIAL；剩 3 個 mandatory external gates**）。
2. #6–#9 — Habits / Shopping / Calendar / Activity + Integrations productization。
3. #10 — Integration / foundation tail closure。
4. #11 — Phase 1 final Release Gate / 封板 checkpoint。

## Non-blocking backlog

以下仍需完成，但只有在成為直接 dependency 或進入對應工作包時才提升優先級：

- Attachment central storage/reference strategy。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。
- Concrete AI provider adapter / deployment config；接入時補 provider/model-aware cache invalidation contract 與 external-provider integration evidence。

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