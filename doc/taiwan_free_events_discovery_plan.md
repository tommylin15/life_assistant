# 台灣免費活動探索與報名追蹤 — Product / Engineering Plan

狀態：**PLANNED / NOT IMPLEMENTED**（2026-10-09）  
產品優先級：**Calendar #8 完成後第一優先（P0 after Calendar）**。正式排序以 `doc/phase1_delivery_order.md` 為準。

## 1. 產品目標與範圍

在台灣發現**新鮮、可查證、尚可參與**的免費活動（含免費講座、展覽、導覽、課程、工作坊、社群活動）；顯示活動與報名起訖時間，讓使用者個別選擇：加入通知／加入待辦／建立筆記（選擇既有筆記資料夾）。

使用者只看有效候選清單；不因掃描到活動就自動建立任何個人日曆、待辦、筆記或推送通知。Admin 只在現有 Flutter Web 入口看到來源健康、更新、異常與清理狀態，不另建專用後台。必要時可見來源維護操作。未確認來源或時間一律顯示「待確認」，不虛構數值。

**優先衡量是否在報名開始前發現**，而不以收錄總量衡量成功。

## 2. 優先級／與 Phase 1 範圍邊界

依使用者 2026-10-09 的明示決定：先完成 Calendar #8 的全部驗收，再將此功能作為**下一個第一優先產品開發項目**，排在既有 #9 Activity / Integrations、#10 Foundation tail、#11 Final Release Gate 的新增開發工作之前；不刪除、不宣稱已完成或跳過這些原有工作包。

本功能以 **Post-Calendar Activity Discovery track** 另列里程碑，**不直接篡改現有 11-package 完成分母**；是否將其設為 Phase 1 release blocker 須在開始實作時依 scope freeze / release governance 明確記錄。現況 Calendar #8 尚未有完整最新 runtime/UI/true-account PASS 證據，本需求只是規劃，不等同已進入實作。

## 3. 活動發現管線（Asia/Taipei）

| 層級 | 來源 | 預設頻率 | 功能 |
| --- | --- | --- | --- |
| L1 高價值第一線 | 官方 RSS、新聞稿、主辦單位網站、原始報名頁 | **每日 06:00 與 18:00，每 12 小時** | 優先發現新公告；發現後核對原始資料 |
| L1 補漏來源 | BeClass、ACCUPASS、KKTIX、EventGo、小藝行事曆、Citytalk | **每 12 小時**，來源合規與存取條件通過後才啟用 | 發現候選活動，非最終事實來源 |
| L2 官方資料 | 文化部藝文活動、觀光署/TDX、縣市活動 API | 每日一次 | 補漏、結構化資料與交叉比對 |
| L3 來源探索 | data.gov.tw 完整目錄與異動清單、官方網站連結發現 | 每日一次 | **發現/更新資料來源**，不能用來保證活動即時性 |
| 既有追蹤 | 使用者已追蹤活動／報名頁 | 每日核對；接近已確認報名時間可每小時核對 | 重大變動提醒、更新個人同步物件 |
| 清理 | 活動有效期、保留期、來源健康 | 每日一次 | 過期撤出選擇、封存／刪除 |

**區分輪詢延遲與來源發布延遲**：12 小時輪詢可能漏過極短名額活動，不得宣稱即時保證。政府目錄的每日更新只代表來源登錄節奏，不代表活動/報名資訊同步速度。每筆候選保存公告時間（若可驗證）、首次發現、最後驗證、報名開放時間與來源，衡量「報名前發現率」、「資料年齡」、「發現延遲」、「活動仍有效率」。第一期至少 14 天對照原始公告與官方資料出現時間，以實測決定來源優先級。

## 4. 來源登錄／合規與監控

可配置的 Source Registry：`source_id`、provider、官方/聚合分級、entry_url、type（RSS/API/HTML）、adapter_version、schema_version/hash、預期更新頻率、last_checked_at、last_success_at、last_content_change_at、授權/robots/條款狀態、rate limit、enabled、health（PASS / FAIL / NOT VERIFIED）、失敗原因和修復記錄。

以官方 API / Feed 優先；沒有公開 API 的站點先確認合法存取，避免把第三方未授權聚合資料當作可轉載。監控 HTTP/認證、schema、解析成功率、欄位完整率、資料量突變、長時間無新資料、原始頁消失；來源異常隔離單一 Adapter、退避重試、恢復補抓，不把來源失效當成活動取消，不因抓不到就刪除。

GitHub 元件候選（實際使用前再次審核版本/安全/授權）：`feedparser` RSS/Atom、`trafilatura` 正文解析；`changedetection.io` / `RSSHub` / `Huginn` 僅二期評估，尤其 RSSHub AGPL-3.0 需法律/部署授權審核。不得只因某 repo 存在就直接導入或新增常駐 VM。

## 5. 驗證、正規化、去重

每筆活動保留 canonical event、場次 session、原始來源 reference / fetch evidence、主辦者、地區、地點、活動起訖、`registration_start_at`、`registration_end_at`、報名 URL、免費分類（完全免費／條件免費／待確認／非免費）、名額/額滿狀態、`verified_at`、`valid_until`、狀態與 version。

報名**日期**若缺精確時分，不得硬填 09:00；若沒有公布開放時間，顯示待公告。搜尋結果／聚合摘要只能用來發現，入庫發布前須查證主辦單位或正式報名頁；過時、報名截止、額滿或活動結束的候選，不可讓使用者新增已失效的報名操作。無需報名的活動可另提供活動日期提醒。

去重優先使用 `(source, stable_external_id)` 與官方 canonical URL，輔以主辦、標題、場次、地點、時間相似度（模糊比對需要審核/可回退），避免把不同場次誤合併。使用者決策與投遞紀錄持久化；通知以 `(user_id, canonical_event_id, session_id, notification_type, version/semantic_change_key)` 冪等，普通活動僅通知一次，重大變更（延期、報名改期、取消等）可單獨通知，絕不重複建立日曆／待辦／筆記。

## 6. UI 與權限

一般使用者：有效免費活動列表，按縣市、日期、主題及報名狀態篩選；可分別勾選「報名／活動提醒」、「建立待辦」、「建立筆記」，筆記需選擇其可存取的資料夾；顯示來源、查證時間、免費條件、報名起訖（沒有就明示未知），允許略過／稍後決定／取消追蹤。不得因「收藏/查看」就隱性建立所有三項。

管理員：復用現有 Flutter Web 設定/管理入口，只顯示來源監控、同步健康與手動重試選項，不另做後台；**FastAPI 端必須驗證 Google 登入主體、UID-based admin allowlist/RBAC**，任何管理 API 不得只靠前端隱藏。使用者提供 admin email `tommylin15@gmai.com`（疑似拼字錯誤）；**在使用者核實與已登入的 verified identity 對齊前不可授權此字串或任何猜測帳號**，本文件不創建 admin policy。

## 7. 技術架構／過渡與正式排程

目標沿用既有 Firebase Hosting → Flutter Web → Cloud Run FastAPI → PostgreSQL。使用 Cloud Scheduler（Asia/Taipei `0 6,18 * * *`）觸發受認證的 Cloud Run 任務/既有 Backend 適當工作端點，實際以目前工程實作、最小權限、成本與併發/重試安全性選型，不預設要加 VM 或獨立長駐服務。使用 PostgreSQL 保存 `event_sources`、`source_fetch_runs`、`event_candidates`、`event_sessions`、`event_source_links`、`event_versions`、`user_event_decisions`、`event_notification_deliveries`、`event_external_links` 與 retention tombstone；欄位/表名僅為設計草案，建 migration 前核對現有 schema。

**目前 ChatGPT 定期掃描（06:00/18:00）只是外部過渡試行，不代表 Cloud Run job、Scheduler、資料庫與通知機制已上線。** 正式 GCP 實測穩定且去重/權限驗收 PASS 後，應先做切換與同批重複通知防護，再停用 ChatGPT 過渡任務，避免雙重發送。真實 production 排程尚未建立，NOT VERIFIED。

可再利用既有 Calendar / Tasks / Notes API：每個使用者核准操作獨立執行，Calendar 保存 provider event id，Tasks 保存 task id，Notes 保存 note id / folder id；更新與撤銷走冪等交易/補償和部分失敗狀態，嚴禁系統自行完成報名或假稱已報名。

## 8. 過期與刪除

報名截止、額滿或活動結束時，不再允許過期報名操作；活動結束退出一般候選清單。**建議預設活動結束 30 天後**清除非必要原始內文、聚合快取與來源擷取內容；僅保留最小去重/tombstone、稽核、依法必要資料及使用者已建立的個人筆記、待辦、行事曆等外部關聯，且個人資料必須依既有授權/刪除規則處理。刪除任務需可重跑、保護使用者產出與 backups，不得直接視為 production 大量刪除授權；若涉及大量或不可逆 production 清理，需另外取得明確確認。

## 9. 分階段交付與驗收

1. **S0 來源/法律實測**：盤點官方 feed/APIs、民間平台條款、可抓取範圍與最近更新時間；14 天新鮮度量測與來源健康規範。
2. **S1 掃描/正規化**：Source Registry + 官方 RSS / 新聞稿 / 報名頁 Adapter、文化/觀光每日補漏、原始證據、來源故障隔離、PostgreSQL 去重與過期清理。
3. **S2 Flutter 候選列表**：有效活動可搜尋/篩選，過期禁用，admin-only 來源健康入口；真實 user/admin API auth、mobile/desktop UX tests。
4. **S3 個人動作**：通知／待辦／筆記三個獨立決策、筆記資料夾、Calendar 精確開放報名提醒、provider 失敗部分成功、版本更新與去重投遞。
5. **S4 GCP 正式切換**：Cloud Scheduler + Cloud Run 定時跑真實來源、負載/費用與授權、失敗重試補抓、真實 Google provider integration、移除 ChatGPT 雙跑、runtime/rollback evidence。

每一階段分別記錄 implementation、tests、CI、deployment、runtime、integration、permissions、UI/mobile/desktop 及來源新鮮度驗收 **PASS / FAIL / NOT VERIFIED**；僅全部必要證據通過才標 **DONE**。目前全部產品實作與 GCP 驗收 **NOT VERIFIED**，需求規劃為 **PARTIAL**。
