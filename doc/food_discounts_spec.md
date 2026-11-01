# Life — 雙北 41 區美食優惠探索正式規格（V0.5.2 / Runbook V1.3.2 整合版）

本文件將原位於 Google Drive `life_assistantGPT/美食優惠探索｜試行/` 之《美食優惠探索 V0.5.2｜雙北41區單一總排程與效期治理》與《雙北41區單一總排程操作手冊 V1.3.2》正式納入 `life_assistant` 主線工程，定義獨立功能邊界、資料庫契約、API、前端頁面與 VM 獨立排程。

---

## 1. 功能定位與系統邊界

- **獨立功能入口**：與「台灣活動探索（`explore`）」完全分離，於 Life Assistant 設立獨立功能 **「美食優惠」**：
  - Feature Key：`food_discounts`
  - 前端路由：`/more/food-discounts`（歸類於「活動與機會」導覽群組，亦可釘選至首頁卡片或底部捷徑）
  - 後端 API：`/api/v1/food-discounts`、`/api/v1/food-discounts/filters`、`/api/v1/food-discounts:batch`
  - 資料庫表：PostgreSQL `food_discounts`（Alembic `20261101_0026` 非破壞性新增）
- **嚴格隔離原則**：美食優惠候選絕不混入 `curated_activities`（台灣活動探索池）或活動交接表，避免日常餐飲促銷稀釋藝文/親子/地方活動列表。

---

## 2. 對象、品類與搜尋優先序

聚焦**台北市 12 區＋新北市 29 區（共 41 行政區）**上班族與日常高頻飲食優惠：

- **P0 一般手搖飲**：純茶、奶茶、珍奶、鮮奶茶、果茶、茶飲連鎖與街邊獨立茶飲。
- **P0 台灣國民美食**：早餐店（蛋餅、飯糰、豆漿、三明治）、便當／自助餐、滷肉飯／雞肉飯／麵食、牛肉麵、鍋貼水餃、滷味、鹽酥雞／雞排、麵線、肉圓、臭豆腐、豆花、甜湯與台式點心。
- **P0 咖啡／烘焙／平價甜點／下午茶／商務午餐**。
- **P1 聚餐／一般餐廳／飯店餐飲／限定餐券／銀行合作**：不得因飯店或大型餐廳資訊易讀而排擠 P0 搜尋配額。

### 雙北 41 行政區週一／三／五輪替計畫

| 探索日 | 責任行政區（共 41 區） | 最低實查組數（手搖飲＋國民美食各 1） |
| --- | --- | --- |
| **週一（MON，14 區）** | 台北市：中正、中山、松山、大安、信義<br>新北市：板橋、中和、永和、新莊、三重、新店、汐止、林口、蘆洲 | 28 組 |
| **週三（WED，14 區）** | 台北市：大同、萬華、文山、南港<br>新北市：土城、樹林、鶯歌、三峽、淡水、五股、泰山、瑞芳、深坑、八里 | 28 組 |
| **週五（FRI，13 區）** | 台北市：內湖、士林、北投<br>新北市：石碇、坪林、三芝、石門、平溪、雙溪、貢寮、金山、萬里、烏來 | 26 組 |
| **週二／四／六／日** | 僅執行每日效期維護與 7 日到期無終日來源追查補正，不執行分區新搜尋 | — |

---

## 3. 低驗證收錄門檻与誠實揭露（V0.5.2）

- **門檻基準**：只收公開來源明示 **「買一送一」** 或 **「名目折扣 ≥ 20%（8 折或更低價）」** 之優惠情報（狀態記為 `COLLECTED_SOURCE_CLAIM`）。
  - 第二件折扣依整單兩件折幅計算（例如兩杯同價時「第二杯半價」＝省 25%，需明示「同價假設」）。
  - 折抵 NT\$50（含）以下之單純固定金額、85 折／9 折／95 折、無原價可比對之「特價」或純贈品，不列入當期推薦（分別標為 `FILTERED_BELOW_THRESHOLD` 或 `LEAD_INCOMPLETE`）。
- **免逐店核實、保留來源揭露**：
  - 不執行電話查核、到店實測、含服務費精算或即時庫存確認。
  - 每筆必備公開可追溯 `source_url`，如實保留來源載明之期間、外送平台、會員／信用卡或指定門市限制；未知欄位留空，絕不臆造地址、價格或截止日。
  - 所有對外展示統一揭露：**「公開來源宣稱，未逐項核實，不保證到店可使用」**。

---

## 4. 效期治理與 7 日續期補正（V1.3.2）

- **日期分離**：分別記錄 `first_seen_date`（AA）、`claim_deadline`（AB，領券截止）、`redemption_end_date`（AC，兌換截止）、`offer_end_date`（AD，活動截止）。
- **明確截止日（AD 有值）**：依 Asia/Taipei 日期，截止當日仍有效，翌日 00:00 自動轉為 `EXPIRED` 下架；領券截止（`today > AB`）轉為 `CLAIM_CLOSED`，不再對新客推薦。
- **無明確截止日（AD 空白）**：
  - 首次發現 7 天內顯示為 `VISIBLE_SOURCE_ONLY`。
  - 滿 7 天（`AG <= today`）由排程重查原公開來源 `N`：
    - 若公開來源仍明示活動持續有效：於「效期追蹤」追加收據，更新 `AE = 本次正面來源日`、`AF = 查詢日`、`AK = ACTIVE_ON_SOURCE`，`AG` 自動延後 7 天，維持 `VISIBLE_SOURCE_ONLY`（不因首次發現逾 30 天而強制關閉）。
    - 若無明確持續有效證據：更新 `AF` 與結果，`AE` 不變，狀態自動轉 `HIDDEN_REFRESH_DUE` 暫停推薦；距最後一次正面證據（`AE` 或 `AA`）滿 30 天自動轉 `ARCHIVED_STALE` 封存，保留歷史不刪除。
- **Google Sheets 陣列公式保護契約**：
  - 主表（`1qwzG8P6wDLtPINoUf-N670TeHVSC6m7jlihDeBjb13U`）「優惠候選」之 `AG2`（`next_refresh_date`）與 `AI2`（`visibility_status`）為 `ARRAYFORMULA` 陣列公式錨點。
  - 新增候選列時，僅可對 `A:AF`、`AH`、`AJ:AL` 分段寫入，**嚴禁覆寫 `AG` 與 `AI` 欄或使用 `appendCells` 破壞陣列公式**；寫入後必須核對「總排程測試」`C10 = 0`（公式缺漏數為 0）。

---

## 5. 交換池（`美食優惠｜交接資料.xlsx`）與雙向 ACK 契約

比照「台灣活動探索（`台灣活動｜交接資料.xlsx`）」架構，於 Google Drive `life_assistantGPT/美食優惠探索｜試行/` 設立獨立交換池 **`美食優惠｜交接資料.xlsx`**（分頁名稱：`交接資料`，共 31 欄 `A:AE`），解耦母表 `ARRAYFORMULA` 運算與 Life PostgreSQL 入庫：

1. **固定 31 欄結構（`A:AE`）**：
   - `A`：`candidate_key`（唯一識別鍵）
   - `B`：`content_hash`（依 25 個核心業務欄位以固定順序 Canonical JSON 計算之 SHA-256 雜湊值）
   - `C:Z`：24 個業務欄位（`city`, `district`, `merchant`, `category`, `offer_summary`, `offer_type`, `nominal_discount`, `fixed_discount_ntd`, `original_price_ntd`, `offer_price_ntd`, `period_text`, `address`, `source_url`, `notes`, `claim_status`, `visibility_status`, `first_seen_on`, `claim_deadline_on`, `redemption_ends_on`, `offer_ends_on`, `last_positive_on`, `next_refresh_on`, `date_basis`, `disclosure`）
   - `AA:AE`：交換池狀態與回執欄位：
     - `handoff_status`：`READY` / `ACKED` / `ERROR`
     - `handoff_updated_at_tpe`：ISO-8601 `+08:00` 時間戳
     - `life_ack_at_tpe`：Life 匯入器完成入庫回寫之 `+08:00` 時間戳
     - `life_import_result`：`CREATED` / `UPDATED` / `UNCHANGED` / `FAILED`
     - `life_error`：驗證或入庫失敗原因摘要（成功時為空白）
2. **狀態流轉與未變動保護**：
   - 既有已 `ACKED` 且 `content_hash` 未改變之列，完全保留原有 `life_ack_at_tpe` 與 `life_import_result` 不重寫。
   - 新增候選或因 7 天到期／30 天歸檔導致 `visibility_status`、`claim_status`、`last_positive_on` 變更時，`content_hash` 自動更新並標記 `READY`，觸發 Life 匯入器更新 `food_discounts` 後回寫 `ACKED`（`UPDATED`）。

---

## 6. VM 獨立排程與 Life PostgreSQL 同步管線

- **排程單元**：
  - `tw-food-discount-discovery.timer`：每日 **04:45 Asia/Taipei（`20:45:00 UTC`）** 觸發。
  - `tw-food-discount-discovery.service`：設定 `After=network-online.target docker.service tw-activity-discovery.service`，確保緊接在台灣活動探索批次（04:00 TPE 啟動）完成之後執行，避免資源與網路競爭。
- **執行流程**：
  1. 讀取 Google Drive `life_assistantGPT/美食優惠探索｜試行` 最新母表、交換池 `美食優惠｜交接資料.xlsx` 與手冊，建立當日唯一批次鍵 `FOOD-UNIFIED-YYYYMMDD`。
  2. 執行每日效期檢查與 `AG <= today` 無終日優惠來源追查；若為週一／三／五則依輪替計畫執行 14/14/13 區動態網頁搜尋與去重寫入，並完成母表（`C10 = 0`）與試行紀錄 Doc 讀回。
  3. 執行 `.venv/bin/python scripts/run_tw_food_discount_batch.py --stage-handoff --sync-db --upload-gdrive`：
     - 將母表變更同步至 `美食優惠｜交接資料.xlsx`（新列或異動列標為 `READY`，未變動 `ACKED` 列原地保護）。
     - 依交換池執行 PostgreSQL `food_discounts` 交易入庫（寫入 `ExecutionLog` `action_type = "food_discounts.handoff"`）。
     - 將交換池回寫為 `ACKED`（`CREATED` / `UPDATED` / `UNCHANGED`）並上傳回 Google Drive，逐鍵讀回驗證 `READY = 0`、`ERROR = 0`。
