# Taiwan Free Events — M1 Implementation Checkpoint

## M1 先行開發 checkpoint — 2026-10-09

**狀態：PARTIAL（實作／單元測試 PASS；新版實際 migration / database integration / Cloud Run runtime / 正式來源擷取 NOT VERIFIED）。**

- **資料結構**：additive Alembic `20261009_0011`，新增 `free_event_sources`、`free_event_organizers`、`free_events`、`free_event_sessions`、`free_event_registration_opportunities`、`free_event_evidence` 六表。保持公用事件共用一份，不納入 user/sub 個人物件；場次/票種分離、報名開啟時間 nullable、全天結束日期 exclusive、證據只保留必要欄位；不碰既有業務表。向上遷移路徑與 fail-closed release revision guard 已更新到 0011；未啟動 production DB migration。
- **來源/費用的後端保護**：`fetch_enabled` 只有 `reviewed_with_evidence` + license evidence 才允許在 SQL 層為 true；未驗證活動不可標正式 verified，free claim 不可附正費用且需正式報名網址。現行來源清冊所有擷取開關仍 false。
- **確定性正規化**：`EventCandidate`／`CandidateSession`／`CandidateOpportunity` Pydantic 校驗，HTTPS 公開 URL、明確時區、distinct session/registration key、不得從未知數推費用/報名時刻；跨來源只有同一已核實官方 URL 才可合併，任何內容衝突需人工檢視。無變更或規則已足夠的資料 AI 呼叫必須 0。
- **離線預檢 CLI**：`python scripts/free_events_m1_dry_run.py reviewed_candidates.jsonl`，最多 5,000 筆 / 10MiB，列出重複、衝突、未授權來源及未知欄位，永不連網、不寫 SQL、不發布提醒/待辦/筆記。
- **文化部資料 Adapter**：`python scripts/free_events_moc_offline.py downloaded_official_moc.json`，只讀預先合法取得的官方 JSON，將 UID / showinfo 場次轉結構化記錄；不把 `onSales=false` 或 `price=免費` 直接當成可確認的免費或報名可用，不推測日期精度、報名開放時間；即使來自政府資料集仍須經來源 Gate 與人工核實。
- **測試/CI**：M1 模型、Alembic、資料契約、manifest、CLI、MoC Adapter、PostgreSQL `ON CONFLICT` SQL/permission gate 已新增測試。來源入庫修正 SHA `c86ef14db34affe57db1fcc1157e34cac619d0c2`，[CI #37895465333](https://github.com/tommylin15/life_assistant/actions/runs/37895465333) backend **463 tests PASS**、deployment-scripts PASS，Flutter 完整結果待 readback。前一個不含 PG ingest 的 `206fe35ec6b0d0afefb7649de2a07d0d428af001` [CI #37894866290](https://github.com/tommylin15/life_assistant/actions/runs/37894866290) 全 PASS。歷史中間 commit `50e3e67` CI backend FAIL 來自測試 mock Result 和 bind params 判定，已修正且最新 backend PASS；**不將歷史失敗隱匿為 PASS**。
- **PostgreSQL 交易式入庫 service（程式/SQL contract PASS，真實 DB NOT VERIFIED）**：`backend/app/services/free_events_ingest.py` 已實作來源表 `SELECT FOR UPDATE` 權限鎖、批次數量上限（100 場次/500 報名機會）、活動/主辦/場次/報名機會的 `ON CONFLICT` 去重與 `RETURNING`、證據 fingerprint 去重。活動正式驗證只由人工審核授權；資料更動會標 stale，未更動才保留原驗證狀態；報名機會欄位有異動即撤銷已核實旗標。**此 service 尚未經正式入口呼叫／production DB migration 未執行**，mock SQL 測試不可當真實 PostgreSQL 幂等或 isolation PASS。
- **尚缺**：已授權/節流的官方擷取 Adapter、14 天真實累積/匯入持久化、PostgreSQL transactional upsert 的真實 DB/concurrency/job-lease 驗收、AI 批次持久化、Cloud Run 遷移後的 live table readback、M2 Flutter UI、M3 使用者 opt-in、M4 Scheduler/部署。模型 migration 是在 main 的**候選程式碼**，不是 production 已套用 schema 的證據。AI 現在是 0 呼叫因為未啟動，不代表真實供應商 E2E 通過。
- **14 天觀測與 M1 並行**：保留既有 ChatGPT 06:00/18:00 過渡候選掃描（不能冒充 PostgreSQL observation store）。正式計時須從可靠儲存且合法取得的來源觀測開始，缺日不能回填虛構紀錄。M0 仍 PARTIAL，不阻擋 M1 研發，但保留 M0–M4 正式 MVP gate。

## 下一實作次序

1. 在來源條款審查後先接文化部/TDX 官方 licensed endpoint，添加 timeout/rate/size guard；保留聚合站停用。
2. 用開發／測試 PostgreSQL 驗證 0011 的 migration、FK、unique、default、check constraints 及 idempotent upsert（不得直接將測試筆數混入正式資料）。
3. 為已授權的 Batch 加入 bounded concurrency、durable lease/claim、相同 fingerprint 無 AI 重算、錯誤／退避、暫時源故障不得當活動取消。
4. 由真正 verified event source 與官方 registration 證據開放 M2 Read API/Flutter；勿在 NULL 開放時間時建立精確提醒。
5. M0 14 天正式觀測照常進行；驗收證據不足維持 NOT VERIFIED，不延後其它低風險程式開發。
