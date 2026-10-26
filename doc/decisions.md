# life_assistant — Current Confirmed Decisions (2026-10-11)

本文件僅保留現行已核准方向；歷史決策見 [archive](archive/decisions_through_2026-10-10.md)。實作狀態以 GitHub main 和 runtime evidence 為準，最高規則見 [PROJECT_RULES](PROJECT_RULES.md)。

## 平台與邊界

- Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL；不破壞已有 SQLite／PostgreSQL 個人資料。
- Life 專案負責 Data、UI、API、Execution、Integration、自己的 Bridge/MCP、權限與 audit；通用 Agent reasoning 由 omniAgent 負責。
- Google 個人資料依帳號獨立 OAuth 與授權；GitHub Actions V3 → public GHCR digest → Cloud Run candidate → gated Firebase Hosting。正式 release 需獨立驗收。

## 活動來源與使用者功能

- **2026-10-26 台灣活動探索排程整併為 Linux systemd 系統排程決策**：
  使用者確認將原本分散在 GAS 快照 (04:30)、外部 AI 探索 (06:00) 與 GAS 觸發 Cloud Run 入庫 (07:30) 的三段分離式排程，整合為由目前 VM 的 Linux 系統級排程（`systemd timer: tw-activity-discovery.timer`，Asia/Taipei 每日 04:00 喚醒，即 UTC 20:00）單一入口啟動，非互動調用 Antigravity CLI (`agy`) 搭載 `Gemini 3.8 Flash (Medium)` 模型。排程獨立於任何對話視窗，依 SOP 循序完成：01快照驗證 → 02全面探索與二輪補漏 → 03候選核證 → 04精選池入池與交接表 READY 輸出 → 04.5 串行觸發 Life 匯入器完成 PostgreSQL 入庫與 ACKED 回寫 → 05回寫統計表與 YYYY-MM-DD.log 結報。停用外部舊 06:00 探索排程與 GAS 07:30 定時觸發器，維持交接表與精選池單一寫入者（Single-Writer）原則。

- **2026-10-12 交接缺值規則（現行，優先於早期『已核證才交接』的敘述）**：`verified_at_tpe` 一律選填，來源未能提供可靠核證時間時保留空白；Life Pydantic 接收為 `None`／持久化 JSON `null`，不可由發現日、交接更新時間或匯入時間補造。來源網址、穩定 `event_key/content_hash`、具名活動與有據活動日／開報節點仍必須具備，待核證據須寫 `evidence_summary`；成功入庫與版本回執門檻不放寬。只有提供核證時間時才驗證 ISO 8601 台北 +08:00 時區。

- 唯一預設交接：ChatGPT 探索／核證 → Drive 精選池 → 獨立交接 Sheet → Life 每日 GCP Job 依永久 event_key/content_hash PostgreSQL 去重、DB commit 後版本一致 ACKED/ERROR。Life 不重啟 crawler、舊 Queue/claim/lease、第二輪 AI；既有 direct API/舊資料留相容。Job／正式 E2E 狀態仍需驗證。[資料契約](curated_sheet_job_ingestion.md)
- **2026-10-16 活動 UX 決策，取代雙入口**：使用者只保留「活動探索」一個導覽／首頁入口，內含「全部活動／限時機會／已收藏」三模式；後端兩種原有 query entry 及 rollout 保留、每主活動僅一張卡片、穩定 parent key 與跨分頁去重。舊 URL 和個人偏好 events/opportunities 相容轉入 explore，不搬移或刪除使用者資料。星等仍全部隱藏。
- 進頁 server-side 依各入口時間接近程度載入 **5 個主活動群組**，再看 **10 筆**；提供「最新收錄」（首次入庫時間）、符合時間語意的一鍵速查、中文一般搜尋（標題／主辦／地點／現有活動摘要）、地區固定映射及精簡篩選；不做 GPS／AI 搜尋。未核實資訊仍顯示未知，不自行推論名額與日期。
- **只保留三個個人操作**：收藏（兩入口共用已收藏篩選）、建立待辦、日曆日期標記。兩者要與現有 Task／Google Calendar 相容並把可靠活動網址帶入；在待辦頁和 Life 日曆頁都能點「前往網址」開活動。日曆資訊標記是全天 transparent、不占 busy、不自動提醒；不能把未知報名或活動日期寫成假時間。
- 活動權限由既有 admin rollout 管理；個人收藏／待辦／日曆依帳號隔離，使用者自行選擇，不自動建立行事曆／待辦、通知／代報名；早期追蹤、預警、確定參與和旅遊候選不再是本期 UI 要求，舊資料/API 先留兼容。**唯一詳細且具待辦與日曆相容性差異的規格**：[活動 UX V3](curated_activity_user_features.md)。

## 管理與現況

- 管理員只管共用精選活動、功能 rollout、Life 內部 Drive AI Provider，不代替使用者操作私人 Google 資料；使用者可設定導覽與首頁卡片。
- 上述 UX V3 為**產品規格**而非已完成程式；工作清單看 [TODO](todo.md)，實際 release/runtime 看 [CURRENT_STATE](CURRENT_STATE.md)。不因文件完成宣稱產品驗收 PASS。
