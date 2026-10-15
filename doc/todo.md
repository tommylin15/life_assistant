# Life — Active engineering TODO
Updated 2026-10-16. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

| Priority | Work / exit gate | Status |
| --- | --- | --- |
| P1-1 | Complete **signed Gemini through logged-in Life `/ai/text` and UI** including 429/502/503/timeout, permission/quotas and no implicit Google Drive content transfer. | Signed synthetic smoke **PASS**, UX E2E **NOT VERIFIED** |
| P1-4 | Drive AI admin/per-user consent, provider failures, **real token/cost/accounting** if introducing budget enforcement; never fabricate spend. | Partial implementation, costs/budget **NOT VERIFIED** |
| P2-2 | Audit dependency/action pinning, public-repository hygiene, access to operational docs, observability, backup restoration and scheduled-job dedupe. | Risk follow-up **NOT VERIFIED** |

**02／03 使用者正式版人工驗收：PASS／DONE（2026-10-15）**。使用者明確回報「02,03驗收完畢」：02 購物清單／品項修改、刪除、批次新增、重載及待辦刪除不白畫面；03 活動跨日搜尋／分頁、收藏、個人待辦／追蹤及 Calendar 操作與讀回。已從 active backlog 移除 P1-2／P1-3；正式版操作是使用者回報，非自動化每條 API log。原有 CI/正式部署證據分開保留見 [acceptance.md](acceptance.md) 與 [CURRENT_STATE.md](CURRENT_STATE.md)。**01 已於 2026-10-16 由真實 Execution + Sheet／PG 版本比對 PASS 結案**。

**01–03 本批全部 PASS／DONE（2026-10-16）**：01 匯入器 [Execution ds4bq](https://console.cloud.google.com/run/jobs/executions/details/us-central1/life-assistant-free-events-ds4bq?project=gen-lang-client-0593591102) 2026-10-16 07:34:20 台北時間成功，Sheet 59 筆／58 ACKED／1 ERROR；[PostgreSQL readback #38825509671](https://github.com/tommylin15/life_assistant/actions/runs/38825509671) 精確比對本輪 5 筆新 ACKED 版本全部 PASS；02／03 使用者正式版人工驗收 PASS。**01 已從 active backlog 移除**。Apps Script Trigger ID 未直接核證、來源單筆 ERROR 屬獨立可觀測性／資料品質追蹤，不作為本批功能結案的阻擋。

**01–03 正式部署／Hosting：PASS（2026-10-15）**：[V3 #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151) 完成 production promotion、回滾演練、importer Job 映像同 digest；[Hosting #38738435372](https://github.com/tommylin15/life_assistant/actions/runs/38738435372) 同 SHA live readback PASS。這只關閉部署 gate，不代替 GAS 同輪匯入或使用者 E2E。

**01–03 開發／PostgreSQL／Staging 最新驗收：PASS（2026-10-15）**：同 SHA `8d27207` [CI #38719801492](https://github.com/tommylin15/life_assistant/actions/runs/38719801492) 四項 PASS；[V3 #38720078074](https://github.com/tommylin15/life_assistant/actions/runs/38720078074) 固定 Staging PASS、活動交接 DB 檢查 + Shopping rollback-only runtime PASS，修復了舊 [#38715747623](https://github.com/tommylin15/life_assistant/actions/runs/38715747623) 的新驗收失敗，production traffic unchanged。上表僅保留尚待核實的外部來源與系統整合事項；P1-2／P1-3 已經使用者正式人工驗收 PASS 並自 active backlog 移除。

**Closed / removed from active blockers:** P2-1 Revision 清理 **PASS**（68→10、刪 58、未刪 Service/Job、live unchanged），證據見 [Release #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751)。P0/P1 CI/CD workflow 收斂 **PASS**（同 SHA CI + staging）。

**Accepted / removed from active blocker list (2026-10-15):** production Google OAuth human sign-in and production multi-user data isolation — both **PASS by user-reported live human acceptance**. Do not reopen solely because workflow artifacts do not include a human interaction log. Keep automated OAuth and tenant-ownership security tests. See [acceptance](acceptance.md).

**2026-10-15 P0/P1 CI/CD 收斂：DONE（有 CI/staging/真實 GCP readback 證據）。** 已歸檔 8 個過時 workflow（29→21），保留四項 CI gate；純文件修改不自動 staging；Gemini synthetic smoke 改按需執行。最後 main 程式 SHA `23d898c` 的 [四項 CI #38674814026](https://github.com/tommylin15/life_assistant/actions/runs/38674814026) 與 [staging/retention Release #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751) **PASS**；GCP 讀回 **68→10**、刪除 **58**、正式流量不變、四個 Life Jobs 均未刪除。此 DONE 不涵蓋其他功能尚未驗證的 Live E2E。

Release reference: [latest verified original source SHA and actions](CURRENT_STATE.md). New `main` documentation commits start a new SHA and do not inherit production evidence. A standard `main` push runs the four CI jobs and staging-only flow; production promotion has its distinct manual V3 release gate. Do not run a second importer on top of GAS without checking the execution ledger.