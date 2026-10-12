# Life Assistant｜導覽、個人化與五種視覺風格（核准規格 2026-10-12）

本文件取代 `doc/ui.md` 中舊版「首頁／待辦／日曆／專案／更多」主導覽及 `doc/ui_visual_system.md` 中「只有三風格」的產品決策。GitHub source、CI、staging、runtime 證據仍分開認定；文件核准不等於已上線。

## 導覽唯一入口與版型

- **底部四快捷恆存在**：第一格「首頁」固定；第 2～4 格由使用者選擇三個不重複、且已開放的業務功能。Google 授權、個人化、管理功能不可放到底部快捷。切換已選項仍保留選擇順序；停用功能以安全備選自動補滿三格。
- **左側完整導覽**：不再出現「首頁」、「更多」、「Google 整合」。手機用左上按鈕開啟抽屜；桌面用一套可縮合／展開的左欄；不再同時維護重複的固定 Rail 和抽屜清單。可用功能依法定 feature rollout 過濾。群組標題點擊只做展開／收合；進入子項後標示目前項目。
- 預設三群組（可調整群組排序及每組內子項排序）：
  1. **日常生活**：待辦、日曆、習慣、購物清單。
  2. **知識與計畫**：筆記、專案、Google Drive 智能整理（業務入口）。
  3. **活動與機會**：限時機會、活動探索。
- 左欄最下方固定「個人化」；只對授權 Owner 顯示「管理中心」及「驗收中心」。群組順序預設上列排序。群組展開狀態可保持在當次操作期間，不要求後端 schema migration。
- 舊深層網址 `/more/notes` 等繼續有效；舊 `/more` 可轉到「個人化」而不是重複清單。既有 Google OAuth callback 使用 `/integrations` URL，必須保留，改由個人化進入而非左欄功能入口。

## 個人化（左欄固定入口）

移除首頁右上角「自訂首頁」，以及「寬螢幕固定左側／手機抽屜」模式選擇。平台按螢幕寬度自動決定，不讓使用者選互斥的導覽模式。

個人化使用四個頁籤，避免原本「先勾選再另外排序」的重複操作：

1. **首頁**：單一卡片清單即可啟閉與排序，動態預覽。只列出產品支援的卡片，缺少權限／資料時遵守既有 loading／empty／error，不虛構資料。
2. **導覽**：顯示固定首頁加 3 格快捷的即時預覽，第 2／3／4 格可直接改選，不能重複；左側三群組和內部功能各自可以移動順序。沿用 `pinned` 與 `more_order`，原有排序依新群組轉換；不再允許首頁／Google 整合進入左欄個人排序。
3. **外觀**：五種視覺風格及系統／淺／深色，選擇後立即套用。外觀目前只保存於該瀏覽器、該帳號的 localStorage，並**不宣稱跨裝置同步**。
4. **服務連結**：目前登入者可分別授權 Google Calendar、Gmail、Google Drive，顯示每項實際連線狀態／重新授權入口。每人自行授權，服務帳號須符合登入 Life 的 Google `sub`／email；不得冒用平台 Owner 授權。普通使用者不顯示開發用的 API Tool/Action 驗收清單。

- **Drive AI 個人同意設定暫不開放**：從個人化與一般使用者功能入口隱藏（包含文件分析同意與 AI 標籤設定的 UI）。維持後端現有 OAuth scopes、授權檢查及 `allow_document_content` 安全保護；絕不因隱藏設定而把 Drive 授權當成同意傳送文件給 AI。後端既有個人資料不可清空。
- 「還原預設」只是編輯預覽，仍須按儲存後才寫入；後端個人偏好維持 revision concurrency 防衝突。新配置與既有 `nav_mode`、`pinned`、`more_order`、`home_cards` API 相容；若可沿用不新增 database schema。

## 五種主題

沿用 Material 3 同一套業務 Widget、API、權限與 responsive 版型；不同主題只改 palette、圓角、陰影、卡片、輕量裝飾與轉場：

- `warm` 暖心日常（既有）
- `fresh` 清新活力（既有）
- `focus` 知性專注（既有）
- `animated` **動畫風格**（新增）：明亮活潑的色彩、圓潤圖示、簡短非循環的微動效與圖形裝飾；**不使用日系動漫、人物插圖、動漫角色或必需的背景圖片**，不依賴未建立的素材。
- `pinkBubble` **粉紅泡泡風格**（新增）：粉彩粉紅／淡紫色、氣泡、柔和圓角／漸層、輕量裝飾；不使用未授權／不存在的圖片。

效能與無障礙：動畫必須尊重 reduced-motion、避免無限循環與全頁背景資源請求；淺色／深色可讀性、320／375／768／1440px 不溢位、任務／日曆／活動來源連結功能不得受主題影響。

## 實作與驗收

涉及 `lib/web/app_shell.dart`、`personalize_page.dart`、`today_page.dart`、`web_app.dart`、`integrations_page.dart`、`visual_system.dart`、必要的 UI/Widget tests；Backend 憑證及 Google OAuth 不因改 UI 而重新發明。先測 Flutter analyze／test／web build，再 GitHub 4 jobs CI，自動 V3 staging-only，核對固定 staging SHA、API rewrite 和 Google 自動化驗收。**只有程式提交不能標 DONE；未驗證的層維持 NOT VERIFIED。**


## 2026-10-12｜主頁標題、刷新與資訊密度修正

- AppShell 只提供單一全域導覽工具列；主功能頁不再各自疊一層純文字 AppBar。每頁以首頁「今日重點」或各功能 LifeFeatureHeader／習慣、購物清單的內容標題作為唯一主標題。表單、子頁、編輯對話可保留其獨立頁名與返回操作。
- 首頁「今日重點」是輕量小型標題列，不應以大面積純裝飾卡擠壓實際內容；待辦「進行中／今天／逾期」統計改為上方緊湊指標，數據仍依真實 API。
- 列表刷新並非後端上游資料抓取：首頁 invalidate 會重取當下待辦／日曆／專案／活動摘要；活動會重取當頁查詢與篩選候選；日曆只重取當月 Google 行程。首頁、活動以 pull-to-refresh 為主，日曆保留有明確功能提示的本月重新讀取按鈕；載入錯誤保留可見重試。習慣／購物仍有 pull-to-refresh。不得聲稱按刷新會觸發所有上游同步排程。
- 限時機會／活動探索：單場次與多場次詳情暨個人操作預設全部收起，使用者自願點開；卡片上的時間／地區／收藏摘要保持可見，原網址、待辦、日曆標記在展開後可用。
- 不增加 UI 強制的人工作業或 OAuth 門檻。Flutter test、CI、Staging SHA、正式部署分層獨立驗收，未取得證據均為 NOT VERIFIED。


## 2026-10-12｜一致的功能標題卡和筆記分類列

- 所有業務主頁（首頁、待辦、日曆、專案、筆記、習慣、購物、限時機會、活動探索、Google Drive）及個人化，都採用同一個 `LifeFeatureHeader`。統一 icon、字級、內距、最低卡片高度與主題；為防小型行動裝置溢位，副標題單行截斷。首頁也不用獨立的巨幅標題卡。正式內容頁不能再額外重複純文字標題。
- 新增操作移入標題卡尾端（手機仍可 FAB）；錯誤和空資料畫面保留有用的功能入口，不以無資料冒充系統正常。
- 筆記分類使用 Header 下方的一列**小字、可水平觸控滑動**分類 Tab，包含「全部」「未分類」與已有分類，立即篩選，手機和桌機都不另開側邊分類或分類底部彈窗；編輯頁／卡片快速修改分類仍保留。
- 此次改版須對照 GitHub 最新 source，Flutter Widget tests、CI、staging、production readback 各自判定 PASS／FAIL／NOT VERIFIED。


## 2026-10-12｜首頁卡片完整清單

「個人化 → 首頁」提供全部 11 個支援項目的顯示勾選與排序：今日待辦、下一個行程、需要關注、今日習慣、精選活動、限時機會、活動探索、進行中專案、筆記、購物清單、Google Drive。`opportunities` 與 `explore` 同時列入 Flutter 選項與後端 `HOME_KEYS` 白名單，回寫及再讀取不得丟失；既有 `events` 繼續相容。首頁「限時機會」使用 `entry=opportunities`、活動探索使用 `entry=explore`，資料無法取得時明示，不虛構公告、日期或活動筆數；只在相關卡片被選用且有權限時才額外向後端讀取。新增卡片預設不強迫勾選，原個人排序與既有預設保持不變。

勾選即表示希望該首頁入口可見：即使今日沒有逾期待辦或習慣清單為空，也要顯示真實的無資料狀態，不得把使用者勾選的卡片悄悄隱藏；Google Drive 卡片不以 Google OAuth 自動代表已同意 AI 文件分析。


## 2026-10-12｜Staging 一般使用者與帳號切換

- Google ID token 驗證與使用者入站權限拆開：正式站依現有 `ALLOWED_GOOGLE_EMAIL` 限制，固定 Staging 只另外允許一個核准的非 Owner 測試帳號；公開原始碼僅保存其正規化 email 的 SHA-256 指紋，不公開明文。
- 額外登入權限只適用 `oauth:staging:` 狀態驗證後的登入與固定 Staging 網域中 `id:staging:` Session；從正式網址夾帶 staging cookie 不得繞過限制。Owner/Admin 仍須比對 `ALLOWED_GOOGLE_EMAIL`，測試者不可使用管理中心或 Owner 功能，使用者資料由 Google `sub` 隔離。
- 個人化頁面上方固定顯示登入帳號及「登出／切換帳號」，即使個人化偏好載入失敗也可登出；`POST /auth/logout` 成功後重載登入畫面、清除舊帳號前端狀態，失敗則回報且不聲稱已登出。Google 登入顯示選擇帳號。
- 真人 Staging 第二帳號實際登入與資料隔離必須獨立驗收；原自動 OAuth redirects/state/cookie 與 production 發布門檻全部保留。

**資料隔離安全閘門**：現有 `notes`／`projects`／`habits`／`shopping_lists` 尚無 `user_sub` 欄位，不能讓第二帳號讀寫這些共享資料。一般 Staging 測試者暫僅允許已檢核為使用者範圍的待辦、Google Calendar/Gmail、個人化設定和授權連結；其他私有功能後端直接 403、前端 feature rollout 標示不可用。待辦舊 `user_sub IS NULL` 僅原 Owner 可見，第二帳號不得引用舊 Project。要開放全部功能，必須另行完成多使用者資料表 ownership migration、關聯與 API 端到端驗證。此限制不能包裝為全功能多人驗收 PASS。

- Gmail 轉待辦也必須設定 `Task.user_sub`，不能建立 `NULL` 擁有者再被 Owner 當成舊資料看到；Staging 測試者的 Gmail 任務與手動任務均按 Google `sub` 隔離。


## 2026-10-12｜一般 Staging 帳號登入後回登入頁（修復）

觀察：Google OAuth callback 完成後，固定 staging 一般帳號仍返回登入頁。根因候選為 Firebase Hosting Cloud Run rewrite 不保證保留 `X-Forwarded-Host`，而 `/auth/me` 只接受固定 Host／Forwarded Host，判錯成 403；原 AuthNotifier 把 403 當無 Session 並不提示錯誤。修正：對已經由驗證 staging OAuth state 核發的獨立 host-only `id:staging:` Cookie，僅在已知 Cloud Run API hostname、HTTPS proxy、沒有明確其他 Hosting Host 且瀏覽器同源 `Referer`／`Origin` 時接受固定 Staging；仍拒絕 production web.app、其他 Cloud Run、跨站來源及自行僞造單獨 staging 前綴。保留 Owner 權限及第二帳號未隔離 API 的 403 防線。前端 403／驗證異常不再靜默顯示一般登入畫面，提供重新驗證與切換帳號入口。這是協助瀏覽器同源識別而非新增登入授權，需真人 staging OAuth round-trip 驗收後才能標 DONE。


## 2026-10-12｜Staging 登入回跳（Firebase pinTag）修復

固定 Staging 在 GitHub V3 Release `#38240040197` 的真實 Hosting rewrite 使用 `run.pinTag=true`，其 Cloud Run 候選 Host 為 `v3-664a32cfc9---life-assistant-api-...a.run.app`。過往 `_fixed_staging_origin` 對候選 Host 的檢查只接受未加 `v3-<SHA>` tag 的 `life-assistant-api-...`，導致第二帳號 OAuth callback 之後 `/auth/me` 被 403 擋住，Flutter 回登入頁。現在以受限的 `v3-[0-9a-f]{10}---life-assistant-api-...a.run.app` 來辨識固定 Staging 的 pinned revision；在 Firebase 省略 `X-Forwarded-Host`、Referer、Origin 時也可核對，明確的 production forwarded host、未加 tag 的一般 Cloud Run 主機與非 staging Session 仍拒絕。CI 中測試正確候選 Host 與負向繞過；真人第二帳號登入仍需重試確認，不把單元測試當真實登入驗收。
