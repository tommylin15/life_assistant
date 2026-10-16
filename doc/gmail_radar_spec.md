# Gmail 智慧事項雷達｜產品與工程契約 V1

- 日期：2026-10-16（Asia/Taipei）
- 狀態：**APPROVED REQUIREMENT / IMPLEMENTATION NOT VERIFIED**。本文為本輪明確產品需求，不是已實作、CI 或上線證據。
- 目標：每小時增量檢查**已授權且啟用自動掃描**的使用者 Gmail，辨識有行動價值的生活事項，回寫 Life 的「Gmail 智慧事項」清單並通知。**不把整個 Gmail 信箱複製進 Life，也不開發郵件用戶端。**
- 優先閱讀：`doc/PROJECT_RULES.md`、`doc/permissions.md`、`doc/security.md`、`doc/todo.md`；實作現況由當前 `main` 與 runtime evidence 決定。

## 1. 介面：每個使用者都有「立即快掃」

在 Life 導覽「Gmail 智慧事項雷達」畫面，頁首顯示 Gmail 連線／授權狀態、**上次掃描時間**、**自動掃描開關**，右上角設置明顯的 **「立即快掃」** 按鈕。

按鈕規範：
1. 使用者按下後立即開始**單人** Gmail 掃描。後端從目前登入 Session 驗證 `current_user.sub`，**不可接受 UI 指定 `user_sub`、email 或批次帳號集合**。
2. 不受「每小時整點」排程等待限制；即使此使用者停用自動排程，也能在 Gmail 授權及必要分析同意有效時手動快掃。停用任何服務授權不得被快掃繞過。
3. 快掃與每小時掃描使用**相同 pipeline／去重與結果格式**；區別只在 trigger_type=`manual`／`hourly`。
4. 點擊後按鈕顯示「掃描中」且不能重複觸發；HTTP 層必須有**同使用者單一進行中掃描鎖**，含跨裝置、同時定時／手動情況，不僅靠前端 disabled。
5. 長任務非同步執行：API 立即回覆 `scan_id` 與 `queued | running`，前端透過狀態讀取更新；**不要依賴 Cloud Run API Request 內的無保證 BackgroundTasks**。排隊／執行失敗明確可見並可重試。
6. 完成後清單更新、顯示「本次檢查 N 封／新增 M 筆事項／略過 K 筆／錯誤 E 筆」和掃描時間；**無新事項也是正常成功**。部分失敗不得顯示全數成功。
7. 快掃只影響**當前登入者**的掃描任務、游標、事項、通知設定與結果；其他使用者的資料、游標、作業及排程完全不變。
8. 與定時掃描相撞時，應回傳既有該使用者 `scan_id` 及執行進度（不產生另一份工作）；跨使用者不互相鎖死。

UI 清單範例：`需處理／待確認／已完成／已忽略`，每張卡顯示**有來源證據的**簡短摘要、分類、優先程度、期限（可空）、掃描來源、來源 Gmail 連結；操作 `開啟 Gmail`、`加入待辦`、`加入日曆`、`完成`、`忽略`。**只有使用者主動確認才能寫入待辦／日曆**，而且沿用既有 Task／Calendar 實作，不另建影子待辦。

## 2. 自動掃描／單人快掃共用流程

1. 前提：本人有效 Google OAuth、Gmail readonly 授權；自動排程需額外 user opt-in，自動內容送 Gemini 則需**個人明確 AI consent**（預設 OFF）。
2. 增量：記錄**每位使用者獨立的 Gmail historyId／最後成功游標**，優先 `users.history.list`，失效 404 則**有上限地回補**近期候選郵件，不能無限制全信箱重掃。初次啟用限定近期窗口（建議 7 天，後續可配置），分頁與每輪掃描上限需記錄。
3. Python 先排除顯然無關的廣告、垃圾郵件、系統例行信，並以 metadata/subject/snippet 規則分類；對候選者，**僅在本人允許且所需資訊不足時**讀取必要正文送 Gemini 分析，輸出經 schema 驗證的分類、行動需求、摘要、信心、期限及來源依據。不能編造日期／金額／姓名。
4. 儲存最小結構化資訊於 PostgreSQL：`user_sub`, `gmail_message_id`, `gmail_thread_id`, `item_type`, `title/short_summary`, `deadline?`, `priority`, `state`, `first_seen_at`, `updated_at`, `scan_id`, `source_evidence` (最小必要值)。**不持久化整封原信、附件或 Gmail access token**。
5. 去重與狀態：唯一鍵建議 `(user_sub, gmail_message_id, item_type, logical_item_key)`，必要時同一郵件可有兩個真實不同事項；重掃只更新允許更新的欄位，不重建已忽略／已完成／已建立 Task 的事項。
6. 通知：只有**首次新增且達使用者通知門檻**的事項才建立通知 outbox；手動／自動掃描共用通知去重鍵。通知送達方式（Life 站內、Web Push 等）需驗證使用者已授權與目前通知 infra，不假設瀏覽器關閉後一定能推播。
7. 來源連結：儲存 Gmail thread/message ID，從已授權使用者情境導向 Gmail 原始郵件；**不得假設所有裝置／多帳號都能以單一 URL 開啟正確信件**，要測試 Gmail Web、Android/iOS App、同裝置多 Google 帳號的行為及 fallback Gmail 搜尋／清單。

## 3. API 與工作派送建議（實作前須對照當前路由／schema）

- `POST /integrations/google/gmail/radar/quick-scan`：需 Login／Gmail 授權；無可指定的 user ID；202 回傳 `{ scan_id, status }`，已執行則回同使用者進行中掃描。
- `GET /integrations/google/gmail/radar/scans/{scan_id}`：僅該掃描 owner 可讀進度與有限計數。
- `GET /integrations/google/gmail/radar/items`：僅當前使用者資料；分頁、狀態篩選。
- `PATCH /integrations/google/gmail/radar/items/{id}`：本人確認／忽略／完成；操作稽核與防重送。
- 每小時單一 GCP Scheduler 只負責 dispatch 已 opt-in user 的掃描，不對未授權使用者掃描，不用 Gemini 判斷是否啟動 Job；執行可用 Cloud Tasks/Run Jobs 或經驗證的耐久佇列／worker，共用 per-user lease 與掃描服務。

重要：先檢查目前 CI/GCP 的雲端排程與通知模組是否有可重用的通道，**不新增第二套 Scheduler／Notification 或相同事項表**。上列 API 為建議契約，非現行已存在端點。

## 4. 例外與風險

- 401/403、Google grant revoked、refresh token invalid：立即停止讀取該帳號、標「需重新連線」，保留已建立的 Life 事項供使用者管理，不以行政身分繞過。
- Gmail／Gemini 429、5xx、timeout：有限重試、退避、掃描 PARTIAL；僅在已完成可靠資料處理後提交游標，避免漏掉事項。
- Google OAuth `gmail.readonly` 為受限範圍；目前 backend 具該 scope 及加密 refresh token 能力，但**不是公開 Google OAuth 驗證／安全評估通過證據**。內容分析 consent 分開管理，撤回後不可繼續送模型。
- 批次數量、Gemini 呼叫額度、通知出站成本、資料保留天數可配置，缺數值時不憑空造價。
- 既有 `GET /integrations/google/gmail/messages` 是最近 30 天 metadata/snipppets 查詢；手動 `gmail/messages/{id}/task|calendar` 也已存在。**Gmail 雷達資料表、掃描排程、單人快掃 UI/API 目前都不應視為已存在。**

## 5. 完成驗收標準

- 實作：Flutter「立即快掃」觸發真實受保護 API；可查掃描狀態；成功／無新件／部分失敗／需重新授權的 UI 都正確。
- 安全：A 登入只能掃 A；篡改 scan_id/item_id 不可讀 B；API 不接受別人的 user_sub；撤權／opt-out 對應防線；未同意 AI = 零正文送模型。
- 同步：手動+手動、手動+排程、相同郵件重送、掃描中斷續跑；事項與通知 exactly-once-effect／可重送；historyId 404 有界回補。
- 系統：Python tests、Flutter widget tests、Migration 測試、GitHub 4 CI、固定 staging、Cloud Run Job/Queue 真實執行、PostgreSQL 讀回、Gmail 真實受授權帳號、通知實際展示及原信開啟。
- 用 `PASS / FAIL / NOT VERIFIED` 分層回報 implementation/tests/CI/deployment/runtime/integration；**沒有 UI + API + 真實單人 Gmail 測通之前不能標 DONE。**
