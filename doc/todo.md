# life_assistant — Active TODO

最後更新：2026-10-04

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #5 — Task 9：Drive Knowledge 正式交付與 production acceptance

狀態：**NOT STARTED**。

依使用者指示，本輪在 Task 8 封板並回寫文件後停止，因此目前沒有開始 Task 9 implementation、migration、deployment 或 production integration work。

Task 9 重新啟動時的第一個 concrete gate：

- 先讀取當時 GitHub `main` 與 runtime evidence，重新確認 Task 8/Task 7 依賴沒有漂移。
- 盤點 true Drive / external-AI production delivery 所需 credential/config contract、migration、runtime/integration acceptance。
- 不把 Task 8 的 mocked deterministic production UI acceptance 誤稱為 Task 9 的真實外部 provider integration evidence。
- 最終仍需 CI、migration、Firebase、Cloud Run、authenticated runtime、true Drive integration evidence 完整後才可封板。

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

1. #5 — Task 9：Drive Knowledge production delivery + acceptance（**NOT STARTED，本輪停止**）。
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