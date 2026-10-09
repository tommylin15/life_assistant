# Taiwan Free Events — M1 Implementation Checkpoint

## M1 先行開發 checkpoint — 2026-10-09

**狀態：PARTIAL（實作／單元測試、隔離 PostgreSQL 16 migration/transaction/concurrency PASS；正式 Cloud Run／production DB／來源擷取／14 天觀測 NOT VERIFIED）。**

- **資料結構**：additive Alembic `20261009_0011`，新增 `free_event_sources`、`free_event_organizers`、`free_events`、`free_event_sessions`、`free_event_registration_opportunities`、`free_event_evidence` 六表。保持公用事件共用一份，不納入 user/sub 個人物件；場次/票種分離、報名開啟時間 nullable、全天結束日期 exclusive、證據只保留必要欄位；不碰既有業務表。另加 additive Alembic `20261009_0012` 的 `free_event_ingestion_leases` 一表，共 **7 張新增表**。release revision guard 已更新到 0012；**production DB migration 未執行**。
- **來源/費用的後端保護**：`fetch_enabled` 只有 `reviewed_with_evidence` + license evidence 才允許在 SQL 層為 true；未驗證活動不可標正式 verified，free claim 不可附正費用且需正式報名網址。現行來源清冊所有擷取開關仍 false。
- **確定性正規化**：`EventCandidate`／`CandidateSession`／`CandidateOpportunity` Pydantic 校驗，HTTPS 公開 URL、明確時區、distinct session/registration key、不得從未知數推費用/報名時刻；跨來源只有同一已核實官方 URL 才可合併，任何內容衝突需人工檢視。無變更或規則已足夠的資料 AI 呼叫必須 0。
- **離線預檢 CLI**：`python scripts/free_events_m1_dry_run.py reviewed_candidates.jsonl`，最多 5,000 筆 / 10MiB，列出重複、衝突、未授權來源及未知欄位，永不連網、不寫 SQL、不發布提醒/待辦/筆記。
- **文化部資料 Adapter**：`python scripts/free_events_moc_offline.py downloaded_official_moc.json`，只讀預先合法取得的官方 JSON，將 UID / showinfo 場次轉結構化記錄；不把 `onSales=false` 或 `price=免費` 直接當成可確認的免費或報名可用，不推測日期精度、報名開放時間；即使來自政府資料集仍須經來源 Gate 與人工核實。
- **測試/CI**：M1 模型、Alembic、資料契約、manifest、CLI、MoC Adapter、PostgreSQL `ON CONFLICT` SQL/permission gate 已新增測試。來源入庫修正 SHA `c86ef14db34affe57db1fcc1157e34cac619d0c2`，[CI #37895465333](https://github.com/tommylin15/life_assistant/actions/runs/37895465333) backend **463 tests PASS**、deployment-scripts PASS，Flutter 完整結果待 readback。前一個不含 PG ingest 的 `206fe35ec6b0d0afefb7649de2a07d0d428af001` [CI #37894866290](https://github.com/tommylin15/life_assistant/actions/runs/37894866290) 全 PASS。歷史中間 commit `50e3e67` CI backend FAIL 來自測試 mock Result 和 bind params 判定，已修正且最新 backend PASS；**不將歷史失敗隱匿為 PASS**。
- **PostgreSQL 交易式入庫 service（程式／SQL contract 與隔離 PostgreSQL 16 實測 PASS）**：`backend/app/services/free_events_ingest.py` 已實作來源表 `SELECT FOR UPDATE` 權限鎖、批次數量上限（100 場次/500 報名機會）、活動/主辦/場次/報名機會的 `ON CONFLICT` 去重與 `RETURNING`、證據 fingerprint 去重。活動正式驗證只由人工審核授權；資料更動會標 stale，未更動才保留原驗證狀態；報名機會欄位有異動即撤銷已核實旗標。**此 service 尚未經正式入口呼叫／production DB migration 未執行**；CI 獨立 sidecar 已驗證同時四路重試的去重效果，不冒充 production runtime。
- **尚缺**：已授權/節流的官方擷取 Adapter、14 天真實累積/匯入持久化、batch execution／AI 批次持久化、Cloud Run 正式 migration 後的 live table readback、M2 正式瀏覽器 UI E2E、M3 使用者 opt-in、M4 Scheduler/部署。隔離 CI PostgreSQL 的 migration、upsert、concurrent lease 測試已 PASS，但正式環境仍未驗證。模型 migration 是在 main 的**候選程式碼**，不是 production 已套用 schema 的證據。AI 現在是 0 呼叫因為未啟動，不代表真實供應商 E2E 通過。
- **14 天觀測與 M1 並行**：保留既有 ChatGPT 06:00/18:00 過渡候選掃描（不能冒充 PostgreSQL observation store）。正式計時須從可靠儲存且合法取得的來源觀測開始，缺日不能回填虛構紀錄。M0 仍 PARTIAL，不阻擋 M1 研發，但保留 M0–M4 正式 MVP gate。

## 下一實作次序

1. 在來源條款審查後先接文化部/TDX 官方 licensed endpoint，添加 timeout/rate/size guard；保留聚合站停用。
2. 隔離 PostgreSQL 16 migration 0011→0012、約束／upsert／併發已 PASS；後續在正式 V3 deploy gate 時另做 production DB revision 與 table readback，勿將 CI sidecar 的合成活動寫到 GCP。
3. 已實作 durable lease/claim、來源授權鎖、5→10→20 分鐘指數退避、最高 360 分鐘、來源正常間隔；下一步建正式授權來源 Adapter 與 bounded batch executor、真實觀測 store。暫時來源故障不得當活動取消，相同 fingerprint 不觸發 AI。
4. 由真正 verified event source 與官方 registration 證據開放 M2 Read API/Flutter；勿在 NULL 開放時間時建立精確提醒。
5. M0 14 天正式觀測照常進行；驗收證據不足維持 NOT VERIFIED，不延後其它低風險程式開發。

## Parallel M2 verified-only preview (2026-10-09)

- **Backend implementation:** authenticated GET `/api/v1/free-events?limit=20&offset=0`，唯讀且 `Cache-Control: no-store`。SQL 只允許 `verification_status=verified`、核實時間與官方來源、來源 fetch 已獲審核授權、未取消且未結束的場次，以及已人工核實的免費／條件免費報名機會；未核實與資料已撤銷者不能曝光。
- **不假造報名可用性：** `window_confirmed_open` 必須官方 `open` 狀態和兩個明確時間邊界都核實且現在處於期間；不代表尚有名額，API 永遠附上原站二次確認提示，NULL 開放時間維持未知。
- **Flutter:** `/more/events`（「更多」→「免費活動探索」）唯讀清單、空資料/錯誤狀態、含來源/資格/時間的精簡卡片、明示外站連結。沒有個人提醒/待辦/筆記/Calendar mutation，也不自動開啟報名網址。已補模擬資料的桌面/手機 widget tests。
- **驗收分級：** M2 Flutter + Backend [CI 37896364737](https://github.com/tommylin15/life_assistant/actions/runs/37896364737) **全 PASS**；早期後端修正 commit `dbef01a9e547a6e199f62f217cfd4b750a20b184` [CI 37896041000](https://github.com/tommylin15/life_assistant/actions/runs/37896041000) PASS（Backend 472 tests、Flutter、deployment-scripts），但該 commit 尚未包含 Flutter UI。
- **不要將程式碼候選冒充正式產品化：** PostgreSQL 0011 尚未證實套用正式 DB，來源 registry 全部 fetch=false，因而目前線上不應宣稱有任何可報名活動；M2 production UI/E2E + live provider/來源 freshness 與 M0 14 天真實觀測均 **NOT VERIFIED**。

## M1 isolated PostgreSQL / durable claim release checkpoint (2026-10-09)

- **migration 0011 + 0012**：正式 Alembic migration 順序在 GitHub Actions 使用獨立 `postgres:16` sidecar，從空 DB upgrade 至 0010→0011→0012，並核對實際 `alembic_version=20261009_0012`、7 個新 public event tables 與既有 `tasks` table 存在。
- **真实 SQL / concurrency**：`backend/tests/test_free_events_postgres_integration.py` **12 tests PASS**，含來源 SQL CHECK、防止未授權寫入、活動/場次/報名/證據 `ON CONFLICT` 去重、4 worker concurrent upsert、人工已核實資料 unchanged 保留／changed 撤銷、24h 來源/活動/報名驗證新鮮度、4 worker source-lease 一人取得、逾時可重領、token fencing、失敗指數退避及來源撤銷不得標示成功。
- **證據**：來源 commit `0f55fe239e3742d4e1fe6bb93aaf63f91167a6da`，GitHub [CI #37904115588](https://github.com/tommylin15/life_assistant/actions/runs/37904115588) `free-events-postgres` + backend + deployment-scripts **PASS**；在此文件更新時 Flutter 工作仍待 CI 最終 readback。先前 [CI #37903633583](https://github.com/tommylin15/life_assistant/actions/runs/37903633583) PostgreSQL 0011／7 integration tests 全 PASS。先前中間測試因跨方法計數干擾產生 FAIL，已改為按來源/event ID 的 test-level assertions；`0012` 的真實 PostgreSQL CI PASS 不是以 mock 代替。
- **運作限制**：`backend/app/services/free_events_lease.py` **只含供未來正式 executor 使用的 claim/finish primitives**，沒有排程工作、沒有自動 HTTP、沒有 API endpoint、沒有變更 GCP Secrets/IAM；租約 `last_checked_at` 只算 attempted check，不是 M0 的獨立有效來源觀測。所有 registry `enabled_for_fetch=false`，production PostgreSQL 0012 / V3 runtime / Firebase hosting / M2 UI E2E 仍 **NOT VERIFIED**。
- **source of truth**：GitHub main 與 Actions 真實 readback。既有已部署 Cloud Run 最後驗證仍為 Calendar release SHA `5c8d2fca8c9b`，**不宣稱新活動功能已在正式環境上線**。

## 2026-10-09 正式部署與真實來源觀測啟動 gate

- 使用者已核准：先以既有 V3 GitHub Actions → public GHCR → Cloud Run 發布 M1/M2，同步擷取合法官方真實活動，14 天實測品質驗收持續累積而不阻塞修正。
- **官方來源審核 PASS（僅 `moc_events_all`）**：文化部 `https://data.gov.tw/dataset/6478` 公告開放授權條款第 1 版、每日更新，提供 JSON 資源連結 `https://cloud.culture.tw/frontsite/trans/SearchShowAction.do?method=doFindTypeJ&category=all`；該公開 dataset JSON 不等於另份需申請 `uk` 的介接 API。只用固定 HTTPS JSON URL，無 HTML scraper、無 API key、禁止 redirect／代理、30 秒 request timeout 與 16MiB response cap。其餘 9 個來源維持停用／待查。
- **真實觀測 Ledger**：Alembic `20261009_0013` 新增 `free_event_source_observations`，含真實觀測時間、回應 fingerprint、來源總筆數／候選接受／拒絕／未知費用／未知報名時刻、是否完整覆蓋來源；日期不能從合成 fixture 回填。每輪來源最多抽樣匯入 400 筆（超過為不完整抽樣）；費用/報名開始未核實絕不標「free/open」。
- **觀測執行**：`backend/scripts/run_free_events_moc_batch.py` 以 PostgreSQL source lease 鎖定 12h，不重複攝取、失敗分級退避；`free-events-moc-observations.yml` GitHub cron UTC 22:00／10:00，即 Asia/Taipei 06:00／18:00（暫代正式 GCP Scheduler M4）。必須在 Cloud Run Job 正式執行成功、資料庫實際 observation readback 後，才能標示首輪「開始」PASS。排程定義提交不等於已執行。
- **正式發布 Gate**：V3 workflow 更新為 candidate/preview/真實 provider 前置驗收 PASS → 由 `life-assistant-db-migrate` 同 release image 執行 additive 0013 + table revision check → 100% promotion → live runtime/rollback/revision-retention；Firebase Hosting 另依正式 Hosting workflow 發布。不能因 CI PASS 當做已部署。
- **逐日判定**：M0 初始日期以第一筆正式 `free_event_source_observations` 的真實 `observed_at` 為準，不能倒填；連續 14 天＋人工來源/費用/報名品質檢查均 PASS 才可封板。M2 對未人工核實的報名與免費活動仍保持空清單。


## 2026-10-09 Owner-only log-free DB readback implementation (not runtime closure)

- 新增 `GET /api/v1/free-events/status` owner-only 聚合讀取，重用現有 `scripts.read_free_events_status.readback`：必要條件是真實已驗證 Google session 且 `ALLOWED_GOOGLE_EMAIL` 有設定並完全相符；未登入 401、非 owner 或 allowlist 缺失 403，`Cache-Control: no-store`。只讀已存在 PostgreSQL 聚合數量、日期與嚴格 verified-only UI predicate，不修改 DB／個人資料，不新增 GCP IAM／Secrets／Log 權限。
- 新增 `backend/tests/test_free_events_owner_status.py` 驗證拒絕非 owner、deny-by-default、只讀回覆；這提供替代 Cloud Logging 的最小 owner-visible evidence path，**不是讓 GitHub Actions 的 deployer 自動取得 end-user session**。
- **仍未驗證：** 新 API 的正式 V3 release / production runtime / 真實 owner HTTPS readback 尚待獨立驗收；舊 GitHub Actions Cloud Logging 讀回依舊 FAIL，不能稱既有 Issue #8 已解除。須在正式 Owner session 讀到實際統計數字及對應頁面／稽核紀錄後才將 DB count 標 PASS。

## 2026-10-09 Production factual readback attempt — explicit blocker

- **Deployment evidence PASS:** V3 [run 37919689731](https://github.com/tommylin15/life_assistant/actions/runs/37919689731), Firebase Hosting [run 37923455110](https://github.com/tommylin15/life_assistant/actions/runs/37923455110), Ministry of Culture source Cloud Run Job [run 37923457846](https://github.com/tommylin15/life_assistant/actions/runs/37923457846) all completed successfully. Source Job success is **not** accepted row count.
- **Readback implementation:** added `backend/scripts/read_free_events_status.py` (read-only transaction, exact production `verified_catalog_query` count, source observation ledger, current event/session/opportunity counts, Taiwan day coverage), and `.github/workflows/free-events-live-readback-once.yml` (existing WIF + transient Job argument override; no schema writes, no new source/permissions). [CI run 37935622309](https://github.com/tommylin15/life_assistant/actions/runs/37935622309) **PASS**.
- **Runtime partial acceptance:** [readback run 37935622371](https://github.com/tommylin15/life_assistant/actions/runs/37935622371) first verified immutable GHCR Job image and DB configuration, then executed the read-only Cloud Run `life-assistant-db-migrate-rn7jp` successfully (**execution PASS**). Subsequent **aggregate result retrieval FAIL**: existing WIF deployer received `gcloud logging read PERMISSION_DENIED: Permission denied for all log views`. No data count was visible to the validator; cannot infer values from a successful task.
- **Current factual statuses:** actual PostgreSQL counts / accepted source observations / unique activities **NOT VERIFIED**; actual count of eligible items shown on logged-in UI **NOT VERIFIED**; true duplicate suppression **NOT VERIFIED** (unique DB keys are guaranteed by schema but don't quantify prevented upserts); 14 contiguous days **PARTIAL**. Source quality and official registration reviews remain gates even if DB counts become available.
- **Follow-up:** [GitHub issue #8](https://github.com/tommylin15/life_assistant/issues/8) tracks least-privilege evidence retrieval and readback, accurate dedup telemetry and verified-only UI acceptance. Do not self-grant broad Logging/IAM roles or present fallback estimates as production row counts. Nine other fetch sources remain disabled.

## 2026-10-09 EventGo / BeClass source-scope amendment (later decision)

- Earlier entries above refer to nine disabled non-MoC sources at the time of those runs; **the current M0 registry now contains nine total sources: one approved MoC source and eight disabled sources**. Do not retrospectively rewrite old execution evidence.
- **Corrected decision (2026-10-09):** BeClass is excluded **only as a direct automated discovery/crawl source**; do not fetch its homepage, listing, search or detail pages. **Preserve** activities discovered via EventGo, other aggregators, or organizer pages even when their registration/original URL points to BeClass; store that URL as an unverified outbound reference, never crawl BeClass to verify it. The BeClass source ID stays absent from `data/free_events_m0_sources.json`, but no EventGo parser/normalizer should filter indirect referrals.
- Added `scripts/eventgo_connector.py` (Crawl4AI 0.9.4 optional runtime, offline parser, dedup/JSONL) and `doc/eventgo_crawl4ai_connector.md`. EventGo terms restrict bulk automated access, so its registry fetch flag stays false. This is standalone development; no production source crawl, persistence, UI or 14-day evidence is claimed.

## 2026-10-09 — Current official source selection (Drive TXT)

- Source-of-truth allowlist: **six IDs** `moc_events_all`, `moc_event_detail`, `data_gov_catalog`, `tdx_tourism_events`, `eventgo`, `yii_calendar` across five source groups. Only `moc_events_all` can fetch; others remain disabled until reviewed. `citytalk`, `accupass`, `kktix` removed from registry, not merely left as candidates. Prior nine-source figures above are historical and superseded.
- Preserve third-party BeClass registration links as unverified URL references, but do not fetch BeClass. Source allowlist removal does not delete PostgreSQL historical events/observations or imply production DB source rows are already changed; application source gate and production state require separate verification.
- Source TXT lists sensitive TDX API/MQTT credentials; no secret values are copied into GitHub. Operational secret storage / rotation remains a separate task requiring explicit approval for production credential rotation.
- EventGo 3-day latest-publication filter is a **future candidate rule only when a verifiable published/posted timestamp exists**; never infer published date from event date or an example fixture. EventGo and yii.tw live crawl/production DB ingestion remain **NOT VERIFIED**.

## 2026-10-09 — Open-data catalog deferred / deterministic structured-source processing

- The registry retains `data_gov_catalog` solely as a **deferred inventory entry**, with `service_access_review=deferred` and `enabled_for_fetch=false`. No directory discovery, arbitrary per-dataset polling, AI extraction or scheduled enablement is authorized. The already-approved Ministry of Culture dataset is a separate fixed-source connection and remains unaffected.
- Ministry of Culture and future reviewed TDX feed should share normalization, staged candidate dedup/queue and official evidence checks, but **structured inputs should not invoke AI by default**. The universal durable queue, multi-source executor and TDX live adapter are still **NOT IMPLEMENTED / NOT VERIFIED**; do not misdescribe the deployed MoC batch as the new queue.
- Reconsider general government open data only after measured event-level freshness, official registration accuracy, duplication, null-field rates and explicit renewed source approval. EventGo/yii.tw three-times-weekly collection remains a requirement, not a running authorized production schedule.

## 2026-10-10 — P0–P2 combined candidate implementation (not production acceptance)

**Single delivery unit:** P0 factual production readback + P1 durable PostgreSQL queue + P2 Ministry of Culture adapter cutover. Implementation is committed together and must be accepted as a package; no individual feature is marked DONE merely because CI is green.

- **P0:** existing owner-only, authenticated, read-only `GET /api/v1/free-events/status` remains the protected factual readback route. The same `scripts.read_free_events_status` now requires Alembic `20261009_0014` and reports actual source event/session/opportunity/verified-only UI counts plus the `free_event_candidate_queue` state counts. This is not a source-observation substitute and requires a genuine owner session and runtime PostgreSQL query; prior GitHub WIF still cannot read Cloud Logging. A successful Cloud Run Job execution does not prove a row count.
- **P1:** additive Alembic `20261009_0014` creates `free_event_candidate_queue`; only normalized, size-bounded Pydantic candidate JSON is stored, **never raw HTML or a source credential**. Unique source+external-event key, full normalized fingerprint, idempotent unchanged no-op, changed-content requeue, PostgreSQL `FOR UPDATE SKIP LOCKED` claim, token-and-fingerprint fencing, five attempts, bounded backoff, terminal failure and revoke-aware source gate. The queue is reusable for other *individually approved* sources, but it does **not** approve TDX, data.gov.tw catalog, EventGo or yii.tw.
- **P2:** the existing 06:00/18:00 MoC Cloud Run batch preserves the official fixed-endpoint JSON fetch, rotating 400-record upper bound and source durable lease. Instead of directly writing every normalized record into the catalog, it **commits the candidate to the queue**, processes a bounded number of claims through the existing `ingest_approved_candidate` transaction, then ACKs. Replays after a crash are idempotent, unsuccessful claims persist for retry and any processing failures fail the job/source lease rather than masquerade as a completed batch. AI invocation remains **0**. No automatic human verification, no personal reminder/calendar mutation, and no third-party crawl.
- **Release:** V3 audited GHCR release migration target and readback expectation advance from `0013` to `0014`; require the additive table before promoting new MoC runtime. CI uses ephemeral PostgreSQL 16 sidecar, runs both existing and new queue concurrency/crash/fencing/approval tests, and validates the schema-reconciliation path. Old production jobs must not be run against an incompatible revision; preserve the old live revision until promotion is validated.
- **Acceptance at end:** implementation / backend unit tests / real PostgreSQL CI / candidate deployment / additive production migration / MoC Job execution / owner-authenticated aggregate readback and 14-day quality evaluation are separate PASS/FAIL/NOT VERIFIED checks. **P0 runtime rows, real per-run prevented duplicate upserts and eligible UI count remain NOT VERIFIED until readback evidence is captured.** The 14-day source-quality gate is tracked separately; it cannot be backfilled from synthetic data.


## 2026-10-10 — Consolidated CI evidence / guarded live release attempt

- Candidate code commit `7c9a9fc4e0f45c47f482a5facc9deacb828e6627` introduced additive 0014 and MoC queue processing. Initial CI [37957726162](https://github.com/tommylin15/life_assistant/actions/runs/37957726162) had a backend **FAIL** because a legacy Drive migration assertion still pinned pre-revision 0012 and target 0013; PostgreSQL queue integration **PASS**. Follow-up commit `22753378154c0905314c16c4bc7fad4143e4b694` updated that test; [CI 37957886391](https://github.com/tommylin15/life_assistant/actions/runs/37957886391) **all four jobs PASS**: backend, Flutter, deployment-scripts, actual PostgreSQL 16 migration/queue tests.
- One-shot `.github/workflows/free-events-activation-once.yml` is restricted to its **own push path** and gates exact-main SHA + all four CI jobs before dispatching existing V3 `v3-release-ghcr.yml` with the existing full candidate/preview/migration/live/rollback requirements. If and only if V3 succeeds, it pins the already-existing `life-assistant-free-events` Cloud Run Job to the exact promoted GHCR image, preserving existing database secret/env, service account and command; it then dispatches the existing MoC observation workflow. It does **not** replace the Job from an unrelated template or deploy Firebase production Hosting.
- **This planned workflow is not itself deployment evidence.** Before final acceptance: verify actual new CI, exact-SHA V3 run, production Alembic 0014, Job image identity and execution, and a genuine owner-session read-only DB aggregate. The first MoC Job after release may legitimately return NOT_DUE_OR_LEASED. In that case, a successful workflow is **not** proof of a new candidate persisted through the queue. P0 counts and queue depth remain NOT VERIFIED without actual authenticated readback.
