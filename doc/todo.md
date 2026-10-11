# Life — Active TODO（2026-10-11）

**唯一活動產品規格：** [UX V3｜活動使用者功能](curated_activity_user_features.md)。2026-10-11 已將 UX V3 與三風格視覺共用元件寫進 main，完整測試與 staging/readback 獨立驗收。新 source 為 **PARTIAL**，不得將新 CI 或部署標成已驗收；以下是仍須特別核對的關卡。

## A. 活動 UX V3 與三風格 UI（2026-10-11 source 已進 main）

| Priority | 工項 | 本次 source 狀態與待核對證據 |
|---|---|---|
| P0 | 兩入口＋舊精選路徑相容轉向、保留首頁 events 卡 | SOURCE IMPLEMENTED；Flutter／staging navigation NOT VERIFIED |
| P0 | 星等從活動 UI 隱藏、取消星等預設排序 | SOURCE IMPLEMENTED；DB 保留舊欄位，API 相容參數忽略；需 SQL／畫面證據 |
| P0 | 5 主群組首載、後續 10 群組、has_more 與穩定主子分組 | SOURCE IMPLEMENTED；offset 跨上游更新可能頁面漂移，真正 snapshot cursor 尚 PARTIAL |
| P0 | 兩入口各六速查、中文搜尋、跨日與最新收錄 | SOURCE IMPLEMENTED；台北時區／取消與 unknown runtime E2E NOT VERIFIED |
| P1 | 固定區域、縣市／行政區／類別／費用篩選 | SOURCE IMPLEMENTED；行政區以文字完整相等輸入，動態下拉選單未實作 |
| P1 | 兩入口主活動收藏／已收藏、舊子場次收藏兼容 | SOURCE IMPLEMENTED；PostgreSQL 跨帳號／舊收藏／重新入庫 E2E NOT VERIFIED |
| P1 | 活動建立原有 Task、確認是否設報名時間／網址可點 | SOURCE IMPLEMENTED；新增 Task/DB/readback 跨功能實測 NOT VERIFIED |
| P1 | Google Calendar 全天 transparent 日期標記、Life 日曆開網址 | SOURCE IMPLEMENTED；真實 OAuth／Google & Life 雙向 readback NOT VERIFIED |
| UI | 三種風格與亮暗切換、六功能視覺辨識／首頁／筆記卡片 | SOURCE IMPLEMENTED（基礎與局部卡片）；海報完整插畫和 18 視圖視覺驗收 PARTIAL |
| Release | 合併的單次 CI／staging／驗收／發布 | 最新程式再啟動完整 CI；先前 #886 CI PASS 屬於舊 SHA，最新版本 staging/owner OAuth/runtime NOT VERIFIED |

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

**2026-10-11 最新整合補強：** 已加入三風格 × 四寬度 × 六功能的基礎 Widget 測試、活動桌面雙欄、共享 action readback 與跨入口刷新、可編輯待辦標題安全驗證，以及取消／過期報名的歷史收藏呈現。完整真實畫面、連動 Google OAuth、staging SHA 均待新 SHA 驗收。不得把先前 staging #38 或任何舊 SHA 的結果當作本批 PASS。
