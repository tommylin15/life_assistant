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
