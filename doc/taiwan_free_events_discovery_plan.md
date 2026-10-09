# 台灣免費活動探索與報名追蹤 — 正式產品／工程規劃

> 更新：2026-10-09 · **APPROVED PLAN / M0 PARTIAL（來源清冊／離線品質工具 CI PASS，14 天真實觀測 NOT VERIFIED；M1–M4 NOT IMPLEMENTED）** · **Calendar #8 DONE 後第一優先（Post-Calendar P0）**
>
> 執行順序只以 [`phase1_delivery_order.md`](phase1_delivery_order.md) 為準；AI routing 只以 [`ai_provider_policy.md`](ai_provider_policy.md) 為準。文件核准≠程式、資料庫、排程或正式部署已完成。

## 1. 定位與成功標準

此功能不是再做一個活動資訊聚合網站，而是讓使用者在報名之前，快速找到**可信、適合自己、仍可參加**的台灣免費活動，並且只在本人決定時建立提醒、待辦、行事曆或筆記。

使用者流程：**查看有效活動卡片 → 看清報名起始／場次／資格與費用 → 自行選擇追蹤、提醒、待辦、筆記與資料夾 → 需要完整資訊時前往主辦／報名原站**。掃描、分類與短摘要都在背景完成；使用者打開清單不必等待 AI。

成功以**報名前發現率、精確報名資訊、有效活動率、重複通知率、資訊品質、單筆有效活動成本**衡量，而不是單純收錄頁數。**每 12 小時一次 ≠ 即時**，短期滿額的活動可能來不及發現，不得保證零延遲。

## 2. 範圍、階段與原計畫關係

依使用者指定：先完整完成 Calendar #8 的真實帳號、API/UI、CI、deployment、runtime、mobile/desktop 驗收；活動探索為其後**第一優先**。原有 #9–#11 工作不刪除，原 11-package 完成比例不任意更改；本新工作是否納入 Phase 1 release blocker，於啟動時依 scope-freeze 與 release gate 明確決定。

| 階段 | 交付成果 | 完成 Gate |
| --- | --- | --- |
| **M0 來源與品質基線（MVP）** | 盤點來源存取授權；14 天真實新鮮度觀察；代表性免費／非免費／不同場次測試集；訂出成本/準確率門檻 | 每來源可追溯、來源健康與授權表、測量報表、資料模型評審 |
| **M1 增量擷取與資料核心（MVP）** | 官方 Feed/網站 adapters、Source Registry、Event／Session／Registration Opportunity／Organizer、PostgreSQL 幂等去重、結構化欄位、批次 AI 與清理 | migration／回退、來源失效隔離、重試、快取／並發、0-AI 不變量、資料品質安全測試 |
| **M2 Flutter 活動列表與 Admin（MVP）** | 精簡卡片＋簡要詳情＋原站連結、有效篩選／空狀態、待公告追蹤、現有 UI 內 Admin 來源健康 | mobile/desktop、圖片缺失、來源下架、非 admin 401/403、真實 auth |
| **M3 個人化操作（MVP）** | 使用者分開選提醒／待辦／筆記、筆記資料夾、手動已報名／候補狀態、行事曆衝突提示、個人追蹤和取消 | 真實 Calendar/Task/Note provider；取消/部分成功/幂等/跨來源重複/提醒變更與 owner isolation |
| **M4 GCP 正式排程（MVP）** | Cloud Scheduler 每日 06:00/18:00、受認證 Cloud Run Batch、PostgreSQL durable jobs、監控/恢復/成本；正式切換後停用過渡 ChatGPT 掃描 | 真實排程、Batch 故障重試/補抓、正式 UI/API/AI provider／回滾與流量、重複通知防護、成本證據 |
| **E1 第一版增強** | 追蹤主辦者、進階興趣/地點偏好、摘要與靜音通知、更細緻報名/候補 UX | 偏好/權限/訂閱/取消/變更通知驗收 |
| **E2 第二階段** | 使用者貼連結擷取、交通時間/距離、合法電子報來源、進階推薦/自然語言探索 | 授權、安全、推薦品質與成本效益 |

**暫時不做：** 自動報名／付款、自建完整票務網站、隨機爬受保護 API、繞過反爬、常駐 VM、新獨立 Admin 後台、大型推薦模型、不必要的向量資料庫。

## 3. 擷取來源、掃描排程

| 類別 | 範例 | 週期 | 權限與用途 |
| --- | --- | --- | --- |
| L1 官方第一線 | 主辦官網、公告/新聞稿、RSS、原始報名頁 | **每 12 小時：06:00、18:00 Asia/Taipei** | 以正式公告與報名頁為事實依據 |
| L1 聚合補漏 | EventGo、小藝行事曆、Citytalk、ACCUPASS、KKTIX | **每 12 小時**，合法可用後才啟用 | 找候選與連回原站；不能無授權複製整站 |
| L2 官方結構化 | 文化部藝文、觀光/TDX、各縣市活動資料 | **每日一次** | 補漏與交叉核對，不冒充即時 |
| L3 來源探索 | data.gov.tw 資料集目錄與異動 | **每日一次** | 發現可用資料來源，不直接當即時活動列表 |
| 重要已追蹤活動 | 官方報名頁與狀態頁 | 一般每日；已知即將開放時可配置短期提高查詢密度 | 只對該活動且不突破來源速率限制 |
| 清理與健康 | expired sessions、來源 adapter 健康、重試佇列 | 每日一次 | 不因來源暫時斷線就刪活動 |

**2026-10-09 新來源決策：BeClass（beclass.com）完全不採用，包含透過 EventGo 間接發現但原始連結導向 BeClass 的候選。** EventGo 僅先建立隔離 Crawl4AI Python 連結器，見 [eventgo_crawl4ai_connector.md](eventgo_crawl4ai_connector.md)。EventGo ToS 禁止自動化工具大量存取；其來源權限／robots 尚未獲核實，M0 registry 保持 enabled_for_fetch=false，正式自動抓取／DB/排程整合禁止先行啟動，直到有書面授權與存取審核。這是獨立開發 checkpoint，不代表現場觀測 PASS。

**現有 ChatGPT 定期掃描只屬過渡來源探索，未與 app 的正式 PostgreSQL durable tasks 等同。** GCP 排程與兩邊去重/切換獲真實 PASS 後才關閉過渡掃描。

Source Registry 最少記錄：來源 ID、官方/聚合等級、URL/API 類型、adapter/schema 版本、允許的存取方法與法律審核結果、期望頻率、最近檢查/成功/內容變更、錯誤分類、退避、enabled/health、可觀測延遲。來源錯誤不可解釋成活動取消。

候選 GitHub 元件：`feedparser`／`trafilatura` 先評估實際版本/依賴/授權；`changedetection.io`、`RSSHub`、`Huginn` 只列候選，不因存在就部署。**AGPL / robots / Terms 要逐來源確認**。

## 4. 資料模型：最少必要欄位，不複製原站

**公用資料共用一份；個人選擇另存，不為每位使用者複製活動全文。**

| 資料 | PostgreSQL 最小必要內容 | 不要長期存 |
| --- | --- | --- |
| **Organizer** | 主辦單位 canonical identity／別名、可信來源 | 完整組織介紹與人員履歷 |
| **Event** | ID、名稱、分類/標籤、主辦、短摘要、來源/官方 URL、狀態、內容 fingerprint | 整份 HTML、長篇新聞稿、講師介紹、完整 prompt |
| **Session** | 一場活動下各場次日期/時間、縣市、場地／線上、時區、有效性 | 冗長流程、全站描述 |
| **Registration Opportunity** | 每場次/票種各自的開放／截止時間、免費/條件免費、必要費用/資格、名額或候補狀態、報名 URL | 完整報名表與參加者名單 |
| **Source / Evidence** | 來源 ID/URL、可核對關鍵文字片段或欄位值、取得／查證時間、hash、解析版本、重大變更紀錄 | 每輪原始回應、無限增長的完整快照 |
| **User decision / action links** | user/sub、追蹤意願、所選提醒／待辦／筆記、provider item ID、投遞去重 key、必要的取消/重試狀態 | 不相關的個人資料與公用資訊副本 |
| **UI presentation** | **60–120 中文字**短摘要、2–3 個主題標籤、最重要注意事項、**縮圖 URL（合法且可用時）** | 活動圖片原始檔、推論的假圖片、完整精裝介紹 |
| **AI operational metadata** | 標準化內容 hash、抽取 schema/模型策略 fingerprint、狀態、最後 AI 時間／必要 trace | 完整輸入、LLM 全文回應及無限的 provider retry log |

精確報名時間未知就留 null／待公告，不猜「09:00」。`registration_start_at` 和 `registration_end_at` 與報名票種/場次綁定；只知道日期時不可轉成精確提醒。免費/條件免費/非免費/待確認要保留判斷依據（押金、材料費、會員、戶籍、入場門票等）。

原站已刪除時，保持最少已核對資訊與當時查證時間，但**立刻降低可操作信任等級**；需要再次查證才能聲稱現在仍可報名。短摘要不可優先於官方欄位或原文證據。

## 5. 活動生命週期、去重與資格

- 報名機會：`unannounced` → `upcoming` → `open` → `full / waitlist_available / closed`；任何階段可因官方證據轉 `cancelled`；活動結束時 `event_ended`。額滿不代表沒有候補；沒有正式報名流程的活動可只追蹤活動日期。
- 系統狀態要區分 `verified`／`unverified`／`stale`／`invalid`。只由聚合站發現或 AI 猜測的項目，不得宣稱「已核實可報名」。
- 去重先用 `source + external_id`、canonical URL、官方 ID，其次場次/主辦/日期/地點；需要時才用語意模型評估疑似重複，**不可自動把不同場次合併**。
- 相同 user/event/session/opportunity/notification semantic version 只能投遞一次；延期、報名時間更動或取消才產生新語意版本，普通文案更正靜默更新。
- 使用者的 `interested`／`registration_pending`／`registered_by_user`／`waitlisted_by_user`／`cancelled_by_user` 必須與官方報名狀態分開。不能因點了連結就宣稱「已報名」。

## 6. 增量擷取與最小 AI 使用量（硬性政策）

**12 小時掃描不等於 12 小時跑 AI。沒有有意義的變更就應是 AI 0 次。**

1. **網路/來源 L0**：優先 API delta、`ETag`、`Last-Modified`、來源唯一 ID；來源內容變動先抽取活動相關區段、去掉廣告/動態時間再做正規化 hash，但費用/時間/取消等關鍵欄位必須獨立比對。
2. **規則/資料庫 L0**：已結構化官方資料、日期/有效期、報名狀態、canonical 去重、清理和提醒計算，直接經後端處理；不呼叫 AI。
3. **AI 條件觸發**：有新的有價值活動或**實際影響欄位**的變化，且 deterministic extraction 無法可靠處理，才建立 Batch AI 任務；**同內容 fingerprint + schema 版本 + AI routing policy 對應的結果重用**。
4. **Durable claim/lease/重試**：同一工作 key 即使 Cloud Run 重啟、兩輪掃描重疊或相同活動被不同來源找到，最多僅一個有效分析者；冷卻、超時回收與重試上限，不每 12 小時反覆重做同一失敗。
5. **批次預產出**：共用 60–120 字卡片摘要與結構化欄位；用戶看卡片、選筆記資料夾或設定提醒不觸發模型。
6. **成本保護**：按來源、模型、有效事件計量及每日預算設 hard limit；超額先延後非關鍵候選，不阻塞已驗證活動瀏覽或關鍵取消通知。

Provider fallback 的正式序列與 Flash/Lite 各最多三個、最後成功優先規則由 [`ai_provider_policy.md`](ai_provider_policy.md) 統一定義；**並不表示 Batch 每次都呼叫 Gemini、Groq、OpenRouter、Shared Codex**。既有 Drive AI 的 consent/cache/partial/error contract 可借用工程模式，活動另有自己的 `EventAIEnrichmentService` schema/資料模型；不得把 Drive-specific 的標籤/相關筆記 schema 原封不動套用。

Shared Codex 是已存在的私有服務而不是 life_assistant 本機 CLI；僅有 project-scoped authenticated owner／caller permission 時才可用，公開 Batch 不可自行虛造 owner。Adapter 故障的複雜診斷可由 Admin 使用 Codex 協助**提出建議**，不能從網站文字直接修改程式或自動部署。網頁不可信資料不得控制模型工具／動作。

## 7. Flutter UX：資料少但卡片仍完整

- **列表卡片**：標題、活動類別圖示/標籤、60–120 字摘要、日期時間、城市/場地、免費或附帶成本、報名開放時間／狀態；重要注意事項最多一項、最後核對時間與原站 link。
- **詳細畫面**：同資料的易讀排版、場次/資格／額外費用、來源驗證說明、原始活動官網與「前往報名」兩個合法連結；不直接轉載原始整篇內容。
- **圖片策略**：只用來源允許且技術可用的縮圖 URL，使用 link validity / fallback；無圖片改用內建主題圖示／配色，**不為了美觀生成不存在的官方照片**，也不儲存圖片二進位。
- **空/例外狀態**：摘要缺失、來源失效、沒有報名時分、候補、活動延期、沒有興趣匹配，均需有完整呈現。缺摘要可用結構化欄位組出簡短模板，避免卡片空洞，不能假造描述。
- **操作**：通知、待辦、筆記分別 opt-in；筆記資料夾由使用者選擇。追蹤「報名時間待公布」和真正建立精確報名提醒要分開。Calendar 行程衝突先提示，不擅自覆寫；個人「已報名」只由使用者或未來經授權的正式平台事件確認。
- **User 端不展示模型名稱、prompt 或模型預測 confidence**；Admin 才看來源健康、抽取失敗、審核/回查證據與模型用量。

## 8. GCP 架構與權限

正式目標：**Cloud Scheduler（Asia/Taipei 06:00/18:00）→ authenticated Cloud Run Batch/既有 FastAPI 適當端點 → PostgreSQL operational tables → Flutter Web / PWA**。以實際部署架構和 GitHub V3 release policy 為準，不為此功能預設 VM/額外常駐服務；Jobs 與原 API 如何復用須經 M1/M4 成本/併發測試決定。

Admin 採現有 Flutter UI／FastAPI API、**後端 verified UID allowlist/RBAC**。過往文件中收到 `tommylin15@gmai.com` 字串有疑似拼寫問題；**核實使用者登入 identity 前不能授權**，不能只隱藏前端管理按鈕。

所有外部頁面經 Adapter 限制來源、解析、HTTP 超時/回應大小、DNS/rebind、redirect、private/link-local/metadata IP 防 SSRF；站外資料包括 prompt 注入都當 untrusted。存取 robots / ToS / RSS/API 條件需逐來源確認，長文/個資不持久保存；私人資料送第三方 AI 需明確同意。

任何新增用戶筆記/任務/Calendar event 必須走既有 Backend validation 與 idempotent execution log；發生部分成功分別顯示並保留成功者 provider IDs，不能假裝三個動作都成功。取消追蹤/過期不擅自刪使用者手動修改的資料。

## 9. 過期與保留（精簡 DB）

1. 報名截止、取消、額滿且無候補，立即從可執行報名清單撤出；活動結束退出一般候選頁。
2. **建議但未最終驗收的保留提案**：活動結束約 30 天後清理非必要原始片段、短期快取/擷取內文，只保留最小去重 tombstone、必要稽核及合法保留資料；原始大 HTML/完整回應正常流程中不應長期入庫。
3. 已由使用者建立的 Calendar、Notes、Tasks 與對應外部 provider IDs 依個人物件本身的生命週期保留，不受公用來源內容清理連帶刪除。
4. 任何 production 大量或不可逆刪除需另經高風險操作明確確認，不能把規劃視為已獲准執行清理。

## 10. 指標與驗收矩陣

| KPI / 硬性不變量 | M0/M1/M4 驗收方法 |
| --- | --- |
| 報名前發現率、來源發布→首次發現延遲 | 至少 14 天來源樣本、活動/報名窗口分母與時區清楚 |
| 免費／資格錯判率、報名時間正確率 | 官方來源/報名頁正反 fixture；未知不是已確認 |
| 過期仍可操作／重複來源／重複通知 | Session/Opportunity/semantic notification key、併發重試與 UI/API 邊界案例 |
| **來源未變／結構化資料／用戶瀏覽時 AI 呼叫 = 0** | instrumented test，覆蓋兩輪 12 小時批次、快取／部分故障 |
| **同一 fingerprint/schema 一次有效 AI 工作** | PostgreSQL concurrency/lease/idempotency／失敗退避與回收測試 |
| Gemini Flash 與 Flash-Lite sticky last-success 獨立 | 兩組最多三模型、各自 preferences、無效型號、429、模型清單故障與 fallback 測試 |
| AI 容量、模型花費、單筆有效活動成本 | 按來源/模型/日期記錄 token 用量和實際費用（資料不足列 NOT VERIFIED） |
| Flutter 空卡／斷圖／原站掛掉 | desktop/mobile UI 回歸及無圖片 fallback 視覺測試 |
| 身分、私人資料/AI consent、外部 URL 安全 | 非 admin 401/403、owner isolation、SSRF、含 prompt injection 網頁輸入 |
| deployment／runtime／provider live | exact SHA CI → V3 release candidate/live/rollback → GCP Scheduler/Job 真實觸發及 provider direct-health 各別證據 |
| 過期資料清理而不傷個人物件 | retention dry-run、外鍵/個人資料保留、重試/復原測試 |

所有百分比/費用目標由 M0 量測與基線決定，**不捏造實際數值**。需要 implementation、tests、CI、deployment、runtime、integration、UI/permission 全部相關 gate PASS 才能宣稱此功能 DONE；任何缺漏維持 PARTIAL。

## 11. 目前狀態與限制

- **規劃/文件：** APPROVED PLAN（完成 readback 才算本次文件修改 PASS）。
- **既有通用 AI Provider 路由：** GitHub `main` 已有程式；2026-10-09 CI 有 PASS；部署與真實 Flash/Lite/Groq/OpenRouter/Shared Codex 多模型 E2E **NOT VERIFIED**。
- **活動專用掃描、Event/Session/Opportunity PostgreSQL tables、Flutter 活動 UI、Admin 健康、GCP 06/18 排程：** **NOT IMPLEMENTED / NOT VERIFIED**。
- **ChatGPT 定時掃描：** 僅過渡，與正式產品來源入庫和用戶操作無關；真實 GCP 切換 PASS 後再停用。
- **M0–M4 / E1–E2 進度：** M0 與 M1 低風險研發並行；M1 六表 migration 0011、資料契約、離線 JSONL 清洗/去重及文化部資料 Adapter 已 commit 至 main，資料庫 migration 尚未正式執行且 live ingestion **NOT VERIFIED**（詳見 `free_events_m1_checkpoint.md`）。M0 已啟動：`data/free_events_m0_sources.json`、`scripts/free_events_m0_baseline.py`、`backend/tests/test_free_events_m0_baseline.py`（8 tests）已在 commit `ea8264562e3f260bb56f52500d3d917104e86a69` 實作並通過 [CI #37892185617](https://github.com/tommylin15/life_assistant/actions/runs/37892185617)；但**尚無 14 天真實觀測、逐站 service 授權審核，M0 整體 PARTIAL / NOT VERIFIED**。M1–M4 及 E1–E2 尚未實作；不能因文件或測試 PASS 封板。

**相關文件：** [`ai_provider_policy.md`](ai_provider_policy.md)、[`phase1_delivery_order.md`](phase1_delivery_order.md)、[`decisions.md`](decisions.md)、[`acceptance.md`](acceptance.md)、[`PROJECT_RULES.md`](PROJECT_RULES.md)。
