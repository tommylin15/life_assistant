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


### P0 新增工項 — 免費／高性價比活動自動候選入庫與跨來源去重（NOT IMPLEMENTED）

- [ ] 將合法來源掃描得到的**免費**或**已查證福利價值至少為不可退實際支出 3 倍**的活動，透過經授權的 FastAPI 批次入口寫入共用 PostgreSQL 候選資料；不可把 ChatGPT 過渡通知當作已入庫。費用需包含手續費/材料費；可退保證金分開記錄及註明退還條件。估值不明維持待確認，不偽稱達標。
- [ ] Additive migration 擴充活動費用、保證金、確定福利、估值證據、查證時間與狀態；保留既有免費資料和來源驗證 gate。建立 authenticated / rate-limited / idempotent candidate batch API，僅允許候選資料寫入，禁止直接設定 verified 或建立個人 Calendar、提醒、Task、Note。
- [ ] **強制去重（release blocker）**：優先以 `source_id + external_event_id`、官方活動 ID、canonical 官方 URL 去重；去除 URL tracking params，維持跨站 alias / source mapping；再以主辦單位＋活動名稱＋日期／地點產生疑似重複待審，不得自動合併不同場次、票種、報名窗口或同名不同活動。資料庫唯一鍵＋交易式 UPSERT＋併發鎖，確保兩輪掃描、重試、不同網站引用同一官方活動時**一個 Event 可對應多個來源，但每個 Session／Opportunity 不重複**。不確定的跨站比對不刪資料，轉人工審查。
- [ ] **通知去重**：以 canonical event/session/opportunity + semantic version + recipient 作唯一投遞鍵；同一活動已通報不再推送，只有新報名窗口、取消、延期、費用或福利重大變更才重新通知。不得以來源文字更新產生重複通知；保留最小 tombstone 防過期清理後重報。
- [ ] 測試涵蓋同站重掃、跨站同活動、不同場次/票種、URL tracking、併發 4 worker、重試/中斷、未知欄位、3 倍福利門檻、通知 exactly-once 語意與禁止個人資料 mutation；CI → V3 deployment → production PostgreSQL migration/readback → Flutter 清單與真實排程逐項 PASS 才可 DONE。

詳細契約：[`free_events_candidate_ingestion_contract.md`](free_events_candidate_ingestion_contract.md)。本工項與現有 M1–M4 合併執行，不另外建立重複掃描系統。

**Phase 1 scope-freeze：** 活動 MVP 插入優先序但不自動變更原 11 包分母；是否納入最終 Phase 1 release blocker 需另明示治理決策，不能推斷。

## 2026-10-09 P1 優先補齊 + P0/P1 聯合驗收 readback

- 已核實的既存 staging live：version `e3a6dd23aec06848`、`release.txt` = `eb9f60c3413a8e5216318888a6456a1c464d8cab`、兩條 rewrite 均 `pinTag` 到 `life-assistant-api-00197-fug`；[readback 37944737101](https://github.com/tommylin15/life_assistant/actions/runs/37944737101) PASS。
- 現況阻礙：staging `/auth/login` **仍回 production callback**；P0 `/api/v1/free-events/status` staging/production 都 404（[readback 37945021056](https://github.com/tommylin15/life_assistant/actions/runs/37945021056)）；因此沒有新的後端 runtime 或 P0 真實 aggregate 驗收 PASS。
- 已修正 staging OAuth 白名單來源選擇與 Google incremental callback/token exchange；加入單元測試及 staging-only clone rollback 安全 readback；建立 `v3-p0-p1-joint-acceptance.yml` 手動唯讀聯合 Gate。修碼與 CI 不等於 staging 重新發布。
- 待辦：Google OAuth Client 追加固定 staging callback（保留正式 callback）、本次完整 SHA V3 candidate／Preview gate、真實 Google staging 登入與證據、stage-only live 更新與回復、P0 owner session 實際 aggregate 回覆／去重計量、聯合 runtime UI E2E。舊 staging version 是**可定位回復候選**，尚未證實完整 OAuth，不能假冒 verified fallback。
- 雙工項維持 **PARTIAL / NOT VERIFIED**；已確認正式 Hosting/version 與 Cloud Run traffic 讀取能力存在，但未更新正式站或變更正式 traffic。

## 2026-10-09 P0/P1 工程啟動續作

- **P0 統計讀回替代實作：** 新增只有明確 `ALLOWED_GOOGLE_EMAIL` owner session 才可使用的聚合 API `GET /api/v1/free-events/status` 與單元測試；GitHub Actions Cloud Logging 權限原 FAIL 未解除，正式 owner HTTPS／實際 rows/14-day/去重計量仍 **NOT VERIFIED**。後續需按 V3 release gate 發布驗證，不可用測試資料冒充結果。
- **P1 staging 固定網址：** 新增版本／pins／前版 SHA readback 的 fail-closed verifier + 12 項以上回歸測試、CI gate 與 manual-only `v3-staging-live.yml`。它具有 staging-only exact-version clone 與失敗回復程式路徑，正式 production 隔離條件必須 readback；**固定 staging 真實 OAuth E2E、首次可信前版 baseline、workflow GCP runtime 與 live URL 驗收尚未 PASS**。預設 preflight，不會因 main push 直接更新 staging live。詳細見 `deployment_runbook.md`。
- 原 Phase 1 仍 **8/11**；P0、P1 都不能因 implementation／CI 完成便標記 DONE。

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
