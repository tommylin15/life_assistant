# life_assistant Phase 1 — Delivery Order

最後更新：2026-10-07

> 本文件定義 Phase 1 後續的**執行順序**。`doc/acceptance.md` 與 `doc/release_checklist.md` 繼續定義完成條件與 Release Gate；本文件只負責「先做什麼、後做什麼」。若本文件與較舊文件的隱含先後順序不同，以本文件的執行順序為準，但不得因此降低既有 acceptance / security / migration 要求。

## Current closure checkpoint — 2026-10-07

2026-10-01 之後的 Phase 1 closure 以 `doc/progress.md` 的 11 個工作包為目前執行序；本文件後續各節保留原始 vertical-slice delivery rationale，不再被解讀成另一套平行進度表。

目前：
- Completed packages：**5/11 = 45.5%**。
- Just closed：**#5 — Task 9 Drive Knowledge 正式交付與 production acceptance，DONE / PASS**。
- Current package：**#6 — Habits 完整產品化，NOT STARTED**。
- exact release SHA `2d08118a13c71c6fec97e8bfba0857b861eefd1e`；CI #551、Firebase #369、Drive Knowledge #47 final mandatory gate PASS。
- Picker production config、Gemini / Groq / OpenRouter 真實 API、真實 Picker-selected Drive fixture、synthetic runtime、production desktop/mobile UI 均 PASS。
- Cloud Run #423 PASS；ready revision `life-assistant-api-00154-xrt` 與末端回歸驗收均完成。
- 封板 evidence 與 secret / fixture 設定見 `acceptance.md`、`integrations.md`；Phase 1 整體仍 PARTIAL。

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
