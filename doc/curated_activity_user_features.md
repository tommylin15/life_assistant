# Life 活動使用者功能｜UX V3 唯一有效規格（2026-10-11）

**決策：APPROVED DESIGN；程式、CI、staging、production/runtime 逐層另驗，不能以文件更新宣稱功能 DONE。**
本文件取代 2026-10-10 同檔的雙入口舊 UX、星等 UI、七種操作、提前預警／確定參與／旅遊候選等當期需求；舊程式與舊個人資料先留相容，不做 destructive migration。正式實作以 GitHub main、runtime evidence 為準。

## 1. 資料與產品邊界

- 上游維持 **ChatGPT 探索 → Drive 精選池 → 獨立「交接資料」Sheet → Life GCP Job → PostgreSQL curated pool**；穩定 `event_key/content_hash`、DB commit 後版本一致 ACK 及去重規則不變。詳見 [交接契約](curated_sheet_job_ingestion.md)。Life **不**重啟官網／文化部／TDX crawler、舊 Queue／lease、第二輪 AI，不因 UX 變更回改 Drive 探索流程。
- **一個共用主活動池，兩個使用者入口**：「限時機會」與「活動探索」。活動可同時在兩入口出現；主活動一張卡片、不同優惠／場次在卡內展開，不能將子項當成獨立重複主活動。
- 移除「精選／活動精選池」第三個**使用者導覽**；舊 `/more/curated` 應兼容導向「活動探索」或共用查詢，不應突然 404；舊 `/more/events` 免費活動頁退出一般導覽，原資料、API 和路徑先保留相容並清點呼叫者。後台仍可檢視共用資料池。保留兩入口各自 feature rollout 與個人導覽排序，舊 `events` 功能旗標／偏好須安全遷移。
- `importance`／上游 1／3／5 星是**資料層原欄位**，標準未定前 **全部使用者 UI 隱藏、不提供星等篩選、也不得以星等作預設排序**。不改探索端評級，也不刪除已存欄位。

## 2. 進頁載入、排序、分頁

- 進入每個入口即由 **FastAPI 對整個 PostgreSQL 資料集執行 server-side 查詢，預設只取 5 個主活動群組**；不先把全庫載入 Flutter，也不要求先輸入條件。按「再看 10 筆」續取後端 10 個主活動群組；改搜尋／切換速查／收藏時重設游標並重取前 5 個主活動群組。回應須有可靠的 `has_more/next_cursor`（或等價證據），不得因返回的子場次數誤判總群組數。穩定排序避免跨頁漏項／重複，資料更新時適當處理失效游標。
- **限時機會**：只選需要行動的報名、預約、領券、限額優惠等；預設顯示最近要截止／開報／可行動的機會，已確認失效者不混入一般清單。報名開放和報名截止是不同欄位，不能用活動開始日代替，未知不假造。
- **活動探索**：依正在進行、最近開始、未來開始的日期接近程度排序；期間與今天／週末重疊的跨日活動必須被查到，不是只比 `starts_on`。沒有可靠結束日，不能宣稱已結束。
- 兩入口均有「**最新收錄**」速查，依首次收錄 `created_at` 排序（不是 `updated_at` 或每次掃描時間）。如要顯示實際入庫筆數，必須從後端回應計算，不寫死 5。
- **已收藏**模式可保留已過期活動供使用者回查，標清「已結束／資料未知」；一般模式不顯示已確定過期／取消的活動。切到活動詳情／外部網址再返回時，保留關鍵字、入口、速查、篩選、收藏模式與已展開的列表位置。

## 3. 快速查詢和一般搜尋

- 頂部始終有一般搜尋框，僅搜尋四類現有資料：**活動標題 `title`、主辦單位 `organizer`、地點 `city/district/venue`、活動內容 `summary` 與可用的既有活動摘要**。目前 `summary` 可能只是 `evidence_summary`，不可誇大成官方活動全文；沒有獨立 keywords 欄位，不引入 AI／向量搜尋。一般中文包含比對、空白正規化，必要時用 PostgreSQL 索引；查詢的是 DB 全部符合條件的資料，不是只查首批 5 筆。原始證據文字需避免不相關的噪音壓過標題。
- **限時機會**速查：即將開報（預設未來 7 天）、今天開報、3 天內截止、限額優惠、時間待公布、最新收錄。**不提供 5★優先**。
- **活動探索**速查：正在進行、本週末、7 天內開始、30 天內開始、免費活動、最新收錄。**不做「附近地區」或 GPS 定位**。
- 「更多篩選」精簡為：地區（全台／北／中／南／東／離島、縣市及已有資料的行政區）、活動類別（由 DB 實際類別動態供應）、日期、自有可靠證據的費用類別、個人收藏狀態。北中南東以**固定縣市對照和同名正規化**計算，不需要 AI；`city` 缺值或不明時放在未分類，不依場地名稱推測縣市。費用未知不可填 0，「可退押金」不當成不可退成本。最小空結果狀態要有「清除篩選」。
- 速查日期以 **Asia/Taipei** 計算，僅有日期的值採日期精度，不補時分；交接時間有衝突時保留未知。不得將「公告開報」或「原站連結存在」寫成「現在可報／名額尚有」。

## 4. 活動卡片與唯一外部動作

- 卡片只顯示名稱、入口對應的**活動期間或報名開放／截止**、城市／地點、已知費用／重要資格、來源待核狀態；不顯示任何星等。子優惠／場次可展開，但預設精簡，手機友善。
- 唯一外站動作統一標為 **「前往網址」**：若該操作是報名／優惠且有可信有效 `registration_url` 優先用它，否則用官方 `official_url/original_url`；展示的是對應子優惠的確切連結。不得因有 URL 就宣稱報名有效或成功。後端驗證 HTTP(S)（原交接規範為 HTTPS 公開 URL），前端僅開啟安全已驗證網址，不使用未信任的 URI scheme。
- 個人操作在兩入口**只保留三項：收藏、建立待辦、日曆日期標記**。不顯示追蹤狀態、預警提醒、報名日曆、確定參與、旅遊候選等既有七動作中的其他項目；本期不新增 App 推播或自動報名。保留既有個人紀錄及相容 API，但不以舊功能作 V3 完成門檻。

## 5. 收藏：同一活動一次、兩入口速查

- 卡片右上書籤一點收藏／再點取消；限時機會和活動探索各自上方有「全部／已收藏」快速切換。收藏模式與關鍵字、時間／地區條件聯動，不新增「我的收藏」主選單。
- 一個主活動被多場次／多 URL 展開時**收藏主活動一次**，兩入口立即同步狀態。現有 `CuratedPersonalAction(user_sub,activity_id,kind='save')` 是**子項 identity_key 粒度**；V3 應制定穩定主活動 key 關聯、既有收藏映射、聚合查詢／批次查詢，不能因新父子群組而丟失或複製收藏。個人資料按 `user_sub` 隔離，跨帳號不可讀／寫；不要對 1000 筆 actions 限制做不完整且不提示的收藏清單。
- 不將收藏轉成待辦或日曆，不自動提醒；收藏後立即可在「已收藏」找到，失效活動不自動刪除收藏。

## 6. 與現有待辦、Google 日曆相容：活動網址必須可直接開啟

### 6.1 已核對的 GitHub source（2026-10-11）

| 元件 | 已存在（source） | V3 缺口／規範 |
|---|---|---|
| `backend/app/models/task.py` | Task 有 `title, note, due_at, reminder_at, source_type, source_ref, user_sub` | 不新建第二套待辦 schema；保留既有 user-owned Task 和可編輯狀態 |
| `backend/app/api/curated_actions.py` 的 `task` | 建 Task，`note=item.original_url`、`source_type='curated'`、`source_ref=item.identity_key`、`due_at=item.registration_deadline`；重試去重，解除時標記 cancelled | 現在只塞原頁 URL，可能不是該優惠的報名網址；且截止時間不能對所有待辦直接當到期日。新動作提供確認／可調整到期日（含不設），連到指定主活動／子場次 |
| `backend/app/models/schemas.py` `TaskOut`、`lib/web/tasks_page.dart` | Task `note` 可回讀／搜尋／編輯；卡片只以 `Text` 顯示備註；`TaskOut` 尚未回傳 source_type/ref | 在待辦卡片／詳情提供可點擊「前往網址」；有需要以**可選**欄位擴充 TaskOut 的來源標識以導向 Life 活動詳情，不破壞舊 Task API／非活動待辦。不可把所有備註當安全連結 |
| `backend/app/api/curated_actions.py` 的 `calendar_info` | Google Calendar 全天事件；結束日採**隔日 exclusive**；`transparency='transparent'`、無預設提醒；`description` 目前放原站 URL（有群組時放多個連結） | 沿用目前 Google OAuth 與日曆，不占 busy、不暗示已報名；`description` 第 1 個標示明確的「活動網址」應是可開的正確子場次 URL，詳細官方／報名來源可附後，避免多連結不知選哪個 |
| `backend/app/api/google_integrations.py`、`lib/web/calendar_page.dart` | 日曆 API 與 Google 事件均能保存 `description,location`；Life 日曆目前只用 `Text(event.description)` 顯示 | Life 日曆事件卡片／詳情增加「前往網址」可點擊操作（只對已驗證活動 HTTP(S) URL），可選「查看 Life 活動」深連結；不得要求使用者複製文字 |
| `backend/app/models/curated_actions.py` | 依帳號與活動／kind 存操作結果和 Google event ID | 同主活動去重、取消／再加入、手動更動日曆後的狀態回讀與失敗回報需驗證 |

### 6.2 使用者實際流程（V3 必須達成）

1. **建立待辦**：活動卡片點「建立待辦」→ 預填清楚的可編輯標題（如「報名：活動名稱」）、簡短說明、該活動正確「前往網址」及來源參照；到期日可依已知開放／截止日由使用者**確認選擇**，或不設日期；確認後使用**現有 Task** 建立，回應真實 Task ID。回到 Life「待辦」頁看得到，能直接點「前往網址」開原站，也能編輯、完成或取消。絕不能把未知日期補成今日午夜。重試／跨兩入口同一行動不可建立重複 Task。
2. **日曆日期標記**：活動卡片點「日曆日期標記」→ 只接受已知活動日或明確日期區間 → 使用使用者的現有 Google Calendar 整合建立**全天、free/transparent、無預設提醒**的資訊事件，標題須標示「活動日期參考」，`description` 預填「活動網址：HTTPS...」及必要來源、`location` 填有據場地（可缺）。建立後在**Life 日曆及 Google Calendar** 看得到同一筆，從 Life 日曆點「前往網址」直接開活動。相同使用者／主活動／日期去重，區分不同場次，不能誤佔忙碌時間。日期未知拒絕建立並清楚說明。
3. 只要 URL 可用，**待辦／Life 日曆中應可直接按「前往網址」**；回 Life 活動詳情的內部入口是可選輔助，外部網址才是本期必驗核心。沒有有效網址時隱藏按鈕、顯示原因，不產生假連結。連結必須同時可在手機與桌面運作。
4. Task 或 Calendar 使用者已編輯的私人項目，不因活動上游資料更新而被靜默覆寫／刪除；取消活動端操作需與私人原項目狀態保持可解釋一致，不可直接刪除人工修改內容。Google 授權失效、API 失敗、部分成功等要顯示實際結果，禁止報成功。活動母子關係與舊 identity_key 更新時，收藏與個人操作映射不能失效。

## 7. 開發順序與驗收門檻

| 優先 | 可交付工作 | 驗收要求 |
|---|---|---|
| P0 | 兩入口與舊導覽相容轉址；隱藏所有星等與移除後端排序／星等過濾 | Flutter mobile／desktop 與 API 查詢結果；舊連結不 404 |
| P0 | 首屏 5 筆群組、續看 10 筆；限時／探索日期排序、最新收錄、期間重疊、失效資料及 unknown 處理 | PostgreSQL 日期／時區／分頁／重送變更測試；不可只測 Flutter 本地篩選 |
| P0 | 兩組一鍵速查與四欄搜尋 | DB 全量查詢、空結果、中文、關鍵字、分頁與資料缺值 |
| P1 | 區域正規化、分類／費用與收藏多選篩選 | 固定縣市映射、未知區域／費用獨立、不使用 AI |
| P1 | 父活動共享收藏與「全部／已收藏」模式、取消收藏 | 兩入口同步、跨帳號隔離、既有收藏向後兼容 |
| P1 | 活動 → 既有 Task → 待辦頁可點「前往網址」 | 必測 task note/source、編輯、取消、重試、跨場次、開報／截止日確認和 HTTPS 防護 |
| P1 | 活動 → 既有 Calendar → 日曆頁可點「前往網址」 | 必測全天 exclusive end、transparent、無預設提醒、location/description、OAuth、去重與真實 Google 讀回 |
| Acceptance | GitHub source tests → CI → staging → owner 端到端 → 必要時 production | 按 `PASS / FAIL / NOT VERIFIED`，分別驗證 implementation、tests、CI、deployment、runtime、integration；只有證據齊全才 DONE |

不需因以上規劃新增第二套收藏資料庫、Activity crawler、新的 Google OAuth 系統、獨立搜尋引擎或 AI。所有實作需遵守 [PROJECT_RULES](PROJECT_RULES.md)，正式交接流程仍以 [curated_sheet_job_ingestion](curated_sheet_job_ingestion.md) 為準。
