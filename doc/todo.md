# life_assistant — Active TODO

最後更新：2026-10-09（Calendar #8 DONE，8/11 = 72.7%；原 11-package Phase 1 Final Gate 仍 PARTIAL）

> 本檔記錄**尚待處理**工作。正式執行優先序以 `phase1_delivery_order.md`，真實證據以 `acceptance.md` / Actions / runtime 為準；歷史 CI/CD V2、已清理清單詳見 `v3_cleanup_and_cutover_inventory.md`。

## Just Closed — #8 Calendar

**DONE / PASS；原 Phase 1 累計 8/11（72.7%）。** 完整 SHA `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7`；[CI 37882690249](https://github.com/tommylin15/life_assistant/actions/runs/37882690249)、[V3 37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014)、[Firebase 37885328134](https://github.com/tommylin15/life_assistant/actions/runs/37885328134)、[真實 Calendar 37885330178](https://github.com/tommylin15/life_assistant/actions/runs/37885330178)、[桌面/手機 UI 37885544932](https://github.com/tommylin15/life_assistant/actions/runs/37885544932)、[Bootstrap 37882690327](https://github.com/tommylin15/life_assistant/actions/runs/37882690327) PASS。Mocked UI mutation 不假裝成真實 Google API 寫入；詳見 `calendar_productization_checkpoint_v0_1.md`。

## Current — Post-Calendar P0

**台灣免費活動探索與報名追蹤（M0）：NOT IMPLEMENTED / NOT VERIFIED；下一優先。** 正式規格 `taiwan_free_events_discovery_plan.md`：
- 盤點可合法利用的官方原始公告、RSS/API、主辦及報名頁；聚合站僅候選，不在 robots／ToS／授權未釐清前啟用自動擷取。
- 14 天來源新鮮度／免費及資格判定／報名窗口標註品質基線，對缺值保留 UNKNOWN；必須真實觀測，不能製造 14 天結果。
- 先完成 Source Registry 和 Organizer/Event/Session/Registration Opportunity 最小 schema 審查，再進 M1 mutation migration。
- 追蹤 MVP：M1 官方 adapter/增量去重/AI 0 無變更；M2 Flutter 候選+admin-only 健康；M3 用戶獨立 opt-in reminders/tasks/notes；M4 06:00/18:00 Cloud Scheduler → authenticated Run → PostgreSQL，通過後才停用 ChatGPT 過渡掃描。

**Phase 1 scope-freeze：** 活動 MVP 插入優先序但不自動變更原 11 包分母；是否納入最終 Phase 1 release blocker 需另明示治理決策，不能推斷。

## Next — 原 Phase 1 工作包

- #9 Activity / Execution Log + Integrations 產品化 — NOT STARTED。
- #10 Integration / Foundation tail（含獨立 Google/provider failure、Bridge/MCP、附件、條件式 SQLite migration）— NOT STARTED。
- #11 Phase 1 Final Release Gate — NOT STARTED；#8 DONE 不代表全案 DONE。

## Non-blocking backlog

以下仍需完成，但只有在成為直接 dependency 或進入對應工作包時才提升優先級：

- Attachment central storage/reference strategy。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。
- Drive Knowledge provider-health regression：#63 exit `91`（historical Gemini-only），#70 exit `93`（Gemini + OpenRouter），均仍為歷史 FAIL evidence。舊 Codex-first 為歷史政策；最新 main 的順位為 Gemini Flash → Gemini Flash-Lite → Groq → OpenRouter → Shared Codex，CI run 37874176801 PASS，新路由正式 deployment／真實 model E2E 仍 NOT VERIFIED。只呼叫 omniAgent 私有 shared Cloud Run；其認證由共用服務專屬 `omniagent-shared-codex-auth` 管理，life_assistant 不新建、不讀取、不複製任何 Codex Secret，舊 `janus-mart-codex-auth` 不作為消費端來源。

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
