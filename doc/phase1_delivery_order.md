# Life — Active Delivery Order (2026-10-10)

## 本批開發與驗收安排（2026-10-10 最新）

- 新交接表、穩定去重、活動卡片、兩個入口及個人動作已在工作樹實作；開發驗證與 deployed／runtime 驗收分開記錄。細節見 [活動規格](curated_activity_user_features.md)。
- 活動能否開放一般使用者由 admin 在後台設定。AI 管理補強暫緩，僅 AI 管理相關能力限 admin；不把這項限制套用到全部新功能。
- 下一輪合併新活動功能、後台及個人首頁做正式上線驗收。真實 Sheet write scope／版本回執、GCP Job、Google Calendar 與新 SHA 的 CI／staging 尚待驗證；舊版測試站登入已完成。


**Activity scope simplified; all upstream cancelled.** Previous P0–P2 MoC/TDX→Queue Job, 14-day source observations, official workbook scanner and Queue ACK tasks are **removed from the active backlog**, not deferred. Previous failures remain historical records.

1. **Curated pool source implemented:** existing PostgreSQL table, validated batch-upsert, signed-in GET and Flutter list remain the target. Run the dedicated source and real DB gates per new Sheet contract.
2. **獨立 Drive「交接資料」→ GCP Job [APPROVED / NOT VERIFIED]：** ChatGPT 核證後只輸出合格 READY 到 [固定交接 Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit)；Life 每日 Job 讀 READY/ERROR、以 PostgreSQL 永久 event_key/content_hash 去重、成功後版號一致 ACKED 回寫。既有僅 readonly 的 Job 必須調整單表最小寫入授權、網址變更穩定鍵映射；tests/staging 真實 DB／Sheet ACK／Flutter readback PASS 才啟 Scheduler。精選池 45 欄為探索原表，不再是 Life Job 直接來源。詳見 [交接契約](curated_sheet_job_ingestion.md)。不恢復 crawler/Queue 或 Plugin/MCP。
3. **Independent product modules — baseline source implemented, some governance/runtime gates outstanding:** small curated-pool admin/batch summary (no source control), Life internal Drive AI Provider admin [#11](https://github.com/tommylin15/life_assistant/issues/11), feature availability + user nav/Home [#12](https://github.com/tommylin15/life_assistant/issues/12).
4. **本批活動開發 SOURCE IMPLEMENTED，runtime NOT VERIFIED：** 父子卡片／群組分頁、未知費用與押金／證據顯示、限時機會及活動探索兩入口、帳號隔離的收藏／追蹤／Task／Calendar 與 Google popup。使用 additive 0016 的永久 event_key，保留舊 URL identity 相容資料。[Single canonical UX spec](curated_activity_user_features.md)。正式驗收與後台及個人首頁合併；AI 管理補強暫緩；旅遊行程仍為未來項目。
5. **Single consolidated gated V3 acceptance and release — NOT VERIFIED for this SHA:** tests/PostgreSQL/CI, Cloud Run candidate, Hosting, OAuth, runtime/API/UI; existing Phase 1 releases and privacy gates remain independent.

Existing source-job Cloud Run resources are not deleted. Do not restore removed GitHub source cron. [Current state](CURRENT_STATE.md). Consolidated gate matrix: [P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md).
