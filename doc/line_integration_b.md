# Life Assistant × LINE｜方案 B 正式規格、落地現況與 WI（2026-10-28）

> **2026-10-28 復原暫停／NOT VERIFIED：本文件第 1–8 節記載的是後一次重新實作，不是「LINE整合方案評估」前次已測試原版；使用者要求排除這批重寫成果，不納入正式完成清單，也不得直接沿此版本開發、配置、部署或宣稱已驗收。**
> 前次對話曾回報 153 項後端測試（含 LINE 15 項）通過，但尚未取得原始碼、commit、執行命令與同版本測試收據；2026-10-28 前次開發前 main `56275487` 與現存其他分支均無 LINE 專項程式，`life_assistantGPT` Drive 根及其可見子資料夾沒有可恢復的原版。這次版本 `a21979c` 的 GitHub CI [#40616784019](https://github.com/tommylin15/life_assistant/actions/runs/40616784019) **FAIL**（Backend release revision 斷言仍預期 0022，實際配置已到 0023；其他四項成功）。完整證據、隔離決策、恢復條件見 [復原查核紀錄](line_recovery_audit_20261028.md)。
> **禁止**在找到且核對原版之前依本文件下方的開發／部署 WI 接續重寫；目前保持 `LINE_BRIDGE_ENABLED` 預設 false，保留原始 Git 歷史與非 LINE 修改；尚未回退程式或 migration。

> 狀態：**PARTIAL（程式已提交 main；CI、Staging、LINE 真人與正式版尚未驗收）**。
> 唯一有效 implementation 來源為 GitHub main 與同 SHA 的執行證據；本文件是技術規格及驗收指示，不等於產品已啟用。手動驗收由使用者執行。

## 1. 決策、邊界與業務目標

採用方案 B：既有 LINE 官方帳號 + LINE Messaging API + 六格圖文選單 + LIFF 頁面，快速留下日常文字，透過 Life 提供的待辦、購物、筆記、行事曆、活動資料與後續查詢。使用者的個人資料仍由 **Life PostgreSQL** 持久化。LINE webhook 只作薄型入口；其餘既有 FastAPI 授權／資料模型／功能開放管控維持不變。omniAgent 不處理 LINE 帳號、DB 直接寫入或 webhook 派送。既有 Google OAuth 用於 Life 使用者身分；LINE OpenID ID Token 僅證明 LINE 身分，不授予 Google 權限。

每次 LINE 訊息接收後的第一階段只進入 **LINE 草稿**；**不得自行建立、變更、完成或刪除 Tasks/Shopping/Notes/Calendar**。使用者在 Life 的「快速新增」先確認分類、時間與目的地，才透過原本 Life Inbox 提交。無日期不補日期；傳訊日期不是自動推定的行程日期。Google Calendar／活動探索仍以 Life 既有功能為準，不另造平行資料源／排程。

## 2. 系統架構

```text
LINE 官方帳號／文字訊息 ── HTTPS webhook (HMAC SHA-256)
                           │
                           ▼
Firebase Hosting /api/** → Cloud Run FastAPI /api/v1/line/webhook
                           │（驗證、個人帳號綁定、訊息 ID 去重）
                           ▼
                    Life PostgreSQL
          line_account_links / line_capture_drafts
                           ▲
           LIFF (/line.html) + LINE Login OpenID
                 （伺服器核驗 ID Token）
                           │
                Life Google 登入 Cookie
                  → bind / unbind
                           │
        個人 scoped drafts / summary（唯讀）
                           │
     主動確認後才經既有 Life Inbox／其他 API 寫正式項目
```

新資料表 migration：`backend/alembic/versions/20261028_0023_line_bridge.py`，Revision `20261028_0023`，接在 `20261019_0022`，新增 `line_account_links`（`line_user_id, audience` 複合 PK）與 `line_capture_drafts`（`message_id` PK）。新增索引及外鍵，不更動既有個人資料；禁止 destructive downgrade。單一 LINE user ID 在 staging/production 是不同綁定，不得相互轉用。

## 3. 交互體驗與能力矩陣

| LINE 圖文選單 | 已提交到 main 的版本 | 下一個待開發階段 |
| --- | --- | --- |
| ① 快速記錄 | 私聊文字經驗證後保存草稿；LIFF 讀最近 20 筆，複製後進 Life 快速新增確認 | 直接從草稿進 Life 預填／確認流程、照片／語音轉文字 |
| ② 今日總覽 | LIFF 顯示本人最多 5 筆未完成待辦、5 個購物清單名稱 | 整合本人日曆、今日日程與提示 |
| ③ 查資料 | LIFF 已有 `/search?q=` 限量、按人 scoped 搜尋 Life 筆記、待辦及購物品項（每類最多 10 筆，僅關鍵字匹配，**不是全文 AI 搜尋**） | 活動與歷史個人記錄、模糊語意及分頁檢索 |
| ④ 待辦・購物 | 同上基本列表；沒有直接改狀態／刪除 | Life 原有授權 API 明確操作 |
| ⑤ 日曆・活動 | 連到 Life 網站現有入口；**不是 LINE LIFF 原生查詢** | 導向指定 Life 頁面、串接本人 Google Calendar |
| ⑥ 我的 Life | 連到既有 Life 網站 | 統一深連結及 LINE 登入後返回 |

以上 ③ 的活動範圍及 ④–⑥ 不能對外宣稱完整完成；除已證實的 LIFF 基本 UI／API source，實際 LINE 真人運作也仍是 NOT VERIFIED。

## 4. API 契約

均位於 `/api/v1/line`：
- `GET /config`：僅回傳 enabled、public LIFF ID 與環境。server-side 配置不足時 503；不曝露密鑰。
- `POST /webhook`：僅接受 LINE 官方原始 body 的 `X-Line-Signature` 正確 HMAC-SHA256；每次最多 50 events、64 KiB，僅私聊文字，最多 1,200 字；不接收群組；使用 LINE message ID 防重送；未綁定不得保存；可回覆簡短提醒，不輸出憑證或原始文字到 Log。
- `POST /bind`：需使用者 Life `__session` Cookie + LINE OpenID `id_token`，後端呼叫 LINE 官方 ID token verify；同 LINE ID 綁定另一人須回 409；staging 與 production 隔離。
- `POST /unbind`：需雙身分，使用者只能撤銷自己的綁定；撤銷後 /summary /drafts 不可用，未來私聊訊息不得入庫。
- `GET /me`、`GET /drafts`、`GET /summary`：LIFF 的 LINE ID token Bearer，每次向 LINE 核驗且只讀已綁定 user_sub 的資料；`GET /search?q=` 額外提供 bounded 本人筆記／待辦／購物品項的關鍵字查詢，不提供 Google Calendar 或活動；禁止使用 LINE userId 客戶端直接作為 Life user_sub。

目前沒有 Life 正式記錄的 LINE 自動寫入 API；一旦真正要新增應經原有 Life Inbox `interpret → explicit confirm` 契約，不得讓 webhook 直接執行寫入。

## 5. 設定與部署（全部不得提交到公開 GitHub）

| 變數 | 用途／規則 |
| --- | --- |
| `LINE_BRIDGE_ENABLED` | 預設 `false`；只在 LINE、資料庫與授權設置完成後開 `true` |
| `LINE_BRIDGE_AUDIENCE` | 必須明確為 `staging` 或 `production`；與 Life session 所屬站一致 |
| `LINE_CHANNEL_SECRET` | LINE Messaging API channel secret；Secret Manager 注入 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API access token；Secret Manager 注入，僅用於 reply API |
| `LINE_LOGIN_CHANNEL_ID` | LIFF 所屬 LINE Login channel ID（非 Messaging channel ID）；ID token 驗證 audience |
| `LINE_LIFF_ID` | LINE Login channel 中已建立的 LIFF ID；公開客戶端配置 |
 
LINE Developers 設定：在同一 LINE Provider 中核對既有官方帳號的 Messaging API channel（取得 Channel secret、Access token），建立或選用 LINE Login channel，在該 Login channel 建立 LIFF App：**Endpoint URL** 指向部署後的 `https://<host>/line.html`，Scope 勾選 `openid`，可選 `profile`。正式 Webhook URL：`https://<host>/api/v1/line/webhook`；Webhook 功能啟用，並由 LINE Console 完成 Verify。若用戶仍在 staging 做測試，優先使用獨立測試 LINE OA/Channel、獨立 LIFF endpoint 與相應候選部署／受控環境變數，避免同一 production OA 對到錯誤 audience。LINE 的 Channel secret 與 access token 不能傳在對話中，也不能寫入 docs 或 git commit。

LINE 六格 Rich Menu URL 指向已核證之 `https://<host>/line.html?view=drafts`（①）、`?view=summary`（②–④）、`https://<host>/line.html`（⑤⑥，LIFF 再跳 Life 功能）；正式上線前要在 UI 文案上註明 ③–⑤ 尚未具備完整查詢的限制，不宣稱完整串接。由 LINE OA Manager/LINE Developers 完成選單配置及是否設為預設；不得於尚未驗收時直接取代現有正式 Rich Menu。

Firebase Hosting 應保留既有 `/api/**` rewrite 到同個 Cloud Run FastAPI；`web/line.html` 隨 Flutter Web 靜態站部署（實際 Hosting 讀回待驗收）。**Production 切流仍受既有 V3 手動 promote / same-SHA / rollback gate 控制**；本次 commit 不宣稱啟用 production LINE。

## 6. WI：由使用者執行的整合／驗收指示

**WI-LINE-00｜前置與版本讀回**  
確認 GitHub `main` 含 `backend/app/api/line_bridge.py`、`backend/alembic/versions/20261028_0023_line_bridge.py`、`web/line.html`；找出相同 SHA 的四項 CI + staging workflow；任一失敗先停，不以歷史 CI PASS 替代。Cloud Run staging 應讀回有界 migration `alembic_version=20261028_0023` 與兩個新表；禁止用 production 證件貼日誌。

**WI-LINE-01｜配置、身分與綁定（使用者操作）**  
用 LINE Developers 獨立測試 OA/LIFF：Webhooks 測試成功、LIFF 能 `openid` 登入；先登入 Life staging Google 帳號，再開 LIFF 綁定，看到「已綁定」。若 Life 未登入不能綁；不同 Google 帳號綁同 LINE ID 應 409；staging 綁定不應使 production 身分取得任何 staging 記錄。

**WI-LINE-02｜實際私聊快記與去重（使用者操作）**  
傳三筆虛構短文：`明天買牛奶`、`下週活動記一下`、`週五晚上七點吃飯`；開 `/line.html?view=drafts`，每則只出現一次，文字相同、時間以 Asia/Taipei 正確顯示。LINE redelivery 再送同 message ID 不得重複；無效 Signature、群組來源、未綁定帳號、超長文字不得入庫。草稿不是 Life 正式 Task：沒有操作 Life Inbox 確認前，Tasks/Calendar 不新增任何資料。

**WI-LINE-03｜唯讀查詢與授權（使用者操作）**  
用已綁定身份讀 summary，對照 Life 中同一帳號最多五筆未完成待辦與五張購物清單；另一帳號及撤銷後應拒絕（401/403/404 依情境），不得返回任何第一個人的文字。日曆與活動目前為 Life 連結：只驗證能打開既有 Life，不把它認作 LIFF 原生功能。

**WI-LINE-04｜撤銷與異常（使用者操作）**  
點「解除綁定」，再送訊息：DB 不得增加草稿；`/drafts` 不得讀舊內容。LINE access token 不可寫入 logs；失敗時不可假回已正式建立 Task。LINE API 超時、斷線應顯示失敗；不要捏造成功通知。

**WI-LINE-05｜確認與發版（使用者決策）**  
先取得相同 SHA Backend/Flutter/PostgreSQL/Deploy CI、Staging Hosting、FastAPI API/DB、LINE 真人驗收證據，並明確列出 ③–⑥ 待辦能力。**只在本人驗收核准後**依既有手動 V3 promote 進行 Production／Hosting 同 SHA readback；再到 LINE Console 變更正式 webhook / Rich Menu。即使 CI 全綠，但真正 LINE 真人與持久化讀回未完成，整體仍標 PARTIAL。

## 7. 狀態與下一工程入口

| Gate | 當前判定 | 理由 |
| --- | --- | --- |
| Code & GitHub main | PASS（source present） | 已提交 Router、Model、migration、LIFF、測試來源；仍可依 CI 發現修正 |
| 測試執行 | NOT VERIFIED | 已提交合成測試，尚無可引用的同 SHA 完整結果 |
| CI | NOT VERIFIED | 須查詢此次新 SHA 的 GitHub Actions |
| Staging + migration | NOT VERIFIED | 尚無這次 SHA 的 Cloud Run/PG/Hosting 實際讀回 |
| LINE Console 配置、真人 | NOT VERIFIED | LINE Channel/LIFF/Secrets 未提供證據 |
| Production + runtime | NOT VERIFIED | 尚未推定部署或 LINE 功能可用 |
| 方案 B 完整使用體驗 | PARTIAL | 查資料、直接確認、日曆/活動深連結、正式選單後續實作仍需開發 |

唯一後續工程：實作 **草稿→Life Inbox 預填→逐項確認** 的 LIFF 流程（保留按人授權與嚴格去重），再擴充筆記／活動／Calendar 查詢；目前不另外引入 agent orchestration、不新增獨立 Scheduler、不建立第二個使用者 DB。

參考：GitHub `doc/life_inbox_quick_capture_spec.md`、`doc/PROJECT_RULES.md`、`doc/ci_cd_ghcr_release_policy.md`；LINE 官方文件 https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/ 、https://developers.line.biz/en/docs/liff/using-user-profile/ 。

## 8. 給其他 AI／工程代理的可執行 WI（不需重新規劃）

請使用下列指示在下一工程輪次執行，**不得直接把尚未驗證之功能標 DONE**：

> 你在 `tommylin15/life_assistant` 的 `main` 繼續 LINE 方案 B。先讀最新 `doc/line_integration_b.md`、`doc/todo.md`、`doc/PROJECT_RULES.md`、`doc/ci_cd_ghcr_release_policy.md` 以及現行 Backend/Flutter/Alembic。不要沿用對話中的歷史「測試已通過」說法。維持單 branch main，最小差異修改。功能開關預設關閉，不得寫入真實 channel secret、access token、ID token、個人訊息至程式、測試或 log。
>
> 首先核對這批 source、synthetic tests 與 release revision 0023 的相容性，補修 CI 失敗；保留 LINE HMAC raw-body 驗證、server-side ID Token verify、Life Google session 雙重綁定、跨帳號與 staging/production 隔離、訊息 ID 去重及已撤銷拒絕。下一功能只實作「LINE 草稿 → Life Inbox 預填 → 多項逐筆確認」及缺失的活動／Calendar 深連結和唯讀查詢；不能讓 webhook 直接永久新增或刪除個人主資料。
>
> 使用 synthetic 狀態執行 Backend 單元／API／PostgreSQL migration、Flutter smoke、security regression，確認四 CI 同 SHA；再使用現行 V3 staging-only 執行、讀回 migration 0023 與 Hosting /line.html，不得自動 promote production。將所有 PASS/FAIL/NOT VERIFIED 證據回寫 `doc/CURRENT_STATE.md` 和唯一 `doc/todo.md`。LINE Console、Secret Manager 憑證、LINE 真人操作與 Rich Menu 驗收由使用者執行，沒有真人證據一律 NOT VERIFIED。不可 force push、覆寫舊規格、清空 production DB 或更動高風險 IAM。
