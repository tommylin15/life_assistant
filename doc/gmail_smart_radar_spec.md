# Gmail 智慧事項雷達 — 週期掃描與個人「快掃」設計

更新：2026-10-16（Asia/Taipei）
狀態：**使用者產品需求已提出；設計／工作契約，非已上線功能。** Implementation / tests / CI / staging / production / real-account E2E = **NOT VERIFIED**。
Source of truth：現行 GitHub main 與實際 runtime；本文件提供實作驗收契約，不能取代證據。

## 目的及與現有功能的關係

Life 不重做 Gmail 郵件客戶端。定期或按需檢查**逐人明確授權且啟用**的 Gmail，辨識有行動價值的資訊，寫入個人「Gmail 智慧事項」清單，依使用者通知設定提示；完整信件仍在 Gmail，Life 僅顯示適量摘要與「開啟 Gmail」。
與現有 Life Inbox 快速新增（使用者主動輸入文字）分開入口但共用必要的分類／確認原則，不另創 Task／Calendar 資料表。
現有 `backend/app/api/google_integrations.py` 只有最近郵件 metadata/snippet 清單及使用者手動 Gmail→Task/Calendar，`backend/app/services/google_oauth.py` 提供 Gmail readonly scope 與 refresh token；**尚無**可聲稱通過驗收的智慧雷達、單人快掃端點、增量游標、常駐郵件通知排程。新設計不應把既有手動轉換當成已完成的快掃。

## 核心 UX

- Life 導覽：`Gmail 智慧事項雷達`；頁面標題右側有明顯 **「快掃」** 按鈕（手機可單指操作）。
- 頁首顯示「每小時掃描（啟用／停用）」、「上次成功掃描時間」、「目前掃描進度／錯誤或重新授權提示」；時間以實際完成紀錄顯示，不用預估冒充實績。
- **快掃**：按下立即對「目前登入的 Life 使用者所綁定的 Gmail」提交一次單人掃描，不觸發其它使用者、也不觸發全員 hourly scan。按鈕在同帳號執行中不可再次啟動，顯示原 job 狀態（queued/running/completed/partial/failed）。
- 每次完成更新結果摘要：`檢查郵件數 / 新增事項數 / 已存在略過數 / 需要人工確認數 / 失敗數`；只顯示真實統計。
- 個人事項卡：重要性、分類、可信日期（不確定時待確認）、最短必要說明、來源寄件者與郵件時間、處理狀態，以及 **「開啟 Gmail 原信」**。可選忽略、已處理、建立 Task/Calendar（使用者明確確認）。
- **不複製完整 Gmail UI**：不做 Gmail 收信、寄送、回覆、封存、標籤或郵件刪除；不長期保存原始郵件／附件。

## 後端與執行契約

1. 保持 Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL。
2. 兩種觸發共用**同一個 scanner domain service**：
   - Cloud Scheduler 每小時啟動一次安全的 batch job，僅處理 enabled 且有效授權的個人。
   - `POST /integrations/google/gmail/radar/quick-scan`（建議 API contract）使用現有 `current_user` 授權，**無** user_sub、email 或 target_user_id 的可傳入參數。僅操作綁定至本人的 Gmail；回應 `202 Accepted` 加不含私人內容的 `scan_id`，非同步工作完成由 `GET /integrations/google/gmail/radar/scans/{scan_id}`（建議）查狀態。
   - API 必須先在 DB 持久保存 job reservation／per-user lock，再交由可靠執行載體（現有 GCP Jobs／有驗證的 Cloud Tasks 等）處理，不依賴請求返回後可能遭 Cloud Run 結束的記憶體 background task。不得為一人快掃啟動全員排程。
   - 每位使用者跨手動與定期來源**最多一個同時執行**；重複點擊／同時 hourly 觸發回傳既有 job ID，完成後保留摘要與實際時間；使用者重新整理仍可取得進度。
3. 使用 Gmail API 增量游標 `historyId`，儲存 user_sub / cursor / last_success / scan source / scan status；第一次啟用採保守有限時間窗與數量上限（建議最近 7 天、最多 100 封，可逐步分頁）。手動和自動共用游標及同一套 dedupe；只在**所有已取得頁面完成持久處理後**推進游標。
4. `history.list` 游標過期（Gmail 可能回 404）時，執行**有界限補掃**並記錄 partial，不得默默跳過信件或宣稱全信箱掃描成功。正確處理分頁、quota、429/5xx、逾時、OAuth 失效和重試。
5. 初篩採 deterministic 規則；真正需要語意判讀的候選才呼叫既有 Life → omniAgent Gateway → Gemini，遵守使用者**單獨的郵件內容 AI 同意**、成本控制、超時與降級。AI 不可猜測金額/日期；有證據才提供，否則標「待確認」。原信的信件內容不可寫入 log 或永久留存。
6. 每位 user 保留最小必要資料：事項標題／短摘要／分類／重要性／可能的 date、Gmail message ID／thread ID、已處理狀態、掃描時間、來源與模型／規則 provenance。以 `user_sub + message_id + semantic_action_key` 或等價穩定鍵做 unique/idempotency；同項內容沒有實質改變，不重建立、不重通知。
7. 通知與掃描分離：只在新增且符合個人通知設定的高重要性事項通知，先保存 notification intent／dedupe key；失敗重試不得推送第二次。快掃也遵守通知設定，不另建重複通知服務；低重要性只更新清單。
8. `開啟 Gmail` 使用 Gmail HTTPS 原信／會話導向，不將全文在 Life 展開。**Gmail API messageId/threadId 並不等同於可保證跨瀏覽器、多 Gmail 帳號與原生 App 均直達的穩定網址**；要用真實雙帳號與 Android/Web 驗證來源連結；不能保證深連結時採可明確辨識帳號的 Gmail 搜尋／信箱入口，絕不顯示錯誤帳號的郵件。
9. 任何要求掃描他人信箱、未授權、AI 同意關閉、取消連結、登入逾期均依最小權限拒絕或優雅降級。原始 Gmail 正文不進 user-visible execution log；admin 不得閱讀個人郵件或事項內容。

## 驗收清單（不得以 UI 存在當作已完成）

- 授權：使用者 A 按快掃只產生 A 的掃描，無法以竄改 request / scan_id 取得 B 的信件或結果；未授權給出可操作的重連提示。
- 排程：每小時只選 enabled 且 Gmail scope 合法的帳號；停用後不繼續讀取，取消 AI 同意不發送正文。
- 共用引擎：同封郵件經 hourly → quick scan → retry，事項只新增一次、推播只發一次；同時提交只保留一筆 active scan。
- UI：按鈕有 queued/running/complete/partial/failed 及真實統計；中斷網路、重新整理頁面仍能讀取執行結果；掃描失敗不顯示「完成」。
- 連結：Android Gmail App/瀏覽器、Web、多登入帳號的原信跳轉逐一 E2E；不可直達時有安全 fallback。
- 完成條件：implementation、tests、四項 CI、staging、production 與真實登入 Gmail 整合視任務需求各別 PASS/FAIL/NOT VERIFIED；沒有實證只能 PARTIAL。

## 外部規格依據

- Gmail history.list: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list
- Gmail sync: https://developers.google.com/workspace/gmail/api/guides/sync
- Gmail OAuth scopes: https://developers.google.com/workspace/gmail/api/auth/scopes

限制：目前 `gmail.readonly` 是 restricted scope；對外公開使用及 Gmail 資料的伺服器保存／傳輸可能涉及 Google OAuth 驗證與安全評估，正式產品化前應核查，不宣稱已獲核准。
