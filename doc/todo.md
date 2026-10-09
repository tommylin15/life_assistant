# life_assistant — Active TODO

最後更新：2026-10-09（Calendar #8 DONE，8/11 = 72.7%；原 11-package Phase 1 Final Gate 仍 PARTIAL）

> 本檔記錄**尚待處理**工作。正式執行優先序以 `phase1_delivery_order.md`，真實證據以 `acceptance.md` / Actions / runtime 為準；歷史 CI/CD V2、已清理清單詳見 `v3_cleanup_and_cutover_inventory.md`。

## Just Closed — #8 Calendar

**DONE / PASS；原 Phase 1 累計 8/11（72.7%）。** 完整 SHA `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7`；[CI 37882690249](https://github.com/tommylin15/life_assistant/actions/runs/37882690249)、[V3 37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014)、[Firebase 37885328134](https://github.com/tommylin15/life_assistant/actions/runs/37885328134)、[真實 Calendar 37885330178](https://github.com/tommylin15/life_assistant/actions/runs/37885330178)、[桌面/手機 UI 37885544932](https://github.com/tommylin15/life_assistant/actions/runs/37885544932)、[Bootstrap 37882690327](https://github.com/tommylin15/life_assistant/actions/runs/37882690327) PASS。Mocked UI mutation 不假裝成真實 Google API 寫入；詳見 `calendar_productization_checkpoint_v0_1.md`。

## Current — Post-Calendar P0

**台灣免費活動探索與報名追蹤（M0）：PARTIAL（來源清冊/離線量測工具/8 tests/完整 CI PASS；14 天真實來源觀測、逐站合法存取審查與 runtime NOT VERIFIED）；下一優先。** 正式規格 `taiwan_free_events_discovery_plan.md`：
- **已完成**：`data/free_events_m0_sources.json` 10 個候選來源與 fail-closed 存取 Gate；`scripts/free_events_m0_baseline.py` 和 `backend/tests/test_free_events_m0_baseline.py`，CI #37892185617 PASS。**M1 開發持續中**：六表 Alembic 0011、資料正規化/去重/來源控管、M1 JSONL 預檢、文化部離線 Adapter、原子 PostgreSQL upsert service 已完成程式開發；M2 verified-only API／「更多」免費活動 Flutter 清單與 widget tests 已提交 main（最新完整 CI 待驗證），詳見 `free_events_m1_checkpoint.md`。**新增已通過**：Alembic 0011→0012（共七表）、隔離 PostgreSQL 16 migration/真實 upsert/4 路併發／租約退避 12 tests [CI #37904115588](https://github.com/tommylin15/life_assistant/actions/runs/37904115588) PASS，M2 24h freshness gate。**未完成**：逐站授權檢查、14 天真實觀測、production PostgreSQL／V3 rollout、M2 production UI E2E、正式 Batch executor 與個人 opt-in。
- 盤點可合法利用的官方原始公告、RSS/API、主辦及報名頁；聚合站僅候選，不在 robots／ToS／授權未釐清前啟用自動擷取。
- 14 天來源新鮮度／免費及資格判定／報名窗口標註品質基線，對缺值保留 UNKNOWN；必須真實觀測，不能製造 14 天結果。
- Source Registry、Organizer/Event/Session/Registration Opportunity schema 與 M1 additive migration 0011 + lease 0012 已寫入 main，隔離 PostgreSQL CI PASS；正式 DB migration 與 live source ingestion 尚未執行。
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

## Deployment-first live-source checkpoint — 2026-10-09

- 來源目前僅核准文化部官方藝文活動 JSON（資料集政府資料開放授權條款第 1 版）；其他九站 disabled。觀測批次／PostgreSQL 0013 source observations、新 CI 已寫入 main；正式部署與來源首次執行須以對應 workflow/job logs 確認，否則仍 NOT VERIFIED。
- 實際排程：GitHub Actions UTC 22:00/10:00（台灣 06:00/18:00）暫行，待 GCP Cloud Scheduler M4 完成可再移交；14 天有效樣本自真正 DB observed_at 累積，不能補日期。
