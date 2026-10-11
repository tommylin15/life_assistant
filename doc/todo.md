# Life — Active TODO（2026-10-11）

**唯一活動產品規格：** [UX V3｜活動使用者功能](curated_activity_user_features.md)；下列狀態取代 10/10 過時的星等 UI、七種個人操作與第三個「精選」導覽工項。產品規格 APPROVED；新 UX 的 source、CI、runtime 尚 **NOT VERIFIED**。

## A. 活動 UX V3 與待辦／日曆串接

| Priority | 工項 | Source / Verification |
|---|---|---|
| P0 | 合併三入口為「限時機會」「活動探索」兩個使用者入口，舊精選路徑轉址，停用舊免費活動主導覽但保留舊 API／資料 | 既有三入口 source 存在；UX V3 **NOT IMPLEMENTED** |
| P0 | UI 全面隱藏星等，取消 API 以星等篩選／預設排序 | 現有星等 UI/API 仍在：**NOT IMPLEMENTED** |
| P0 | 各入口預設查 5 個主活動群組、再看 10 個；限時／活動時間排序，最新收錄、跨日期、已確認失效及未知時間語意 | 現有 API 預設 20、Flutter 每頁 50，先按星等排序：**NOT IMPLEMENTED** |
| P0 | 六種速查各入口、一般搜尋（標題／主辦／地點／現有摘要），後端 DB 全量查詢 | 現有城市／類別完全相等篩選，無 keyword 搜尋：**NOT IMPLEMENTED** |
| P1 | 固定縣市→北中南東離島、縣市／行政區選項、DB 類別與費用篩選；不做定位或 AI | **NOT IMPLEMENTED** |
| P1 | 主活動一次收藏，兩入口「全部／已收藏」切換，保留已結束收藏、去重和舊收藏遷移 | `save` per activity 已有；主活動共用收藏／清單 **NOT IMPLEMENTED** |
| P1 | 活動建立既有 Task：確認到期日、來源網址與正確子活動，待辦列表直接點「前往網址」 | Task.note/source_type/ref 基礎 **SOURCE IMPLEMENTED**；待辦頁仍純文字 URL，跨功能驗收 **NOT VERIFIED** |
| P1 | 活動日期標記用既有 Google Calendar 全天透明事件，帶地點與活動網址，Life 日曆直接點「前往網址」 | Google description/transparent 基礎 **SOURCE IMPLEMENTED**；日曆頁仍純文字 URL，真實 Google OAuth/readback **NOT VERIFIED** |
| P1 | 卡片縮減為收藏／待辦／日曆標記／前往網址，保留主活動與子場次、回上一頁篩選狀態 | **NOT IMPLEMENTED** |

## B. 必要整合測試／驗收

- PostgreSQL：parent／child 去重與收藏映射、中文搜尋、5+10 分頁、穩定排序、時區 Asia/Taipei、跨日活動、未知時間、失效收藏。
- Task：從活動產生的 Task 在既有待辦列表看得到、可編輯完成／取消、能點活動 URL；不因重試或同活動兩入口重複建立；授權及不同帳號隔離，原始網址更新不靜默覆寫私人備註。
- Calendar：只有有據活動日期才能建立 Google 全天資訊標記；exclusive end、transparent、不預設提醒；Life 與 Google 都可讀回，Life 日曆可點 URL；OAuth/失敗時不虛報成功，跨帳號、去重和取消處理有證據。
- 回寫後分層回報 **implementation / tests / CI / staging deployment / runtime / integration = PASS / FAIL / NOT VERIFIED**，完整才可標 DONE。

## C. 仍未完成的資料／發布工作（不因 UX 文件完成而關閉）

- [交接契約](curated_sheet_job_ingestion.md)：真實 Drive「交接資料」READY → GCP Job 讀取 → PostgreSQL 穩定鍵／版本去重 → DB commit → Sheet ACKED/ERROR → owner/Flutter 讀回，與 30 天 ACK 清理；真實 Sheet scope、Job、runtime **NOT VERIFIED**。
- CI/CD V3：每次 main SHA 的完整測試、GHCR digest、候選／固定 staging exact-SHA、Google owner OAuth、API/DB/Flutter 真實 readback 獨立驗收；既有固定 staging OAuth 曾對舊 SHA PASS，不可當成本 SHA 或 UX V3 PASS。[CURRENT_STATE](CURRENT_STATE.md)
- Admin rollout／個人導覽與首頁卡片維持現有模式；Drive AI admin provider 補強仍 Deferred，不阻擋活動 UX。
- **持續取消**：Life 端來源 crawler、舊 Excel source scanner、Queue／claim／lease、第二輪 AI、重啟舊來源 14 天驗收、為本期新增 AI 向量搜尋／GPS／推播／代搶票。舊 DB/migration/API 留相容，不做破壞性刪除。
