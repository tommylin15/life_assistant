# Life — Active engineering TODO
Updated 2026-10-15. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

| Priority | Work / exit gate | Status |
| --- | --- | --- |
| P0-1 | Verify actual **GAS 07:30 trigger → importer Job Exit 0 → PostgreSQL event_key/content_hash readback → Sheet version-fenced ACK/ERROR** on same execution; separate `data_status=PARTIAL` from technical failure. Prevent duplicate imports. | **NOT VERIFIED**; promoted Job image aligned, execution was NOT_RUN in Release |
| P1-1 | Complete **signed Gemini through logged-in Life `/ai/text` and UI** including 429/502/503/timeout, permission/quotas and no implicit Google Drive content transfer. | Signed synthetic smoke **PASS**, UX E2E **NOT VERIFIED** |
| P1-2 | Verify activities **multi-day search, pagination during updates, old favorites, personal tracking/Task, Google Calendar actual write/readback**; this is functionality-specific, not a reopen of the accepted multi-user isolation gate. | Source/CI **PASS**, these targeted live E2E cases **NOT VERIFIED** |
| P1-3 | Validate **Shopping list + item edit/delete, multiline add and Task deletion** against fresh reload, browser error cases and automated regression. | User manual checks positive; targeted expanded regression **NOT VERIFIED** |
| P1-4 | Drive AI admin/per-user consent, provider failures, **real token/cost/accounting** if introducing budget enforcement; never fabricate spend. | Partial implementation, costs/budget **NOT VERIFIED** |
| P2-1 | 清除 `life-assistant-api` 第 11 版以後的歷史 V2/V3 0% tagged revisions；保存最新 10 版與現役正式流量／staging，要求最新一次 `workflow_run` 後 **exactly 10** 的 API readback。四個 Life Jobs 已查到最近執行或發布依賴，均保留。 | 2026-10-15 audit **63→10 目標、預計刪 53**；apply 結果依執行紀錄判定 |
| P2-2 | Audit dependency/action pinning, public-repository hygiene, access to operational docs, observability, backup restoration and scheduled-job dedupe. | Risk follow-up **NOT VERIFIED** |

**Accepted / removed from active blocker list (2026-10-15):** production Google OAuth human sign-in and production multi-user data isolation — both **PASS by user-reported live human acceptance**. Do not reopen solely because workflow artifacts do not include a human interaction log. Keep automated OAuth and tenant-ownership security tests. See [acceptance](acceptance.md).

**2026-10-15 P0/P1 CI/CD 收斂：** 已歸檔 8 個老舊 workflow（29→21），CI 仍維持四項獨立 gate；移除重複 Flutter navigation 測試，文件專用 SHA 不啟動 staging，Gemini Smoke 改人工按需／現行 Gateway URL，V3 release 後直接跑帶競態保護的最新 10 版清理。以上屬 source 實作；**新 SHA CI/staging、最後 10 版 GCP readback 應分層驗收，未讀回前不能標 DONE**。

Release reference: [latest verified original source SHA and actions](CURRENT_STATE.md). New `main` documentation commits start a new SHA and do not inherit production evidence. A standard `main` push runs the four CI jobs and staging-only flow; production promotion has its distinct manual V3 release gate. Do not run a second importer on top of GAS without checking the execution ledger.