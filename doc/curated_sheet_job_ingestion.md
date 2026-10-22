
## 2026-10-22｜交換池與「全部活動」整併驗收契約（待實作驗證）

- 唯一使用者活動列表為「全部活動」；移除「限時機會」獨立切換不代表刪除、隱藏或排除原 `opportunities` 類別。後端 `entry=explore` 必須包含所有合格的 `event_key`，無論 `record_type=main/offer/session`、`opportunity_type`、核證狀態 `verified/pending_review/unknown`，並以 `parent_event_key` 分組去重。
- 交換池 `READY` 只表示待匯入；`ACKED` 只表示 importer 已回執，**不能推論**已在 Life「全部活動」可見。須對同一 `event_key/content_hash` 逐段讀回：交接 Sheet → importer 結果 → PostgreSQL → `entry=explore` API（含搜尋、篩選、游標分頁）→ Flutter 卡片。
- 部分待核且具有合法具名來源、可信活動日期／開報節點的活動可以進交換池；不要求第二官方網站、即時餘額或全部費用欄位。未知資料留空、前台標示待核，不得偽造可報名、仍有名額或報名成功。
- 正式列表仍排除已過期／取消活動；已收藏歷史活動可回查並標註。功能旗標、舊 `opportunities` 入口、個人收藏與待辦／日曆標記需維持相容；不得因 UI 整併變成資料遺失。
- 回歸測試至少包含：新 `offer` 入庫可在「全部活動」找到、`pending_review` 可顯示、主子項去重、同一鍵版本更新、跨分頁不漏項、搜尋與地區篩選、舊收藏、過期排除、舊網址導向。
- 這是工程驗收契約，**不是**程式、CI、部署或真實活動端到端驗收已完成的證據。

# 台灣活動｜獨立 Drive 交接資料 → Life 每日匯入契約

> **2026-10-18 15:54＋PostgreSQL 最終增量讀回：技術資料鏈 PASS。** `交接資料` 已達 65 個互異鍵、65 ACKED／0 READY／0 ERROR；新增三筆 BeClass 仍 `verification_status=pending_review`。既有 importer 完成真實 GCP 執行，另以 [#39110194986](https://github.com/tommylin15/life_assistant/actions/runs/39110194986) 進行不覆寫 importer 的 `SET TRANSACTION READ ONLY` 核對全部已 ACK 活動之 PostgreSQL `event_key/content_hash/verification_status`，PASS。此為技術資料交接，不取代尚待驗的 Flutter 真實前台、GAS 次日自然觸發及完整來源品質。下方 62 ACKED 及來源 ERROR 舊數字屬歷史快照，不得作最新狀態。


> **2026-10-18 最後讀回（替代下方歷史匯入狀態）：** [真實 hash 修復重跑 #39101120210](https://github.com/tommylin15/life_assistant/actions/runs/39101120210) CI/live/job preflight PASS，Execution 完成且 0 failed；固定交接 Sheet 31 欄、62 不同鍵、62 ACKED、0 ERROR/READY，BeClass pending_review 同鍵成功回執。這是 **Job + Sheet PASS**，不是 PostgreSQL 同鍵新 hash/UI 實機或本日完整探索 A7/B10 PASS；尚需個別 readback。舊 exact-SHA [#39101120348](https://github.com/tommylin15/life_assistant/actions/runs/39101120348) 在匯入前被 gate 擋下，不構成新 Job 故障。正式 07:30 GAS trigger 證據仍待確認。

> **2026-10-18 新增：可報名、未充分核證的活動**。保留既有 A:AD 30 欄及 Z/AB:AD 回執位置，僅於 AE 追加可選 `verification_status`：`pending_review`（報名入口存在但活動／資格等未充分核實）、`verified`（已由具名主辦／授權報名頁核實）、`unknown`（舊資料，不能無證據自動升級）。交換池最小追溯門檻不變，不能有假主辦、虛假日期、過期或未經許可網址。BeClass 由具名主辦直接建立且可追溯的合法授權報名表本身足以作為主辦來源，不強制一定還有第二個政府官網。星等與報名分類保持獨立；在 Life 前台提供驗證狀態篩選和醒目標籤，不保證有現貨、已報名或已通過審查。後續有可靠主辦新證據時，**同一 event_key、同一 parent_event_key**，更新 evidence/url、`verification_status=verified` 與完整業務 `content_hash`，現有 PostgreSQL 列更新為 UPDATED，保留使用者收藏和操作。新版本 importer 相容舊 30 欄與新 31 欄（缺少 AE 默認 unknown）；不可將舊有核證時間是否為空單獨當作已核實或未核實的證據。若新版尚未完成 CI、部署、runtime，標 PARTIAL，不宣稱 UI 已正式顯示。


> **2026-10-16 最新驗收（優先於下方歷史紀錄）：01 技術交接資料鏈 PASS／DONE。** 正式 Job `life-assistant-free-events` 在 07:34:20 台灣時間的 Execution `ds4bq` 成功，Sheet 59 筆＝58 ACKED／1 ERROR，其中 5 筆 07:34:15 新 `CREATED`；[唯讀 Cloud Run／PostgreSQL 查核 #38825509671](https://github.com/tommylin15/life_assistant/actions/runs/38825509671) 對五筆鍵、內容版本、更新時點與建立時間逐筆讀回 PASS。**無第二次 importer 執行**。未直接讀取 Apps Script 觸發 ID／ledger（NOT VERIFIED），故只主張「07:30 時段每日匯入功能有真實成功證據」，不虛稱已核對 GAS 觸發器來源。來源 1 筆 `invalid_handoff_record` 保持 ERROR、品質 PARTIAL，不因此使技術 Job FAIL。


> **2026-10-15 historical evidence update (superseded above):** 正式 [V3 Release #38572432707](https://github.com/tommylin15/life_assistant/actions/runs/38572432707) 將 importer Job pin 至 production promoted digest 並 readback PASS；該 Release **execution=NOT_RUN**，不是最新 GAS 定期排程/PG/Sheet ACK 成功的證據。舊 2026-10-12 FAIL 與 2026-10-14 52 ACKED / 2 ERROR 為歷史觀測。最新驗收狀態以 [CURRENT_STATE](CURRENT_STATE.md) 為準；技術 status 與來源資料 data_status 仍分開判定。

**2026-10-12 契約（07:30 配置與 verified_at_tpe 規則仍有效；runtime 狀態以 10/16 最新驗收為準）：`verified_at_tpe` 一律選填，未知必須留空；不得以發現時間、批次時間、匯入時間冒充核證。每日 GAS 接收排程最新設定為 07:30（Asia/Taipei，使用者已確認；Apps Script 時間觸發器與定時執行證據仍 NOT VERIFIED）。** `handoff_updated_at_tpe` 仍是必要版本時點。2026-10-12 GAS read-only preflight 與 Job 啟動請求 PASS；當次 Cloud Run Execution 容器 Exit 1，實際入庫與回執 E2E 尚未通過。GitHub 匯入原始碼採選填契約並須由新 SHA 的 CI／部署及真實 DB/Sheet 讀回各自驗證。 探索規則本身以 Drive「台灣活動探索」正式 01～05 文件為準；這份文件僅規定 Life 如何消費交接資料。不要因文件寫好就宣稱 Life 已上線。

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
- 1／3／5 星是價值、不是可報名或有空位的證據；報名開放、截止、活動期間不能互相混用。未知費用／押金／福利不填零；未知時間留空，只有日期的來源不得補造午夜。`verified_at_tpe` **可空**：空白映射為 `None`／JSON `null`，不得補上 `handoff_updated_at_tpe` 或執行時間；若提供核證時點，必須是具 +08:00 的 ISO 8601 datetime。`handoff_updated_at_tpe` 是獨立且必填的交接版本時點。
- **2026-10-10 更新：交接是「提前告知＋清楚標註待核」，不是所有條件完全核證才顯示。** 精選池已選入且具穩定鍵、具名活動、可回查官方／主辦授權／可靠來源，以及有據活動日或開報節點者，允許輸出 `READY`；不因 5★ 潛力待核、主辦索引頁暫不能直接開啟、即時名額未查、必要費用或退款細節未知而一律阻擋。1★／3★一般活動同樣可輸出，星等是價值而非證據等級。待核、時點衝突、資格限制、費用未知寫入 `evidence_summary`，Life UI 要保留並連回來源。**僅索引可見不能標示已開頁核證，也不能保證可報名或尚有名額。**
- **最小排除條件：** 活動無法識別、無穩定 event_key、沒有任何可回查來源、已證實取消或確定過期者不交接；日期／開報資訊有矛盾，僅輸出有據且無衝突的欄位，其他留空並文字註記。未知費用／押金／福利、開報／截止、精確時分及核證時間均不得假填 0 或編造日期。Life importer 接收 `verified_at_tpe` 空值是**正式契約與必要回歸測試**；若 runtime 仍因其空白拒收，應更新 Life 實際部署映像，不得讓探索端假稱已核證。
- **獨立嚴格門檻保持：** event_key/content_hash 永久去重、資料版本一致性、DB commit 後 ACKED 仍要嚴格；內容核證門檻放寬不等於放寬資料完整性。

## 每日定期匯入與回執

1. Life 以固定 ID 讀 `交接資料`，先比對表頭／欄位契約，處理 `READY`、可重試 `ERROR` 及全部 `ACKED`。ACKED 每輪仍核對 DB；只有已驗證同版本、同業務內容的成功回執才不重寫。表內 `event_key` 不可重複，異常失敗關閉並記錄，不能讀取錯表仍宣稱成功。
2. **去重持久化必須在 Life PostgreSQL**：以 `source=chatgpt_drive_handoff`＋`event_key` 建立永久唯一對應，並保存最後成功 `content_hash`。同鍵同 hash → `UNCHANGED`；同鍵新 hash → `UPDATED`；新鍵 → `CREATED`。**現有 backend 的 `identity_key` 是 canonical URL＋occurrence_key 的 SHA256，不等於 Drive 的 `event_key`；原始網址一換可能多建一筆**。正式介接前先檢查 schema，採最小 additive mapping/migration 和兼容性測試，不得假定去重已完成。
3. DB transaction **commit 成功後**，Life 才形成回執隊列；批次重新讀取 Sheet，依穩定鍵定位、核對全部業務欄位、hash 及 handoff 更新時點，再以有界 `values:batchUpdate` 批次回寫並一次讀回核對（不能再逐列重讀全表造成 API 429）。遇到 429/暫時 5xx 有界退避重試，最終失敗維持未驗收狀態；依實際 Sheet 規格，`life_import_result` 是裸字串 CREATED／UPDATED／UNCHANGED，失敗留空並寫 life_error，不增加 JSON 回執要求。Life 每輪連 ACKED 也核對 PostgreSQL，以資料庫版本與內容作可靠收據；已正確 ACK 的版本不重設成功時間。Sheets 不提供原子條件寫入，不能宣稱完全排除跨寫入方移列競態；寫後不符報 PARTIAL，下輪再核對／修復，不能憑 Sheet status 跳過新版。
4. 匯入失敗保留列並寫 `ERROR`／脫敏 `life_error`；若 DB 已 commit 但回 Sheet 失敗，下輪相同鍵與 hash 由資料庫冪等處理（UNCHANGED）並補 ACK。單筆來源欄位驗證失敗時，在該列記 ERROR／invalid_handoff_record，其他列繼續處理，並計入 data_status=PARTIAL；只要 Job 的 Sheet 讀寫、DB 操作及回執核對均正常，Job status=PASS／容器成功結束。DB 寫入失敗、無法核對或回寫回執、Sheet API 失敗、結構性表頭／重複鍵異常等技術與完整性問題仍讓 Job FAIL。每輪保留 run id、created/updated/unchanged/invalid/import_failed/ack_failed、Job status 與 data_status；不可拿 Job PASS 假稱全部活動合格。
5. **探索端滾動 30 天清理**：沿用交接規格，只清 ACKED 且可信 life_ack_at_tpe 超過30天、精選池仍保存活動的列；清前再確認目前 key/hash。READY、ERROR、無可靠回執或新版不得清除。Life 不修改探索端清理流程；永久去重依靠 PostgreSQL，不依靠交接表歷史。

## 2026-10-14｜雙層完成判定（使用者最新核准）

- **Cloud Run Job 成功**：完成固定 Sheet 讀取、逐列資料驗證、有效列 PostgreSQL commit、所有必要 ACK/ERROR 回執及讀回版本核對，程式正常結束即可記 `status=PASS`、Exit 0；個別活動 `invalid_handoff_record` 不得單獨使 Cloud Run Job Exit 1。
- **探索端資料品質**：欄位枚舉不合、offer 自指父鍵、缺值或來源證據問題等，保留該列 `ERROR` 和不含敏感內容的錯誤資訊，由每日 AI 探索批次修補正式精選池及同版本交接欄位、重算 business `content_hash`、更新 `handoff_updated_at_tpe` 後再設 READY。若 `invalid>0` 則 `data_status=PARTIAL`；此狀態是探索工作未完，不代表 Cloud Run 技術失敗。
- **仍須 Fail Closed**：固定來源表頭／event_key 唯一性異常、Sheets API 或回執讀寫失敗、PostgreSQL 寫入失敗、版本一致性回執不能證明等屬 `status=FAIL` 並使 Job Exit 非零，不得藉「資料品質放寬」掩蓋真正技術錯誤。
- 2026-10-14 執行案例：52 ACKED、2 ERROR 只證明部分逐列資料成功及兩列來源錯誤；當時舊版 Job 因 `handoff_import_partial` Exit 1，**歷史 Execution FAIL 不得追改 PASS**。新版本需經 CI、正式 digest pin／Job、真實執行及 Sheet/PG 讀回，才能宣稱新的技術成功。

## 授權與實作落差

- 只授權指定交接 Sheet 給 Life Job 專用 service account；不能公開分享，不建立長效 SA JSON key。既有 Job 設計的 **Viewer＋`spreadsheets.readonly` 只能讀、不能回寫 ACK/ERROR**；新實作需最小必要的單表 Editor／Sheets write scope、校驗 Google 身分並防止其他文件被讀寫。憑證、Token 不進 Sheet／Log。
- **2026-10-11 排程責任移轉**：原 `.github/workflows/curated-handoff-daily.yml` 已移除舊每日 09:30 `schedule`（歷史設定；目前正式目標改為 GAS 07:30），僅保留受 `LIFE_CURATED_HANDOFF_ENABLED=true` 控制的手動 `workflow_dispatch` 備援；此 workflow 僅確認正式 API 的唯一 100% Ready Revision、不可變 GHCR digest、既有 `life-assistant-free-events` Job 映像及固定 Sheet／command／apply 設定一致後，才允許人工觸發，**不再更新 Job 映像、環境變數或 command**。正式 V3 `.github/workflows/v3-release-ghcr.yml` 在 `promote=true`、正式健康／資料庫／OAuth、回滾演練及 Revision 保留步驟全部 PASS 後，由同一 deployer WIF 對現有 Job 做 image/command/args/固定 Sheet 和 apply 設定更新並 readback；不建立 Job、不執行匯入、不在 staging-only 發布更新。**GAS 接收排程以每日 07:30（Asia/Taipei）為最新使用者設定**；GAS 專案時間觸發器是否建立並實際按此時間執行，尚未取得 Apps Script runtime 證據（NOT VERIFIED）。另須驗證最小 IAM、真實 PostgreSQL readback、Sheet ACK、開關及重跑冪等，才可宣稱整條 E2E PASS；**移除 GitHub cron 不代表 GAS 定時接收已被驗證，也不可同時啟用雙入口**。
- GitHub 現有 importer 若仍讀舊 `精選活動`／`pool狀態=selected`、僅 Sheets readonly 或使用 URL identity，應標 **IMPLEMENTATION GAP**。需求須經現況程式盤點、tests、CI、staging、PG、Flutter、Drive ACK 實際驗收；文件更新不等於 Job 已改造、授權、排程或部署。

**2026-10-12 接續**：使用者的 GAS 讀 Job 與正式 live GHCR digest preflight 回報 `READY`，`jobs.run` 回報 `ACCEPTED_NOT_COMPLETED`；Execution `life-assistant-free-events-zc4xr` 最終 `CONDITION_FAILED`（Exit 1）。交接表仍有待處理 READY/ERROR；使用者提供 stderr 可確認：Pydantic `HandoffItem` 有單一欄位驗證失敗（片段未包含欄位名稱，尚不能認定是哪一欄），舊版逐筆回執時發生 `sheets_http_429` 並使 Execution Exit 1。現行 GitHub `main` 已實作批次回執、429/暫時 5xx 有界退避重試與驗證錯誤欄名（不輸出值）診斷，回歸測試 Backend／free-events-postgres jobs PASS；尚未證明正式 Job 已部署或 E2E PASS。詳見 [CURRENT_STATE](CURRENT_STATE.md)。實際 Job 終態、PostgreSQL 及 Sheet ACK 仍須在修正版本部署後驗收。

## 2026-10-18｜整批活動探索 P0–P2 與匯入 Job 合併收斂（待整體驗收）

- **責任合併**：先完成 life_assistantGPT Drive 01～05 與正式來源／精選池、Life 前台核證狀態和來源連結、`life-assistant-free-events` 修復，再一次進入整合驗證／部署。探索來源備援改為網頁讀取 TinyFish → Tavily → Firecrawl；不是 DNS 專用，也不使用 Jina Reader，絕不繞過 403/429／登入／站方限制。
- **執行異常證據（唯讀）**：2026-10-18 GitHub「Life Importer Evidence (read only)」列出最近 Execution `life-assistant-free-events-gpp8c` `status=False / failed_tasks=1 / reason=NonZeroExitCode`；尚未取得該次容器應用程式 traceback，不能斷言根因。當日曾有 Wild Wild 舊 ACKED 與新 READY **相同 event_key 雙列**，違反 importer `parse_rows` fail-closed 唯一鍵契約；此為高可信風險候選，不等同已證明本次 Exit 的原因。後續原鍵第60列保留新版 READY、重複第63列清空並讀回；必須正式重跑查證。
- **來源品質**：第55列 `invalid_handoff_record` 為舊 ERROR，不能僅改 READY 或 ACKED 冒充復原。以新版本正式 `HandoffItem` 驗證及 Job `life_handoff_invalid fields=...`（僅欄名與錯誤類型）釐清後才依業務變動重算 `content_hash`。若新版本能合法重試既有 ERROR，允許 importer 在 DB commit 後自然寫回 ACKED。
- **第31欄 rollout 嚴格順序**：目前正式 30 欄，最新版 GitHub main 新增可選 `verification_status`（`unknown/pending_review/verified`）及 `LEGACY_HEADERS` 30欄相容。**不能先改正式 Sheet 表頭成31欄，再讓舊版 Job 讀取**；先新 SHA 四項 CI／候選／固定 staging 通過，將具30/31欄相容的 Job image/args/env 依正常 V3 production promotion 對齊正式 API digest 並確認 readback；接著擴充正式 Sheet AE 表頭、回讀確認，舊活動 AE 留空視為 unknown、不可偽造已核實。新業務內容（含核證狀態）依版本 hash 更新相同 event_key，唯有改變實質業務時才更新 READY；最後執行 Job，核 PG 版本及 Sheet ACK、Flutter 核證標籤與來源/報名兩網址。對任何不一致 fail closed，保留原版可回滾。
- **測試/部署 gate**：新程式 tests/CI、部署 digest、Cloud Run Job Execution、PostgreSQL `event_key + content_hash`、Sheet 實際 ACK、前台一般用戶 readback、Drive 當日唯一 Log 與 A7/B10 分面向 PASS/FAIL/NOT VERIFIED。完整 E2E 證據前標 PARTIAL，不因 CI 綠燈或文件修改稱 DONE。
