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
