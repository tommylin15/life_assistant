# Life — Active engineering TODO
Updated 2026-10-15. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

| Priority | Work / exit gate | Status |
| --- | --- | --- |
| P0-1 | GAS 07:30 → importer Execution 終態 → PG 版本／Sheet ACK 讀回；確認正式 Job image 已包含跨流程排他鎖，再做同輪驗收（禁止因驗收重觸發匯入）。 | **PARTIAL**：主線新增 DB 排他鎖與測試 CI PASS；Sheet 實讀 54 筆＝ACKED 53／ERROR 1；GCP 唯讀掃到 16 個歷史 Execution。正式 Job 與既有 production digest／執行契約 **PASS**（[唯讀 #38725678405](https://github.com/tommylin15/life_assistant/actions/runs/38725678405)）；新版排他鎖仍在 staging、GAS 真實觸發來源與同輪 Sheet/PG 版本讀回 **NOT VERIFIED** |
| P1-1 | Complete **signed Gemini through logged-in Life `/ai/text` and UI** including 429/502/503/timeout, permission/quotas and no implicit Google Drive content transfer. | Signed synthetic smoke **PASS**, UX E2E **NOT VERIFIED** |
| P1-2 | 驗證活動跨日搜尋、分頁新活動插入、舊收藏、個人追蹤/Task、Google Calendar 寫入讀回。 | **PARTIAL**：已新增固定 as_of 分頁快照及刷新重置，PostgreSQL 測試 PASS；既有收藏／Calendar 單元測試保留；真人 Calendar 寫入與新版正式 URL **NOT VERIFIED** |
| P1-3 | 購物清單及品項編輯/刪除、一次新增多品項、重新載入、待辦刪除不白畫面與權限回歸。 | **PARTIAL**：已增購物批次排序鎖、Flutter 真實 widget 交互回歸、保留 Task nested Navigator 刪除測試；新版 CI 四項 PASS。正式使用者實際重新載入與跨帳號 runtime **NOT VERIFIED** |
| P1-4 | Drive AI admin/per-user consent, provider failures, **real token/cost/accounting** if introducing budget enforcement; never fabricate spend. | Partial implementation, costs/budget **NOT VERIFIED** |
| P2-2 | Audit dependency/action pinning, public-repository hygiene, access to operational docs, observability, backup restoration and scheduled-job dedupe. | Risk follow-up **NOT VERIFIED** |

**01–03 開發／PostgreSQL／Staging 最新驗收：PASS（2026-10-15）**：同 SHA `8d27207` [CI #38719801492](https://github.com/tommylin15/life_assistant/actions/runs/38719801492) 四項 PASS；[V3 #38720078074](https://github.com/tommylin15/life_assistant/actions/runs/38720078074) 固定 Staging PASS、活動交接 DB 檢查 + Shopping rollback-only runtime PASS，修復了舊 [#38715747623](https://github.com/tommylin15/life_assistant/actions/runs/38715747623) 的新驗收失敗，production traffic unchanged。上表 P0-1 / P1-2 / P1-3 **只保留外部來源及正式使用者 E2E**；不要把已 PASS 的 DB/CI/Staging 再列成待修 bug。

**Closed / removed from active blockers:** P2-1 Revision 清理 **PASS**（68→10、刪 58、未刪 Service/Job、live unchanged），證據見 [Release #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751)。P0/P1 CI/CD workflow 收斂 **PASS**（同 SHA CI + staging）。

**Accepted / removed from active blocker list (2026-10-15):** production Google OAuth human sign-in and production multi-user data isolation — both **PASS by user-reported live human acceptance**. Do not reopen solely because workflow artifacts do not include a human interaction log. Keep automated OAuth and tenant-ownership security tests. See [acceptance](acceptance.md).

**2026-10-15 P0/P1 CI/CD 收斂：DONE（有 CI/staging/真實 GCP readback 證據）。** 已歸檔 8 個過時 workflow（29→21），保留四項 CI gate；純文件修改不自動 staging；Gemini synthetic smoke 改按需執行。最後 main 程式 SHA `23d898c` 的 [四項 CI #38674814026](https://github.com/tommylin15/life_assistant/actions/runs/38674814026) 與 [staging/retention Release #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751) **PASS**；GCP 讀回 **68→10**、刪除 **58**、正式流量不變、四個 Life Jobs 均未刪除。此 DONE 不涵蓋其他功能尚未驗證的 Live E2E。

Release reference: [latest verified original source SHA and actions](CURRENT_STATE.md). New `main` documentation commits start a new SHA and do not inherit production evidence. A standard `main` push runs the four CI jobs and staging-only flow; production promotion has its distinct manual V3 release gate. Do not run a second importer on top of GAS without checking the execution ledger.