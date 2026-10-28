# Life × LINE 方案 B｜正式規格 V1

日期：2026-10-28（Asia/Taipei）
狀態：開發候選；真人驗收由 Owner 執行。文件、原始碼及自動測試不等於 LINE 已啟用。

## 1. 決策與工程基線

Owner 已選 B「聊天快速記錄＋LINE 內管理頁面」，並明確指定以本對話原版優先。原版已於 `/workspace/scratch/ce8451bfc5e6/life-line` 找回；其前進整合使用 `backend/app/api/line.py`、`models/line.py`、`services/line_channel.py` 與 `web/line/`。

- [原版復原證據](line_recovery_audit_20261028.md)：保存精確來源 hash、原始 patch 及 153 項本地測試重跑收據，其中 LINE 15 項。153 是本地已取得的相關測試集合，不是全倉庫完整 CI 數量。
- 後次 `line_bridge.py` 與 `web/line.html` 的替代流程不再作為產品基線。舊 API 模組不註冊；舊頁僅導向原版入口。保留既有 0023 migration／model／資料表，不做 downgrade 或抹除資料。
- 本版採新 migration **20261028_0024 → 20261028_0023**。可從 0022 依序前進，不假設 0023 是否已在真實 DB 套用。既有舊版綁定／草稿不自動轉成新授權；舊資料保留，新版要求重新綁定。
- 所有非 LINE 的 main 變更（來源路由、活動匯入等）保留。

## 2. 本版交付範圍

| 能力 | 本版行為 | 邊界 |
|---|---|---|
| 帳號綁定 | Google 登入 Life → 產生碼 → 本人 LINE 傳送 → Life 核對尾碼並確認 | 一個 namespace 內 LINE 與 Life 帳號一對一；不覆蓋其他綁定 |
| 文字／網址快記 | 私聊文字 1–1200 字先持久化為草稿，回覆 LIFF 入口 | 尚未確認不建立正式事項；不自動下載網址 |
| 草稿分類 | 沿用 Life Inbox 規則／omniAgent Gateway，拆成筆記、待辦、購物、行程 | AI 只提出候選；使用者確認欄位與目的地 |
| 正式新增 | 每項明確確認，沿用 Inbox validation／receipt／idempotency | UNKNOWN 先核對回執，不能自動重新建立 |
| 個人查詢 | 筆記內容、未完成待辦、未買購物品項；20 筆分頁 | V1 為關鍵字查詢，不宣稱完整自由語意或跨來源推理 |
| 聊天查詢 | `查 筆記 水電`、`查 待辦 繳費`、`查 購物 牛奶`、`待辦`、`購物` | 回覆前五筆標題及時間，詳細原文在頁面看 |
| 問句防誤存 | 無法確定的常見問句引導搜尋，不當作新增指令執行 | 未支援任意自然語言查詢規劃 |
| 待辦 | 查看、完成、修改標題與截止時間 | 新增使用確認流程；不自動推播 |
| 購物 | 新增清單、品項、勾選完成 | 沿用原資料與 ownership |
| 筆記 | 查看原文、修改標題與內容 | 輸出以 textContent 顯示，不執行筆記 HTML |
| 日曆 | Google Calendar 日期範圍查詢、確認新增、外連 Google 編輯 | 只讀已授權日曆；授權錯誤不得回報空清單 |
| 活動 | 關鍵字、全部／已收藏、分頁、來源、收藏切換 | 查 Life 已匯入池，不發動新的網站探索；標示待核與費用未知 |
| 今日總覽 | 今日／逾期待辦與今日 Google 行程 | 待辦前 20 筆、行程前 50 筆；畫面明示範圍 |
| 停用 | 解除綁定／unfollow／feature hidden 會撤銷後續 LINE 存取 | 原有 Life 資料不刪；重新加入好友需重新綁定 |

下一版：主動提醒、每日摘要、語音／圖片辨識、完整自然語言查詢、多使用者共用清單。沒有建立上述排程或推播工作。

## 3. 入口與六格選單

| 位置 | 名稱 | LIFF page |
|---|---|---|
| 上左 | 快速記錄 | capture |
| 上中 | 今日總覽 | today |
| 上右 | 查我的資料 | search |
| 下左 | 待辦・購物 | tasks（頁面上可切 shopping） |
| 下中 | 日曆・活動 | calendar（頁面上可切 activities） |
| 下右 | 我的 Life | home |

- LIFF endpoint：`https://<同環境 Hosting>/line/index.html`。
- Google 身分綁定頁：`https://<同環境 Hosting>/line/link.html`，需外部瀏覽器開啟。
- Life 個人化 → 服務連結新增 LINE 入口，僅在 LINE 已設定且帳號 rollout 可用時顯示。
- 選單 URL：`https://liff.line.me/<LIFF_ID>?page=<page>`。無須先按選單即可直接傳文字。
- `scripts/line_rich_menu.py` 預設只輸出 JSON；`--apply` 才會建立、上傳指定圖及套用預設選單。不自動刪除舊選單。

## 4. 架構與權責

Firebase Hosting 的 LIFF 輕量頁面 → 既有 FastAPI → PostgreSQL／既有 Google adapter。Flutter 仍為完整 Life 主站；LIFF 使用同一組業務 API，不另建資料庫或完整第二套產品。

Webhook 路徑不執行 AI、Google 日曆查詢或通用 Agent loop；僅驗證、綁定握手、持久化文字、有限 DB 查詢及 Reply。AI 理解移至使用者開啟草稿並按解析後，沿用既有 Inbox。沒有記憶體背景工作、長駐 worker 或新的 Cloud Tasks/PubSub。

Webhook 為有界同步處理，與原方案中「耗時工作非同步」相容的方式是將耗時理解移出 webhook，而非虛稱已有 queue。資料先 commit 再回覆，HTTP 失敗由 LINE 重送；即使 Reply 失敗仍可從 LIFF 最近草稿找回。

## 5. 資料與 API 契約

新增四張表：`line_bindings`（namespace＋LINE id／Life sub 唯一）、`line_link_tickets`（雜湊碼、10 分鐘、一用）、`line_sessions`（雜湊 bearer、1 小時）、`line_events`（namespace＋webhookEventId 的 SHA256、文字草稿、回覆狀態、到期時間）。

| API（/api/v1/line 下） | 用途與授權 |
|---|---|
| GET config | 僅回公開 LIFF ID／origin；未配置 503 |
| POST webhook | 原始 body HMAC 簽章；只接受一對一 user source |
| POST session | LINE 平台驗證 ID token 的 issuer/audience/expiry/sub，再查既有綁定 |
| POST link/start、check、confirm、unlink；GET link/status | 已登入 Google Life 身分＋line rollout；LINE session 不可管理綁定 |
| GET search | 已登入帳號＋目的功能 rollout；kind 白名單、q≤120 字、20 筆分頁 |
| GET drafts、drafts/{id} | 帳號＋namespace＋TTL＋life_inbox 權限；最近最多 30 筆 |
| POST drafts/{id}/archive | 本人明確移除草稿原文；保留事件去重 receipt |

正式業務寫入使用既有 `/api/v1/inbox/interpret`、`commit`、`receipts/{action_id}`，並沿用 Notes／Tasks／Shopping／Calendar／Curated API。新增 `line_event_id` 只用於讀取屬於該使用者的原始 capture 日期，不接受客戶端提供任意日期基準。

- 「明天」以 LINE 簽署事件的傳送日期（Asia/Taipei）為基準；截止或結束時間不明不自填。
- 草稿正式 action ID：`line-<event-id>-<candidate-index>`；同草稿同候選重送保持同一 ID。請求結果不明時保持欄位與 ID，不換 ID 重試。
- 手動新輸入採一次畫面內固定的隨機 capture ID。重新整理後再次手動輸入視為新的意圖，不宣稱跨頁面自動辨識同義重複。
- PostgreSQL 與 Google 是不同交易邊界；外部 Calendar 結果不明使用 UNKNOWN，不自動 retry create。

## 6. 安全、保留與故障處理

1. Secrets 僅 Secret Manager 注入；frontend/config/log 不含 channel secret、access token、ID token、綁定碼。
2. Server 驗證 LINE ID token；不信任 LIFF 解碼 profile、名字或 email。Google 既有帳號是 Life ownership 來源。
3. 兩端握手，綁定碼 192-bit 隨機且雜湊儲存。確認前比較 LINE 尾碼；唯一約束防止競爭綁定。
4. LINE session 使用 HttpOnly/Secure/SameSite=Lax 的 `__session` cookie；每次 request 重查 binding、expiry、namespace、rollout。Owner 的 LINE session 也不能存取 admin、Drive、Gmail、connector。
5. Cookie 寫入端點驗證固定 origin；群組／多人聊天室訊息完全忽略。URL 與 private text 不寫一般 log。
6. 保留既有 Owner 對 NULL legacy rows 的既有 ownership 規則，一般帳號不可讀取。
7. 草稿讀取 TTL 30 天；下一個合法 webhook 有界清理各類最多 100 筆到期事件／session／ticket。低流量時物理資料可能晚於 TTL 才清理，不能宣稱時間一到即完成實體刪除；讀取始終阻擋過期資料。
8. 封鎖官方帳號（unfollow）立即將 binding inactive；解封不自動恢復。重新綁定需由 Google Life 身分先解除舊綁定。
9. 回覆失敗不自動改用 Push；可能已成功送出的 reply token 不換 token 猜測重發。草稿可在 LIFF 找回。
10. 顯示外部錯誤與部分完成；沒有 CI 或實機證據不能標 DONE。聊天回覆可出現在手機通知預覽，私人長文預設留在登入後頁面。

## 7. 部署、版本及回滾

候選版 `0.6.0+6`，公告 featureKey=`line`。V3 原有 tests/build/migration/staging/live/rollback gates 保留。新增 `enable_line`，預設 false；每次需要 LINE 的手動 staging／promotion 必須勾選，並配置對應 STAGE／PROD variables 與 Secret Manager 數字版本。完整配置見 [WI](line_integration_b_wi.md)。

正式與測試應使用不同 LINE channel/LIFF、不同 namespace；同一 OA webhook 只能指向一個環境。只有一個 OA 時，應先在 staging 驗收，切正式時同步替換 endpoint、webhook、menu 及配置，不同時假裝兩環境都可用。

既有 V3 promotion 會把同一 candidate 同時用於 staging gate 與正式流量。當 candidate 配置 PROD origin 時，staging 的 LINE 頁面會拒絕環境不符；這不是另外一個已啟用的 stage LINE 版本。一般 staging OAuth gates 不變；要再測 LINE staging，重新跑 STAGE 配置候選。

停用以 rollout hidden 或 `enable_line=false` 的正常 V3 發布處理；Google Life 功能保留。回滾 application revision，不 downgrade 0023/0024、不刪原有資料。尚未核對真實 DB revision 或 LINE Console，均 NOT VERIFIED。

## 8. 交付／驗收對照

| 工作 | 程式或文件 | 自動／人工驗收 |
|---|---|---|
| 原版復原 | archive patch、manifest、test receipt | hash＋原版 153/15 重跑 |
| 連結／登入 | api/line.py、services/line_channel.py | 簽章、雙端確認、撤銷、origin、帳號隔離 |
| 資料／契約 | models/line.py、migration 0024 | Alembic single head＋PG CI；真實 DB readback 獨立 |
| LIFF | web/line/*、Flutter 服務連結 | 離線 Playwright；LINE iOS/Android 由 Owner |
| 選單／部署 | line_rich_menu.py、line_deploy_flags.py、V3 workflow | 配置 fail-closed；真實 Console 由 Owner |
| 正式業務 | 既有 Inbox／domain API | targeted regression＋Owner WI 多功能讀回 |

參考官方文件（2026-10-28 查核）：
- https://developers.line.biz/en/docs/liff/using-user-profile/
- https://developers.line.biz/en/docs/messaging-api/receiving-messages/
- https://developers.line.biz/en/docs/line-login/getting-started/
- https://developers.line.biz/en/docs/messaging-api/using-rich-menus/
