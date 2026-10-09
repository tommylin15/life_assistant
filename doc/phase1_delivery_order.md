# life_assistant Phase 1 — Delivery Order

最後更新：2026-10-09（Calendar #8 封板 8/11；台灣免費活動 M0 開始排程）

> 本文件定義 Phase 1 後續的**執行順序**。`doc/acceptance.md` 與 `doc/release_checklist.md` 繼續定義完成條件與 Release Gate；本文件只負責「先做什麼、後做什麼」。若本文件與較舊文件的隱含先後順序不同，以本文件的執行順序為準，但不得因此降低既有 acceptance / security / migration 要求。

## 2026-10-09 使用者指定優先級 — Calendar 之後優先交付免費活動探索

**明確授權的優先級變更：Calendar 工作包 #8 已於 2026-10-09 以完整證據 DONE/PASS，下一個第一優先產品項目是「台灣免費活動探索與報名追蹤」（Post-Calendar P0），在既有 #9 Activity / Integrations、#10 Integration / Foundation tail、#11 Final Release Gate 的新增產品開發工作之前安排。** 原本 #9–#11 未取消；本功能的工作包另列，不直接更動原 11-package 完成分子或分母，不能因文件更新宣稱 #8 或新需求已完成。

- 正式產品/工程規格：[`taiwan_free_events_discovery_plan.md`](taiwan_free_events_discovery_plan.md)，已統一最小 DB／精簡卡片／增量 Batch AI／M0–E2 驗收；共用 AI 路由的單一政策見 [`ai_provider_policy.md`](ai_provider_policy.md)。
- 第一線官方 RSS、新聞稿、主辦網站、報名頁與合法接入的活動網站：每 12 小時（Asia/Taipei 06:00、18:00）；文化/觀光官方 API 每日補充；data.gov.tw 目錄每日只負責發現/維護來源，不作為活動即時性依據。
- 先查證是否真正免費、是否仍有效、報名起訖時間；不可從活動日期猜測報名時間。聚合站需核對來源和授權。資料持久去重、重要變更通知、過期後禁用；預設活動結束後 30 天清除非必要內容但保留最小去重紀錄及使用者自行建立的資料。
- 一般使用者可獨立決定加入提醒、待辦、筆記與指定筆記資料夾；來源監控/健康只給 authenticated admin，沿用既有 Flutter UI 與 FastAPI RBAC、不建立專用後台；admin email 仍待核實。
- ChatGPT 的 06:00/18:00 掃描**只是暫時過渡**；正式目標是 Cloud Scheduler → Cloud Run → PostgreSQL → Flutter Web，真實 GCP 驗收通過後才停用過渡任務。
- **階段與 Gate**：M0 來源合法性/14 天新鮮度基線 → M1 掃描/活動－場次－報名機會/去重與安全 → M2 一般使用者候選清單＋現有 UI 的 admin-only 來源健康 → M3 三種獨立個人動作/提醒與真實整合 → M4 Cloud Scheduler/Cloud Run 正式切換；以上 **M0–M4 屬 MVP 必要驗收**。其後 E1 第一版增強（主辦追蹤、進階偏好、摘要/通知控制）、E2 第二階段（貼連結、交通距離、電子報/推薦）。詳細驗收見產品規格 §9–§13。
- **資料模型先行的必要決策**：同一活動下需分場次 Session 和報名機會 Registration Opportunity（窗口／票種／免費條件／候補）；精確報名時刻未知須保留未知，報名時間待公布可追蹤；主辦單位 Organizer 留可持續的身份關聯。必須在 migration 前評審。
- 此次只變更開發順序與設計；既有 Phase 1 release scope freeze / 必要驗收不能被文件默默取消。開始實作時必須明確記錄對 #9–#11 排程與 release gate 的影響。此功能 **APPROVED PLAN / NOT IMPLEMENTED**。

## Current closure checkpoint — 2026-10-09

2026-10-01 之後的 Phase 1 closure 以 `doc/progress.md` 的 11 個工作包為目前執行序；本文件後續各節保留原始 vertical-slice delivery rationale，不再被解讀成另一套平行進度表。

目前：
- Completed packages：**8/11 = 72.7%**。
- Just closed：**#8 — Calendar 完整產品化，DONE / PASS**（CI 37882690249；V3 37882875014；Firebase 37885328134；Google True Account 37885330178；Calendar UI 37885544932；同一 SHA `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7`）。
- Current priority：**台灣免費活動探索 M0 來源合規/新鮮度基線，NOT IMPLEMENTED / NOT VERIFIED**。
- #6 final release SHA `02eda1124885846f41ca32ca185d9e1a5a5ebfe1`；CI #558、Firebase #376、Cloud Run #430、Habits UI #7、Post-deploy Runtime #96 PASS。
- Habits production desktop/mobile list/create/edit/complete/history、真實 PostgreSQL cloud-domain runtime 與 release-level post-deploy regression均 PASS。
- Cross-feature health：latest-release Drive Knowledge #54 為 FAIL（live external AI production acceptance）；不回滾 #6 closure，但在 final release gate 前必須重新收斂。
- #6 封板 evidence 見 `acceptance.md` 與 `habits_productization_checkpoint_v0_1.md`；Phase 1 整體仍 PARTIAL。

測試、CI/CD、deployment、acceptance 遇到卡住時，依 `recovering-stuck-ci-deploys` 先分類 queued / silent-but-bounded / timeout-failure / workflow-chain break，再決定是否 retry；不以重跑取代 evidence。

## 原則

- 不再採「所有底層項目清零後才開始 UI」的順序。
- 先收斂會直接影響 UI contract、資料一致性或高風險操作的 foundation，之後立刻進入 UI vertical slice。
- 非 UI-blocking 的 Bridge/MCP 完整化、真實 provider failure、歷史 SQLite migration、附件完整策略，不得無限期阻塞主要產品 UI。
- 使用者功能不能只因 API、CI 或 deployment PASS 就標示 DONE；至少要有可到達的 UI entry、可操作 flow，以及相應的 mobile/desktop browser acceptance，才可視為產品層 DONE。
- Foundation 與 UI 仍各自保留 PASS / FAIL / NOT VERIFIED evidence，不以畫面存在取代 backend/runtime 驗證，也不以 backend PASS 取代 UX 驗收。

## 現行執行順序

### 1. 收尾 Cloud mutation idempotency

目的：避免重試、連點或網路重送造成重複 mutation，先固定 UI 之後會依賴的 mutation contract。

目前狀態：

- `470d54c236286dc364fd920cc52e79deee685c09` 已加入 action-id idempotency baseline、migration 與 runtime acceptance job。
- 後續以目前 `main`、CI、deployment、runtime evidence 為準，不重做已完成實作。
- 完成此項後才將 Cloud mutation idempotency 標記為 PASS；若只有 implementation 而 runtime evidence 不完整，維持 PARTIAL / NOT VERIFIED。

### 2. 收斂 authorization / minimum-permission + destructive/sensitive policy 核心版

目的：讓主要 UI 在開始擴張前，已經知道哪些 action 可執行、哪些 action 必須 explicit confirmation，以及拒絕/權限不足的 error contract。

範圍只做會影響 Phase 1 主要 UI 的核心 policy：

- Backend authorization / minimum-permission baseline。
- destructive / sensitive action 共用 policy gate。
- 既有 Calendar delete confirmation 視為已建立的 reference pattern，不重做。

不要求先把所有未來 MCP/Agent policy 完整化。

### 3. Checklist Cloud 主線

目的：在 Task UI 擴充前補齊 Task 詳情頁直接依賴的 checklist cloud path。

完成標準包含：

- Backend / PostgreSQL persistence。
- API contract。
- tests / CI / deployment / runtime evidence。
- 可供 Flutter Web 主線使用。

### 4. UI Vertical Slice A — App Shell + Task 完整 UX + Project UX

這是下一個主要產品交付階段，不再先等待其餘 foundation 全部完成。

#### 4.1 App Shell

建立主要產品 navigation / responsive shell，至少讓下列已完成或即將完成的 domain 有正式入口：

- Tasks
- Projects
- Notes
- Habits
- Shopping
- Calendar
- Integrations / Settings

#### 4.2 Task 完整 UX

把既有 Task backend 能力從最小列表提升到可日常使用：

- create / edit / complete / delete
- due date / time
- priority
- reminder
- tags
- project
- checklist
- loading / empty / error / data states
- mobile + desktop responsive acceptance

#### 4.3 Project UX

- project list
- create / edit / delete
- linked Task visibility / relation flow
- delete guard 的使用者可理解錯誤呈現
- mobile + desktop responsive acceptance

### 5. UI Vertical Slice B — 已完成 Cloud Domain 逐一產品化

原則：做到哪個 domain，就補該 domain 真正需要的剩餘 backend，而不是先把所有 backend feature 一次補完。

建議順序：

1. Notes；同批補 Notes full-text search。
2. Habits。
3. Shopping。
4. Calendar；補完整一般使用者 read/list/create/update/delete UI。
5. Activity / Execution Log 與 Integrations 的使用者可理解呈現。

### 6. 次要 foundation / integration 收尾

以下項目保留，但不再阻塞前述 UI vertical slices：

- Attachment central storage/reference strategy；在實際開始附件 UI 前收斂。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy source file 可定位時執行，不以缺少 source 阻塞 UI。

## Delivery Gate 調整

從本文件生效後，Phase 1 的產品功能採 vertical-slice 完成判定：

1. implementation
2. tests
3. CI
4. deployment
5. runtime / integration
6. UI entry + 操作 flow
7. mobile / desktop UX acceptance

只有與該功能相關的證據完整，才可標示 DONE。Backend-only PASS 可以保留為 foundation PASS，但不能等同產品功能 DONE。

## 與既有文件的關係

- `doc/acceptance.md`：完成條件與 evidence truth。
- `doc/release_checklist.md`：Phase 1 release gate。
- `doc/decisions.md`：長期架構與 scope 決策。
- 本文件：目前後續開發執行順序。

若 GitHub implementation/runtime 與本文件描述的狀態不同，仍以 GitHub implementation/runtime evidence 為準，並更新本文件，不以規劃文字覆蓋實際狀態。
