# 台灣免費活動探索與報名追蹤 — Product / Engineering Plan

狀態：**APPROVED PLAN / NOT IMPLEMENTED**（2026-10-09，競品缺口與階段範圍修訂）  
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

**資料建模以「活動 Event → 場次 Session → 報名機會 Registration Opportunity（報名區間／票種／名額）」為第一期必要設計。** 一場活動可有多個場次、同場次可有不同免費／付費票種及報名窗口，不可用單一全域報名時間覆蓋所有場次。每筆記錄保留 canonical event、session、registration opportunity、主辦單位 Organizer、原始來源 reference / fetch evidence、地區／地點、活動起訖、`registration_start_at` / `registration_end_at`、報名 URL、免費分類（完全免費／條件免費／待確認／非免費）、資格條件、押金／材料費／門票等額外成本、名額/額滿/候補狀態、`verified_at`、`valid_until`、狀態與 version。

報名**日期**若缺精確時分，不得硬填 09:00；若沒有公布開放時間，顯示待公告並允許使用者**選擇追蹤公布結果**，公布後再依訂閱決策建立具體報名提醒。候選生命週期：`unannounced`（時間待公告）、`upcoming`、`open`、`full`、`waitlist_available`、`closed`、`cancelled`、`event_ended`；狀態與來源證據、檢查時間、適用場次／票種綁定，異動需版本化；不可由抓取失敗直接判定取消。搜尋結果／聚合摘要只能用來發現，入庫發布前須查證主辦單位或正式報名頁；過時、報名截止、額滿且無候補或活動結束的候選，不可讓使用者新增已失效的報名操作；仍有合法候補的活動可顯示候補選項。無需報名的活動可另提供活動日期提醒。

去重優先使用 `(source, stable_external_id)` 與官方 canonical URL，輔以主辦、標題、場次、地點、時間相似度（模糊比對需要審核/可回退），避免把不同場次誤合併。使用者決策與投遞紀錄持久化；通知以 `(user_id, canonical_event_id, session_id, notification_type, version/semantic_change_key)` 冪等，普通活動僅通知一次，重大變更（延期、報名改期、取消等）可單獨通知，絕不重複建立日曆／待辦／筆記。

## 6. UI 與權限

一般使用者：有效免費活動列表，按縣市、日期、主題、活動型態及報名狀態篩選；MVP 提供最基本的興趣／地區篩選與排除，不提前建置大型推薦模型。可分別勾選「報名／活動提醒」、「建立待辦」、「建立筆記」，筆記需選擇其可存取的資料夾；顯示來源、最後查證時間、免費/額外費用/參加資格、場次/票種、報名起訖（沒有就明示未知），允許追蹤報名時間待公告、略過／稍後決定／取消追蹤。**查看、收藏或來源掃描都不等於同意通知或建立任何個人物件**。使用者可手動標示待報名／已報名／候補／取消；外站操作不自動假定成功。Calendar 衝突需警示，不自行覆蓋既有行程。

管理員：復用現有 Flutter Web 設定/管理入口，只顯示來源監控、同步健康與手動重試選項，不另做後台；**FastAPI 端必須驗證 Google 登入主體、UID-based admin allowlist/RBAC**，任何管理 API 不得只靠前端隱藏。使用者提供 admin email `tommylin15@gmai.com`（疑似拼字錯誤）；**在使用者核實與已登入的 verified identity 對齊前不可授權此字串或任何猜測帳號**，本文件不創建 admin policy。

## 7. 技術架構／過渡與正式排程

目標沿用既有 Firebase Hosting → Flutter Web → Cloud Run FastAPI → PostgreSQL。使用 Cloud Scheduler（Asia/Taipei `0 6,18 * * *`）觸發受認證的 Cloud Run 任務/既有 Backend 適當工作端點，實際以目前工程實作、最小權限、成本與併發/重試安全性選型，不預設要加 VM 或獨立長駐服務。使用 PostgreSQL 保存 `event_sources`、`source_fetch_runs`、`event_candidates`、`event_sessions`、`event_source_links`、`event_versions`、`user_event_decisions`、`event_notification_deliveries`、`event_external_links` 與 retention tombstone；欄位/表名僅為設計草案，建 migration 前核對現有 schema。

**目前 ChatGPT 定期掃描（06:00/18:00）只是外部過渡試行，不代表 Cloud Run job、Scheduler、資料庫與通知機制已上線。** 正式 GCP 實測穩定且去重/權限驗收 PASS 後，應先做切換與同批重複通知防護，再停用 ChatGPT 過渡任務，避免雙重發送。真實 production 排程尚未建立，NOT VERIFIED。

可再利用既有 Calendar / Tasks / Notes API：每個使用者核准操作獨立執行，Calendar 保存 provider event id，Tasks 保存 task id，Notes 保存 note id / folder id；更新與撤銷走冪等交易/補償和部分失敗狀態，嚴禁系統自行完成報名或假稱已報名。

## 8. 過期與刪除

報名截止、額滿或活動結束時，不再允許過期報名操作；活動結束退出一般候選清單。**建議預設活動結束 30 天後**清除非必要原始內文、聚合快取與來源擷取內容；僅保留最小去重/tombstone、稽核、依法必要資料及使用者已建立的個人筆記、待辦、行事曆等外部關聯，且個人資料必須依既有授權/刪除規則處理。刪除任務需可重跑、保護使用者產出與 backups，不得直接視為 production 大量刪除授權；若涉及大量或不可逆 production 清理，需另外取得明確確認。

## 9. 分期交付（依賴順序，不等同現有 11-package 分母）

本功能必須在 **Calendar #8 真實產品驗收完成後**才啟動正式實作。MVP 由 M0–M4 組成，不能因 M0 研究通過就稱產品 DONE。第一版增強 E1 與第二階段 E2 是產品擴充，不是 MVP 的 release blockers。詳細排序以 `doc/phase1_delivery_order.md` 為準，所有階段遵守 `PROJECT_RULES.md`、`acceptance.md` 及既有 release governance。

| Gate | 優先 | 交付範圍 | 必要驗收證據 | 狀態 |
| --- | --- | --- | --- | --- |
| M0 Source Baseline | MVP | 最少 14 天來源時效觀測；官方 Feed/API/公告與聚合站授權確認；固定正反測試樣本；偵測來源新增/下架 | 有可追溯公告時間／首次發現／報名開放時間與來源授權紀錄；不把每日官方資料宣稱為即時 | NOT VERIFIED |
| M1 Discovery Core | MVP | Cloud Run/既有 Backend 適用 job、Source Registry／Adapter、PostgreSQL Event–Session–Registration Opportunity、Organizer、證據、去重、生命週期、來源安全與過期政策 | migration 可重跑；同活動多來源/場次/票種負測試；故障隔離、恢復補抓與來源異常不誤刪；安全測試 | NOT VERIFIED |
| M2 User & Admin UI | MVP | Flutter Web 有效候選清單、基本地區／興趣篩選、免費條件、場次／報名狀態、追蹤待公告、過期不可選；僅既有設定入口顯示 admin 來源健康 | 真實 UID admin/non-admin API RBAC、401/403、mobile/desktop 操作、來源更新時 UI 一致性 | NOT VERIFIED |
| M3 Personal Actions | MVP | 通知、待辦、筆記分別授權；筆記資料夾；精確報名提醒與報名待公告的後續通知；最小手動已報名狀態；行事曆衝突提示與使用者取消追蹤 | 真實 Google Calendar/Task/Note 整合；幂等重試、跨來源通知去重、時間異動更新、部分失敗、取消與補償 | NOT VERIFIED |
| M4 GCP Cutover | MVP | 台灣時間 06/18 Scheduler、Cloud Run 真實掃描、PostgreSQL durable states、監控、清理、過渡期間併行去重／正式切換 | 真實 12 小時排程、權限、來源成功率、新鮮度、重試、成本、rollback/恢復、真實使用者 UI/API；通過後停用 ChatGPT 過渡任務 | NOT VERIFIED |
| E1 Post-MVP enhancement | 第一版增強 | 主辦單位追蹤與來源擴張、進階個人興趣／距離排除、可訂閱活動摘要／靜音時間、細緻手動報名/候補管理與跨系統同步 UX | 偏好/取消訂閱、追蹤不同主辦單位與變更後去重、頻率設定、跨使用者隔離 | NOT VERIFIED |
| E2 Advanced discovery | 第二階段 | 使用者貼連結擷取、交通時間/距離、電子報作為額外來源（遵守同意與權限）、進階個人化推薦；需要來源品質證據再擴大 | 授權/合規/成本驗收；推薦品質實測，不能自動提高寫入權限 | NOT VERIFIED |

**暫時不做：** 自動替使用者報名或付款、繞過網站反爬限制、抓取有權限障礙的內部 API、大型推薦模型、完整社交/售票平台、獨立後台/常駐 VM、無證據的大規模聚合資料鏡像。

## 10. 詳細業務規則與跨系統一致性

1. **Activity 與 Registration 分離：** 報名機會可屬於某場次/票種（包含完全免費、限額免費、部分免費）。同一場次可能有報名起訖改期、額滿轉候補；用有來源時間戳的狀態事件維護，禁止用 LLM 推斷確切分鐘或剩餘名額。
2. **候選發布門檻：** `verified` 才能執行實際報名提醒；只有聚合/新聞摘要時為 `unverified`，可提示待驗證或讓使用者選擇「通知我查證結果」，不可偽稱可以報名。釣魚、詐騙、受限制、無法證明免費、需另付費、已失效的項目不得以「完全免費且可報名」曝光。
3. **個人參與狀態：** `interested` / `registration_pending` / `registered_by_user` / `waitlisted_by_user` / `cancelled_by_user`；使用者自行按「已報名」才可確認，或在將來有合法官方 integration 時依授權更新。自動探索不能生成「已報名」的事實。
4. **通知類型與同意：** 新活動預設**只進清單不推播**；摘要訂閱屬 E1，可獨立 opt-in。報名時間公布、即將開始、重大延期/取消可在使用者選定追蹤後依各自設定觸發；普通來源內文微調靜默更新。重大異動只通知變更類型與版本一次。靜音時段/頻率設定列 E1，MVP 至少支援取消追蹤與通知通道有效性檢查。
5. **衝突與撤銷：** 使用者已有行事曆時段行程時先顯示衝突資訊供其決定；不可擅自改既有事件。每次建立的 Calendar/Task/Note 都儲存 provider id 與 owner scope；操作過程發生部分失敗，保存成功與失敗項、提供重試，不得因 Calendar 成功就宣稱其他兩者成功。取消追蹤不等於刪除使用者自行修改或已完成的筆記／待辦；提議刪除需清楚呈現範圍並走既有 confirmation。
6. **主辦單位長期追蹤：** M1 schema 就保存 Organizer 的 canonical identity + source aliases，E1 才提供追蹤 UI 和其新活動通知，以因應主辦單位更換報名平台。

## 11. 安全、合規與可維運性（MVP 必做）

- **外部 URL 安全：** 網頁擷取器以 allowlist/可配置政策管控 host、scheme、redirect；擋 private/link-local/metadata IP（含 DNS 解析與重新導向）、限制大小/逾時/併發，避免 SSRF、無限 redirect、惡意檔案或抓取攻擊。
- **資料與 LLM 信任邊界：** 網頁、新聞稿、電子報與聚合摘要均為 untrusted input；不執行 embedded instructions；LLM 只能提出抽取候選，結構/時間/費用須以來源及 deterministic validation 確認；原文清洗與記錄最小化，不存多餘個資。
- **平台授權：** API 優先，逐來源審核使用條款、robots、更新週期、授權與來源標示義務；不能把公開可讀直接等同允許大量擷取或任意轉載。授權不確定者維持 disabled / NOT VERIFIED。
- **清理與隱私：** 活動過期候選立即撤出可選列表；預設結束後 30 天清理可刪的原始內容，保留最小去重 tombstone、必要 audit 及使用者既有個人資料。清理條件包含場次、報名窗口與個人追蹤關係；批次 production 不可逆刪除需另依高風險操作規則核准。
- **資源成本：** 使用 HTTP conditional request、來源 delta/etag、hash 去重、規則過濾；僅對低信心內容送 LLM，監控每有效活動的 HTTP/LLM/Cloud Run/DB 成本，避免每次都做整站全文擷取。

## 12. KPI / Acceptance Matrix（定義先於上線，門檻由觀測決定）

| KPI | 定義／避免誤判 | 驗收方式 |
| --- | --- | --- |
| 報名前發現率 | 在**正式報名窗口開始前**系統就已有來源可追溯事件／同場次機會的比例；沒有報名窗口的活動另列 | M0 14 天實測，M4 真實資料重測，按來源拆分 |
| 新鮮度與發現延遲 | 官方原始發布至首次觀察、抓取成功至入庫，分開計算；12 小時 polling ≠ 即時 | 來源抓取歷程與 UTC/Taipei 時間比對 |
| 免費資格誤判率 | 樣本中被標成免費但實際有必要費用/不符資格的比例 | 固定正反案例 + 抽樣回原始站核對 |
| 報名時間正確率 | 有精確時間者與官方公告一致的比例，未知不得納入錯誤「精準度」分母 | 精確時區、日期/時分與 DST 解析案例 |
| 重複投遞率 | 同一 user/event/session/opportunity/notification semantic key 的重複推送數 | 多來源、重試、併發、恢復與變更測試 |
| 過期可操作率 | 截止、取消、活動已結束但 UI/API 還可建立失效報名操作的比例 | UI + server-side API 競態/時鐘邊界 |
| 來源覆蓋與健康 | 授權可用來源中按期擷取、可核驗的比例；失效不等於沒有活動 | Admin-only 健康記錄/假來源與回復測試 |
| 使用者採納率 | 有效推薦候選中選擇追蹤的比例；與資料品質分開看 | 僅匯總必要行為資料，不推測心理意圖 |
| 單筆有效活動成本 | 掃描/抽取/LLM/儲存總成本除以有效非重複活動數 | 真實監測並分來源列出 |

**硬性不變量（應以自動測試驗證）**：非 admin 不得讀取/執行 admin API；未知精確時間不得憑空建立「準時提醒」；已截止/取消/額滿且無候補不能執行報名動作；同一通知 key 不重覆投遞；相同活動跨來源不可重複建個人物件；部分成功不可偽裝為全部成功；來源抓取失敗不得自動取消活動；個人筆記不能被來源資料清理級聯刪除。品質 KPI 的百分比目標需 M0 基線與成本測試後正式訂定，**不得捏造已達到門檻**。

## 13. 開發啟動條件與狀態

- 依 `doc/phase1_delivery_order.md`：Calendar #8 先通過適用的 implementation、tests、CI、deployment、runtime、real Google account、mobile/desktop UX gates，才啟動 Post-Calendar track 的正式產品實作。
- 在 M0 完成前，M1 migration 的 Registration Opportunity / Organizer / tombstone 設計先可評審但不應直接對 production DB 落地；缺值、授權或 admin identity 未確認時 fail closed。
- GitHub main 當前實作與 runtime evidence 高於本設計文件；本次只更新規格和 backlog，不新增 scheduler、不修改 DB、不發布部署。
- 進度狀態：**planning/documentation = PASS（須文件 readback）**；**M0–M4 implementation / tests / CI / deployment / runtime / integration = NOT VERIFIED**；整體 **PARTIAL / NOT IMPLEMENTED**。

## 14. Batch AI 模型路由與增量成本（2026-10-09 確認）

高價值來源每日 06:00/18:00 掃描，但**掃描不是必然推論**。ETag／Last-Modified／正規化內容 hash 與 PostgreSQL AI fingerprint 命中時呼叫 0 次；規則／官方結構化 API 可處理者也不使用 AI。新或有意義變動且規則無法可靠抽取者才使用 **Gemini `latest-3-flash` → Gemini `latest-3-flash-lite` → Groq → OpenRouter → 私有 Shared Codex** 的備援順序，逐項上限與工作預算另依 M0 實測收斂。

Flash 和 Lite 各自從官方可用清單選最多三個穩定文字模型，並**分別持久保存**最後成功型號，下一輪優先選仍可用的該型號；各系列候選缺額不以 preview/TTS 充數。Shared Codex 僅複雜例外/必要備援且遵守 owner 授權，無需將 CLI 或金鑰放入本專案。批次一次產生一份精簡 UI 卡片與公用摘要（60–120 中文字）、核心報名/免費/時間證據；不存整站 HTML／大圖／完整 prompt，不因使用者觀看或選擇筆記再呼叫 AI。明確日期/費用/權限與發送操作均由可稽核來源、後端規則及使用者決策確定，AI 只產候選建議。

M1 驗收：相同內容相同抽取規格的重試／併發只產一份有效 AI 工作；無內容異動／有完整官方結構化欄位／使用者打開清單或建立一般筆記時 AI 呼叫為 0；Lite/Flash last-known-good 互不污染；資料庫只留核心欄位、簡短摘要、來源與最低限度稽核/去重。M4 驗收：模型個別真實可用性、精度、provider 失敗後備援、p95 查詢速度、批次成本、過期清理、真實 GCP 06/18 任務均須取得證據。預算超標時延後非關鍵 AI 工作而不是停止所有活動探索。**本功能依然 NOT IMPLEMENTED**。
