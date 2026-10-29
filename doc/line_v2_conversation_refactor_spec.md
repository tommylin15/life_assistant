# Life Omni × LINE v2｜八格選單與對話式操作重構規格

- **版本：** SPEC v2.0 / 2026-10-29（Asia/Taipei）
- **狀態：** DESIGN APPROVED BY OWNER REQUEST（範圍與產品方向）；**SOURCE / TEST / CI / STAGING / PRODUCTION 均非本規格的功能實作證據**
- **GitHub 現行實作基線：** `backend/app/api/line.py`、`backend/app/services/line_channel.py`、`web/line/*`、`scripts/line_rich_menu.py`、`backend/app/api/curated.py`、`backend/app/api/curated_actions.py`、`backend/app/api/inbox.py`。本規格**取代 v1「六格全部跳 LIFF 頁面」的未來產品方向**，不否定 v1 已驗收功能、資料或原先的安全契約。
- **交付原則：** 本輪只完成規格與工作入口；不更動現行 OA 預設選單、Webhook、LIFF、正式 Life Web、資料庫、Cloud Run 或使用者紀錄。產圖與上架另立執行／驗收證據。

## 1. 決策摘要與非目標

### 1.1 產品決策

1. **Rich Menu：六格改八格（2×4）**；「待辦・購物」拆為「待辦」「購物」，「日曆・活動」拆為「日曆」「活動」。維持 Life Omni 薄荷綠主視覺，右下保留 Owner 提供的雙生獸意象作為 **Life Omni** 入口。
2. **前七格以 LINE 聊天內互動為預設**：使用 Messaging API 的 Postback、Quick Reply、Flex Message；不再全部連到同一個 LIFF 首頁。
3. **第八格 Life Omni 直接打開完整 Life Web App 的手機友善入口**（優先正常 HTTPS URI）。既有 Google Life 登入 Session 在同瀏覽器且有效時可沿用，跨 LINE 內建瀏覽器／Chrome／Safari 不保證 Cookie 共用；不得把 LINE ID Token 當作完整 Google OAuth 身分或暗中授權 Google 服務。
4. **LIFF 保留，但降級為補充編輯／授權／複雜確認的工具**：畫面直接定位單一任務，不再做第二個八格首頁。連結與撤銷仍遵循既有外部瀏覽器＋Google Life 雙端綁定。
5. **活動優先 Flex Carousel：依「最新進入 Life 活動池」排序，橫向滑動；「依 Tag 看活動」是活動功能內的第二層選單，並非第九個 Rich Menu 格子。** 收藏／取消收藏可在 LINE 內完成；進階篩選／大量瀏覽回 Life App。
6. **資料工程不重造來源**：只讀取 Life PostgreSQL 已匯入的 curated 活動與既有個人操作；不建立第二套活動 crawler、RAG 或 LINE 專用 DB。

### 1.2 暫不納入 v2 第一輪

主動推播／定時摘要、完整自然語言代理規劃、語音及圖片辨識、共享帳號或群組私有資料、跨使用者分享、任意複雜 Tag 多選、大規模 Life Web 全站重寫。需要時排獨立 v2.x，不能把預留 API 當作已完成。

## 2. Current vs Target：具體差異

| 項目 | GitHub v1 已有／可驗證的行為 | v2 目標（**未實作**） |
|---|---|---|
| Rich Menu | 六格 URI → 同一個 `/line/index.html?page=…` LIFF | 八格 2×4：前七格 Postback/必要 Message，最後一格 Life HTTPS URI |
| 聊天回覆 | 一般文字與附「開啟 Life」Quick Reply；直接傳訊先保存草稿 | Flex 卡、狀態操作、查詢導引、分類確認；只有少數情境跳 LIFF |
| 活動 | LIFF 查 `/free-events/curated`、關鍵字／收藏／分頁 | LINE 最新上架 Carousel、依分類／Tag 子選單、LINE 內收藏切換 |
| 待辦、購物 | LIFF 頁面編輯；聊天「待辦」「購物」回前五筆文字 | LINE 內清單 Flex／逐項 Postback 完成／新增；複雜編輯開 Life |
| 日曆 | LIFF 日期範圍及 Google Calendar API | LINE 內近期行程摘要；授權／複雜新增開 Life／LIFF |
| 內容解析 | Webhook 不做 AI；LIFF 手動 `/inbox/interpret`→`commit` | 保存草稿後、使用者明確觸發的有界分類→Flex 候選→確認寫入 |
| Life App | LIFF `home` 再按「開啟完整 Life」 | Rich Menu 第八格直接到 Life 手機入口（登入沿用視瀏覽器 Session） |

**相容條件：** 維持 v1 既有 `line_bindings/line_sessions/line_events`、訊息草稿、Inbox action_id receipt、FeatureRollout、舊六格 URI 的生命週期；新版本 staged rollout 可退回 v1 入口。不刪除 v1 使用者資料或做 destructive migration。

## 3. 八格 Rich Menu IA、圖片與點擊契約

最終圖面採 **2500×1686，2 列×4 欄**；左右欄寬各 625，列高各 843；圖像與 bounds 一律由同一配置輸出並有測試，熱區須涵蓋圖片內完整對應按鈕。採不超過 1 MB 的合規 PNG/JPEG；圖中不可用假按鈕當未定義熱區。

| # | 列/欄 | 名稱 | bounds `x,y,width,height` | 動作／指令 | 下一步 |
|---|---|---|---|---|---|
| 1 | 上 1 | 快速記錄 | 0,0,625,843 | postback `v2.capture.start` | 引導在當前對話輸入文字；已輸入者保留原草稿 |
| 2 | 上 2 | 今日總覽 | 625,0,625,843 | postback `v2.today.view` | 今日待辦＋今日行程 Flex 摘要 |
| 3 | 上 3 | 查我的資料 | 1250,0,625,843 | postback `v2.search.start` | Quick Reply 選筆記／待辦／購物，接收關鍵字 |
| 4 | 上 4 | 待辦 | 1875,0,625,843 | postback `v2.tasks.list` | 未完成待辦 Flex、標記完成、更多 |
| 5 | 下 1 | 購物 | 0,843,625,843 | postback `v2.shopping.list` | 清單／品項 Flex、勾選、新增 |
| 6 | 下 2 | 日曆 | 625,843,625,843 | postback `v2.calendar.today` | 今日／近期 Google 行程摘要 |
| 7 | 下 3 | 活動 | 1250,843,625,843 | postback `v2.events.latest` | 最新 Flex Carousel；附「依 Tag 看」子選單 |
| 8 | 下 4 | Life Omni | 1875,843,625,843 | URI `<verified Life origin>/` | 直接開完整 Life Web 行動入口 |

- 上述 `v2.*` 是**邏輯命令名稱**，LINE `postback.data` 實際採有版本的精簡白名單，例如 `v=2&cmd=events.latest`，不是公開可寫的 REST API。每項傳入 ID／cursor 必須走受控 server-side state／不可猜測的短期 action token。
- 同一張圖片不要沿用 v1 2500×1686 的「六格狹小卡片座標」；新版圖檔、八個 bounds、Colab 發布 JSON 皆應一同版控與檢查。**先前建立的八格構想圖若未通過尺寸與熱區對照驗證，僅可作設計參考，不能聲稱上線。**
- 按鈕 1–7 優先 Postback，不讓用戶看到一堆系統命令文字；LINE 用戶端或回覆能力不足時退回簡短文字指引＋安全 LIFF 連結。
- 按鈕 8 必須用白名單站台 URI，不能拼接使用者可控的 arbitrary return URL。
- 改 OA 預設 Rich Menu 影響所有好友；使用者先前已同意可直接覆蓋舊選單、不要求保留舊圖，但**仍不得在沒有本版程式及端到端驗收前宣稱新八格已正式服務**。部署時以當次 OA API ID 讀回為準，不沿用六格的 Owner PASS。

## 4. 活動 Flex Carousel（第一優先）

### 4.1 LINE 對話 UX

點「活動」→ 回一則「活動探索」導引（Quick Reply：「最新上架」「依 Tag 看」「已收藏」「開 Life 進階探索」）並**預設直接附最新活動 Flex Carousel**。Carousel 可左右滑動，一張 bubble 代表同一個**活動群組／主活動**，不是同活動不同日期／子場次各占一張。

每張 Flex bubble 最多呈現：
- 活動標題（最多兩行，溢出縮略）、活動日期／期間（**未提供不亂填**）、縣市、1–2 個真實分類標籤、費用（免費／明確金額／未知）、核證狀態（已核證／待核／未知）。
- 額外短摘要或主辦來源，不放大段文章；**無授權圖片或無可信 HTTPS 圖片時，用文字 Flex bubble，不做圖片自動抓取**。
- 底部 `收藏`／`取消收藏`（postback 以目前 DB 讀回狀態判定）、`看來源`（已存在的 `original_url` 且 HTTPS）、`Life 詳情／更多`（受控 Life 路由，避免任意 URL）。
- 顯示「本次顯示前 N 個；按『下一批』繼續」，並附 `下一批` Postback；沒有結果時回「目前沒有符合條件的活動」，保留進階搜尋入口。

LINE 官方 Flex Carousel 最多 **12 個 bubble／50 KB JSON**，實作預設每批 6 張（可配置 6–10），必須同時檢查 bubble 數與 JSON UTF-8 大小，超限縮減筆數／文字，不能送到 LINE 才失敗。單次 Reply 最多 5 message objects；減少無用重複回覆。

### 4.2 最新「上架」排序契約（不與活動日期混淆）

- 現有 `GET /free-events/curated?entry=explore&quick=latest` 會按**分組後最早 `CuratedActivity.created_at` 倒序**，再按群組鍵固定排序；這代表**資料初次納入 Life 池的時間近似值**，**不是活動官方發佈日期、報名日期或活動開始日期**。
- v2 第一輪可直接重用 `quick=latest` 的既有排序，UI 標記為「Life 最新上架」；不得硬稱「官方最新發佈」。若日後要求追官方發布時間，需先驗證來源 schema 是否有可用 `published_at`，不能假造。
- 使用既有 `snapshot/as_of` 進行跨批分頁；同組只顯示一張主活動卡，避免子場次重複。快照不代表 DB 在修改後完全靜止；如分頁中內容已變，提示「清單已更新」並從第一頁重載。
- 只展示可由現有 activity filter 證明可見、符合 `entry=explore` 條件的資料，保留 verification、fee_kind（缺值如實顯示）。

### 4.3 「依 Tag 看」第二層選單（不是第 9 格）

按「依 Tag 看」→ 顯示 Quick Reply／Flex 分類選項 → 選一個分類 → 回帶相同 `quick=latest` 排序的篩選 Carousel → 可「下一批／換分類／回最新／開 Life」。

**資料能力邊界：** 目前 `curated_activities` 有 `category` 與 `handoff_details`，`GET /free-events/curated/filters` 有真實 `category` 值；尚未證實有泛用的多值 `tags` 欄位。v2 第一版將**可用 `category` 映射為單選 Tag 選單**（只顯示 DB 真實存在、允許展示的值）；不得預設產生「音樂、親子、戶外」等八個固定 Tag，除非資料存在且已建立明確映射。第二版若要多 Tag、階層 Tag 或同義字，需獨立設計 schema／migration／索引／回填／驗收；先不做。
- 類別數超過一頁時以 Flex 分頁或「更多分類」處理；Quick Reply 上限 13 個（包含返回、更多等，單次建議 8–10 個分類）。
- Tag selection token 必須與使用者及 namespace 綁定並有短 TTL；過期給出重新選擇入口，不套用先前權限。

### 4.4 收藏操作與資料一致性

- 重用既有 `PUT /free-events/curated/{activity_id}/actions/save` 的 ownership 與 parent-group collapsing 行為，但**Webhook 不直接呼叫需要瀏覽器 Cookie 的 API**；應抽取可重用 Domain Service，在已驗證 LINE 綁定 `user_sub`、活動可見及 `events/explore` rollout 之後呼叫。
- Postback 先依 server state 找到活動，讀回當前 `saved`，使用者明確選 `save=true/false`；重複投遞應收斂到相同狀態，不能因重複 click 反覆反轉。動作成功後回覆結果卡或狀態文字；先 DB commit／readback 再宣稱已收藏。
- 跨帳號或過期、已下架活動一律拒絕，不回傳他人收藏與資料；403/404 不等於「活動不存在於世界」。
- 卡片與原 Life 網站共用唯一 PostgreSQL source；網頁刷新應能讀回相同收藏狀態。

## 5. 其他七個入口：對話操作契約

| 功能 | LINE 內必備操作 | 何時進 LIFF／Life |
|---|---|---|
| 快速記錄 | 發文字→先存草稿→「分類並確認」Postback→最多四類候選 Flex（筆記／待辦／購物／行程），每筆明確確認→receipt。未知分類不能靜默正式寫入 | 欄位太多／日期或結束時間不足／複雜多筆時進定位到該 draft 的 LIFF |
| 今日總覽 | 以 Asia/Taipei 顯示今日／逾期待辦＋今日 Calendar；各來源獨立錯誤與截斷數量，不把授權失敗當無事件 | 全部紀錄／歷史／跨週檢視 |
| 查我的資料 | 先用 Quick Reply 選筆記／待辦／購物，再輸入字詞；回五筆內摘要卡、含更多入口；不猜任意 AI 語意 | 閱讀筆記原文、複雜多來源查詢 |
| 待辦 | 未完成前五筆，逐項按「完成」；可回「新增待辦」文字引導；狀態讀回成功才說完成 | 複雜編輯／修改多欄位 |
| 購物 | 顯示可用清單、近期未買品項；單項完成、文字新增（需確認清單）；不在無清單時亂建預設清單 | 多清單整理、批次勾選 |
| 日曆 | 近期已授權 Google Calendar 行程摘要，時間與時區明確；Quick Reply 提供「新增／看更多」，新增需確認完整時間 | OAuth 授權／撤銷、缺結束時間、跨時區複雜修改 |
| 活動 | 最新 Carousel、分類 Tag 子選單、已收藏、收藏開關 | 進階地區／日期／多分類篩選、活動完整詳情 |
| Life Omni | **直接連 Life HTTPS 手機入口**，不得先繞回 LIFF 八功能首頁 | 主站完整操作 |

**快速記錄效能設計：** 維持 webhook 原則「先持久化，再回覆」；第一次回覆「已保存草稿」＋「分類並確認」Quick Reply；分類在使用者下一次 Postback 才透過既有 `inbox/interpret` Domain Service 進行有界執行。若解析耗時、失敗或需要 OAuth，保留草稿並回 LIFF 深連結，不在 Webhook 同步等待無界 AI，也不新增默默推播的常駐 Agent。正式新增始終明確確認、固定 `action_id`；UNKNOWN 先查 receipt／原 Life 或 Google 資料，**不換 ID 自動重建**。

## 6. 架構、授權與 API 設計

### 6.1 端到端路徑

`Rich Menu Postback / 私聊文字 → LINE Webhook（簽章）→ Auth Binding + FeatureRollout → 對話命令路由（白名單）→ Life Domain Services（Curated / Inbox / Tasks / Shopping / Calendar）→ PostgreSQL／既有 Google adapter → Messaging API Reply (Flex / Quick Reply)`

LIFF 仍走 `Firebase Hosting /line/index.html → FastAPI → PostgreSQL`，完整版 Life 仍走 Flutter Web。**不新增 LINE 專用 database、不複製 Business Rules、不讓 webhook 以 Admin 權限讀取 Life 或繞過現有 API policy。**

### 6.2 建議拆檔（下一輪實作，不是當前程式）

- `backend/app/services/line_conversation.py`：命令／狀態機、讀取者權限、出錯狀態、回覆型態選擇。
- `backend/app/services/line_flex.py`：純函式 Flex bubble/carousel、大小／文字／連結／數量檢查、文字 fallback；不接 DB。
- `backend/app/services/line_activity.py`：用 Curated Domain 查詢 latest/tag/saved、去重主活動、cursor、安全收藏。
- `backend/app/services/line_action_state.py`（如需）：短期 Postback state／user/namespace/expiry／nonce，優先沿用 PostgreSQL；確有新增持久表才用 additive Alembic migration、PG readback。
- `backend/app/api/line.py`：維持唯一既有 Webhook 入口，新增有限 Postback 路由；絕不重新引入舊 `line_bridge` 為雙寫源。
- `scripts/line_rich_menu.py`：八格 actions 配置，圖片製作與 bounds contract test。舊 v1 可重產供回退，但新八格上架需另記 LINE API ID。
- `web/line/*`：只留補充編輯、draft confirmation、綁定與授權提示，不與 Web App 全站 UI 雙重維護。
- `lib/web/*`：行動版 Life 首頁、入口與登入回導另作獨立功能卡；不把這次規格誤認為已完成 UI 重構。

### 6.3 協議與資料契約

| 對象 | 來源／契約 |
|---|---|
| LINE webhook | 驗 `X-Line-Signature` 原始 body；只接受 `source.type=user`，拒群組／多人私人資料操作 |
| 身分 | `(namespace, line_user_id) → active LineBinding.user_sub`；每次 postback 重查，絕不信任傳入 user_sub |
| 入口命令 | `v=2&cmd=<allowlisted>`；未知、超長、篡改、過期一律安全失敗並引導重開選單 |
| 狀態 | `action_state_id / cursor` 為伺服器產生且限時，綁 user_sub + namespace + feature + 目標 ID + 版本；不在 LINE `data` 暴露內部 email／Google token |
| 活動列表 | 重用 curated `entry=explore&quick=latest&category=...&saved_only=...&as_of=...` 的 **Domain Service**，遵守資料可見性與 page snapshot |
| 收藏寫入 | 重用 `CuratedPersonalAction` 的 `save` service，顯式目標狀態，讀回後回覆 |
| 草稿/確認 | `LineEvent` + Inbox interpret/commit/receipt；stable action_id，不能因重送或快速重點產生兩次資料 |
| feature policy | 入口 `line` 及目標 `life_inbox / tasks / shopping / calendar / explore` 等 server-side gate 都須驗證，不僅隱藏按鈕 |
| 外連 | 僅 https 正式站／已允許來源；網址檢查、跳轉不暴露 session/token；Life Google OAuth 沿用自身登入流程 |

### 6.4 錯誤與隱私

- Reply token **只能使用一次，且一般須在收到 webhook 後 1 分鐘內使用**；不得將 AI 長任務綁在 webhook 等待。LINE redelivery 以 `webhookEventId` 去重，重新送達可能亂序；以 event timestamp 和既有 event ledger 收斂狀態。
- 回复失敗／UNKNOWN 不可盲目 Push 或使用新 token 猜測重發已寫入動作；訊息可顯示「結果尚未確認，請查回執」，資料仍保留。
- 私人筆記全文、精確地點、敏感資訊預設不在聊天室卡片完整展示；卡片為短摘要，需要更多在有身分驗證頁查看。聊天記錄可出現在通知預覽。
- 未經授權的 Google Calendar 錯誤顯示「需要授權」，不可顯示「今天沒有行程」。
- 每次 Webhook action 必有適度有界紀錄（event id hash、command、結果、error category、執行時間），不記 raw token、綁定碼、私人文字全文。

## 7. 驗收矩陣（v2 新增，與 v1 U01–U17 分開）

| ID | 驗收場景 | PASS 條件 |
|---|---|---|
| V2-01 | 八格圖面與配置 | PNG/JPEG 2500×1686、≤1 MB；8 區 x/y 不重疊不溢出、文字與點擊一致 |
| V2-02 | Rich Menu 八格真機 | 7 個互動入口觸發正確聊天回覆，第 8 個直達 Life；iOS/Android 各自記錄 |
| V2-03 | 快速記錄完整鏈 | 文字保存草稿→分類候選→必填檢查→本人確認→Life 正式資料讀回 |
| V2-04 | 意外重送與重複點擊 | 重複 webhookEventId/action token 不重複寫入，回同一 receipt 或明確 unchanged |
| V2-05 | 今日／日曆 | 時區正確、沒有授權正確報錯；跨來源部分故障不誤報空值 |
| V2-06 | 搜尋資料 | 查筆記／待辦／購物只屬本人，缺值與無結果明確、更多分頁正常 |
| V2-07 | 待辦／購物 Postback | 前後資料一致，項目不存在或已完成為安全冪等或明確拒絕 |
| V2-08 | 活動最新輪播 | 真實 Life `created_at` 排序、同主活動一張、Carousel 可左右滑、每批上限與下一批正常 |
| V2-09 | Tag 子選單 | 僅來源中實際 `category`，選類別有命中／無命中，且可換分類及恢復最新 |
| V2-10 | 收藏與取消收藏 | LINE 操作→PG→Life Web 真實讀回，重點兩次不變成反向，跨帳號隔離 |
| V2-11 | 安全／功能關閉 | unbind/unfollow/hidden/錯誤 token/跨 namespace 與 group 皆拒絕私人資料 |
| V2-12 | Flex 渲染與降級 | iOS/Android bubble 不嚴重溢出；12 bubbles／50 KB／5 msg／13 Quick Reply 規格守門與純文字 fallback |
| V2-13 | Life 入口與登入 | 有效既有 Session 減少登入；不同 browser 隔離能正常進 Google 登入，不越權 SSO |
| V2-14 | U17 異常恢復回歸 | Reply/網路故障時草稿／回執保留、UNKNOWN 不雙重建立，人工與受控故障分別取證 |
| V2-15 | 同 SHA 發布驗收 | tests、CI、GHCR image、Cloud Run／Staging、LIFF 靜態頁、OA Menu、Production runtime/PG/Google 分層取證 |

任何單一 v2 功能只標 `PASS / FAIL / NOT VERIFIED`；Docs 完成不等於 Source PASS。U16 既有 Owner「六格操作 PASS」只適用 v1，不自動繼承八格 V2-02；U17 在 v1 仍 NOT VERIFIED，後續須補。

## 8. 工程執行卡（依序，一次只有一個下一入口）

| SEQ | 工作卡 | 文件設計 | 程式開發 | 測試驗收 | 發布 | 模型建議 |
|---|---|---|---|---|---|---|
| V2-01 | LINE 對話核心＋活動 Carousel | Postback/Activity mapping、LINE state | `line_conversation`、`line_flex`、`line_activity`；latest/tags/saved，維持原 API | unit/contract、PG multiuser、真人 carousel／tag／收藏 | Staging-only，**不先換 OA 預設八格** | GPT-6 High |
| V2-02 | 八格圖面＋Rich Menu switch | 2×4 座標／Life 正式 URI／雙生獸風格 | 8-grid generator、JSON、圖片位置 contract、手動上架程式 | 靜態規格／LINE API ID readback／iOS Android 八格 | Staging 驗收後切 OA 選單 | GPT-6 Medium + 製圖 |
| V2-03 | 快速記錄與日常卡片 | 分類確認、Today、Tasks/Shopping、Calendar fallback | Domain service reuse、receipt/state、Flex/Quick Reply、LIFF 單任務導引 | 重送、UNKNOWN、缺值、Google 授權、讀寫回執 | Staging，再受控正式發布 | GPT-6 High |
| V2-04 | Life App 手機首頁與認證體驗 | 首頁最常用資料、Life 按鈕登入流程 | Flutter Web 手機資訊層次、共用登入改善（不自動 SSO） | iOS/Android、LINE內建瀏覽器／外部瀏覽器登入、手機性能 | 同 SHA App Release/Hosting | GPT-6 High |
| V2-05 | U17／完整正式整合驗收 | 上述矩陣、WI 補完 | 缺口修正；必要 additive migration | v1 regression、全部 v2、CI、候選、外部整合、Runtime | 正式發版／LINE Console readback | GPT-6 High |

**唯一下一工程入口：`V2-01 | 對話命令核心＋活動 Flex Carousel`**。先完成文件與 source diff、程式、離線測試、提交 main；Owner 在 Staging 用真 LINE 人工驗收；圖面上架等後續獨立卡處理。既有六格 OA 與 Life production 目前不得因規格文件自動切換。

## 9. 狀態、文件、來源與差異清單

### 9.1 本輪狀態

- 規格編寫／GitHub 及 Drive 讀回另記交付收據（文件層）。
- v2 程式／新資料表：**NOT IMPLEMENTED / NOT VERIFIED**。
- v2 CI、部署、runtime、LINE Flex 實機：**NOT VERIFIED**。
- v1 既有 Owner 已回報 U08–U15、六格操作子項 PASS；U16 跨平台及登入返回細項、U17 以及 U01–U07 指定例外仍依 [v1 WI](line_integration_b_wi.md) 記錄。
- 既有 main 屬於 v1；**規格與實作差異是刻意分層，不要把這份設計回寫成目前已運作 API。**

### 9.2 官方與專案來源

- LINE Rich Menu: https://developers.line.biz/en/docs/messaging-api/using-rich-menus/
- LINE Rich Menu overview: https://developers.line.biz/en/docs/messaging-api/rich-menus-overview/
- LINE Flex Messages: https://developers.line.biz/en/docs/messaging-api/using-flex-messages/
- LINE Flex carousel: https://developers.line.biz/en/docs/messaging-api/flex-message-elements/
- LINE Quick Reply: https://developers.line.biz/en/docs/messaging-api/using-quick-reply/
- LINE Postback/Actions: https://developers.line.biz/en/docs/messaging-api/actions/
- LINE Webhooks/redelivery: https://developers.line.biz/en/docs/messaging-api/receiving-messages
- LINE Messaging API reference (12 bubbles, 50 KB, Reply token): https://developers.line.biz/en/reference/messaging-api/
- Project: [Life v1 LINE spec](line_integration_b.md) / [WI](line_integration_b_wi.md) / [Project Rules](PROJECT_RULES.md) / [TODO](todo.md)。

