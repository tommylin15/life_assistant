# 台灣活動｜獨立 Drive 交接資料 → Life 每日匯入契約

**2026-10-10：匯入程式與 additive 0016 migration 已在工作樹實作；本機 PostgreSQL 併發去重／更版測試 PASS，真實 Sheet／GCP Job／ACK E2E 尚 NOT VERIFIED。** 探索規則本身以 Drive「台灣活動探索」正式 01～05 文件為準；這份文件僅規定 Life 如何消費交接資料。不要因文件寫好就宣稱 Life 已上線。

## 唯一交接來源與責任邊界

- 固定的原生 Google Sheet：[台灣活動｜交接資料](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit)；**Spreadsheet ID：`1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4`**；資料分頁 `交接資料`，第二分頁 `交接規格`。生命週期中的 Life Job 只讀**前者**；不依檔名搜尋、不直接掃描舊 45 欄「精選活動」。
- 探索端唯一原表仍是 [台灣活動｜精選池](https://docs.google.com/spreadsheets/d/10aZRbXTLXdn34Zgj3gCgeXAYzWhNeVjMKOtlnO9vGAY/edit)；交接表只是**滾動 outbox**，不是永久活動資料庫，也不代替證據、每日探索 Log。
- **ChatGPT 探索任務終點**：原來源核證／精選原表 upsert → 把**符合可交接條件**的活動寫成 `READY` → 從交接表讀回驗證。探索端不連 Life API、PostgreSQL、不接觸 DB secret。
- **Life 任務起點**：GCP 每日定時 Python Job 讀取交接表，Pydantic 驗證、穩定去重、PostgreSQL upsert、DB commit 後寫回結果。Life 不爬文化部、觀光署、官網或票務，不做第二輪 AI 判讀，不在匯入時建立使用者個人待辦／行事曆／提醒。
- 此設計取代「ChatGPT direct API 直接寫庫」與早期「GCP Job 唯讀精選池 45 欄」的**預設匯入入口**；既有 `/api/v1/free-events/curated:batch` 與 URL-based identity 尚存在，僅作相容實作，不可刪除或聲稱已自動改用本表。原 Queue／claim／lease／來源爬蟲仍取消；`ACKED` 是新交接的入庫收據，並非舊 Queue 系統。

## 固定資料表欄位 v1（精簡 30 欄）

欄名以實際 Google Sheet 首列與「交接規格」分頁為準；任何名稱／必要欄位／狀態變更需版本化調整讀取者，不可默默相容失敗。

| 領域 | 實際欄位 |
| --- | --- |
| 穩定鍵與父子 | `event_key`, `content_hash`, `parent_event_key`, `record_type` |
| 活動資訊 | `title`, `city`, `district`, `category`, `organizer`, `start_at_tpe`, `end_at_tpe`, `venue` |
| 可追溯連結與價值 | `official_url`, `registration_url`, `source_url`, `importance_star`, `opportunity_type` |
| 時間、費用與證據 | `registration_open_at_tpe`, `registration_deadline_at_tpe`, `nonrefundable_cost_ntd`, `refundable_deposit_ntd`, `verified_benefit_ntd`, `eligibility_limit`, `evidence_summary`, `verified_at_tpe` |
| 雙方交接回執 | `handoff_status`, `handoff_updated_at_tpe`, `life_ack_at_tpe`, `life_import_result`, `life_error` |

- `event_key` 是穩定活動／優惠鍵、`parent_event_key` 是主題父鍵，`record_type` 區分 main／offer／session；`content_hash` 用規格化**業務欄位**計 SHA256，須排除交接狀態／回執／掃描批次，不因重跑而改變。這些鍵都不能由列號、run_id 或目前時間臨時產生。
- **2026-10-10 使用者最新決策：交接表規格優先，Life DB/UI 配合，不回頭修改探索表或文件。** `content_hash` 是探索端提供的業務版本 SHA256；Life 驗證64位十六進位格式與全部業務欄位，不強迫探索端採用 Life 自訂的 JSON 序列化。PostgreSQL 同鍵同 hash 時必須再比對已保存的完整業務內容；同 hash 卻改內容拒收 ERROR，不能假稱 UNCHANGED。
- 1／3／5 星是價值、不是可報名或有空位的證據；報名開放、截止、活動期間不能互相混用。未知費用／押金／福利不填零；未知時間留空，只有日期的來源不得補造午夜。所有可核定時點使用 ISO 8601 帶 +08:00。
- 只有主辦證據、費用、活動身分等達到探索規格的交接 Gate 才能成為 `READY`；待核五星、官方時點衝突、關鍵資格不明或只有第三方索引者留原精選池等待，不因原表內 `selected` 就批量全搬。Life 只做結構和安全驗證，不代替探索核證。

## 每日定期匯入與回執

1. Life 以固定 ID 讀 `交接資料`，先比對表頭／欄位契約，處理 `READY`、可重試 `ERROR` 及全部 `ACKED`。ACKED 每輪仍核對 DB；只有已驗證同版本、同業務內容的成功回執才不重寫。表內 `event_key` 不可重複，異常失敗關閉並記錄，不能讀取錯表仍宣稱成功。
2. **去重持久化必須在 Life PostgreSQL**：以 `source=chatgpt_drive_handoff`＋`event_key` 建立永久唯一對應，並保存最後成功 `content_hash`。同鍵同 hash → `UNCHANGED`；同鍵新 hash → `UPDATED`；新鍵 → `CREATED`。**現有 backend 的 `identity_key` 是 canonical URL＋occurrence_key 的 SHA256，不等於 Drive 的 `event_key`；原始網址一換可能多建一筆**。正式介接前先檢查 schema，採最小 additive mapping/migration 和兼容性測試，不得假定去重已完成。
3. DB transaction **commit 成功後**，Life 再重新讀取 Sheet，以穩定鍵重新找列並核對全部業務欄位、hash 及 handoff 更新時點，再寫回並讀回。依實際 Sheet 規格，`life_import_result` 是裸字串 CREATED／UPDATED／UNCHANGED，失敗留空並寫 life_error，不增加 JSON 回執要求。Life 每輪連 ACKED 也核對 PostgreSQL，以資料庫版本與內容作可靠收據；已正確 ACK 的版本不重設成功時間。Sheets 不提供原子條件寫入，不能宣稱完全排除跨寫入方移列競態；寫後不符報 PARTIAL，下輪再核對／修復，不能憑 Sheet status 跳過新版。
4. 匯入失敗保留列並寫 `ERROR`／脫敏 `life_error`；若 DB 已 commit 但回 Sheet 失敗，下輪相同鍵與 hash 由資料庫冪等處理（UNCHANGED）並補 ACK。允許部分成功但整體報 PARTIAL／FAIL；每輪留可稽核 run id、imported/unchanged/invalid 計數與真實 DB、Drive readback。
5. **探索端滾動 30 天清理**：沿用交接規格，只清 ACKED 且可信 life_ack_at_tpe 超過30天、精選池仍保存活動的列；清前再確認目前 key/hash。READY、ERROR、無可靠回執或新版不得清除。Life 不修改探索端清理流程；永久去重依靠 PostgreSQL，不依靠交接表歷史。

## 授權與實作落差

- 只授權指定交接 Sheet 給 Life Job 專用 service account；不能公開分享，不建立長效 SA JSON key。既有 Job 設計的 **Viewer＋`spreadsheets.readonly` 只能讀、不能回寫 ACK/ERROR**；新實作需最小必要的單表 Editor／Sheets write scope、校驗 Google 身分並防止其他文件被讀寫。憑證、Token 不進 Sheet／Log。
- 固定設定的 `LIFE_CURATED_SHEET_ID` 應指向**新 ID**；不能沿用舊精選池。`.github/workflows/curated-handoff-daily.yml` 每日台北09:30或手動，以既有 WIF 觸發既有 GCP Python Job `life-assistant-free-events`，映像取已正式切流且 Ready 的 GHCR immutable digest，與發布共用併發鎖。不新增付費 Scheduler／Job、不恢復來源 crawler；只有 staging dry-run、真實 apply、DB／Flutter／回執驗證 PASS 並完成正式切流後，才設定 repository variable `LIFE_CURATED_HANDOFF_ENABLED=true` 啟用。這是排程啟用條件，不改活動的 admin 開放設定。
- GitHub 現有 importer 若仍讀舊 `精選活動`／`pool狀態=selected`、僅 Sheets readonly 或使用 URL identity，應標 **IMPLEMENTATION GAP**。需求須經現況程式盤點、tests、CI、staging、PG、Flutter、Drive ACK 實際驗收；文件更新不等於 Job 已改造、授權、排程或部署。

**2026-10-10 最新實況**：真實 Sheet已有3筆 READY，欄位／來源 payload 本機驗證 PASS；使用者明確授權的單表 Editor 分享及權限讀回 PASS。Life Job實際入庫／ACK、DB/UI E2E與排程尚待驗收；不把本機驗證當成上線。
