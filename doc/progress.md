# 生活助理 App v0.1 — 開發進度摘要

最後更新：2026-10-01

目前狀態：**Phase 1 = PARTIAL。**

> 本檔只提供人類可快速閱讀的 rollup，不取代 `acceptance.md`、CI、deployment 或 runtime evidence。最新 PASS / FAIL / NOT VERIFIED 與 release evidence 仍以 GitHub `main` + runtime evidence 為準；目前開發先後順序請以 `phase1_delivery_order.md` 為準。

## Phase 1 全案封板進度表 — 剩餘 11 個工作包

### 百分比規則

- 封板進度 = `已 DONE 工作包 / 11`。
- 只有完整通過該工作包 exit condition 才打 ✅ 並納入百分比。
- `IN PROGRESS`、`PARTIAL`、`NOT VERIFIED` 都不算完成。
- 每完成 1 個工作包，封板進度增加約 **9.1%**。
- 這個 11 包百分比衡量的是 **2026-10-01 checkpoint 之後的剩餘 Phase 1 封板工作**，不是整個專案從第一天開始的歷史投入比例。

### 目前總覽

- **Completed packages：0 / 11**
- **Closure progress：0.0%**
- **Current package：#1 — 完成 Task 6：Drive / Notes 共用 Tag**
- **Current state：PARTIAL / IN PROGRESS**
- **Next checkpoint：#1 DONE 後 = 1/11 = 9.1%**

| # | 工作包 | 狀態 | DONE 條件 / 目前 gate |
|---|---|---|---|
| 1 | 完成 Task 6 — Drive / Notes 共用 Tag | 🟡 IN PROGRESS | Backend Tag service / Drive Tag API 已 GREEN；剩 Drive 卡片 Tag 編輯/顯示 + Project 關聯文件 Tag 顯示，需 Flutter tests / Web build / CI PASS |
| 2 | 全專案 Design System / UI Style Checkpoint | ⬜ NOT STARTED | 核准全站視覺方向；固定 design tokens、共用元件、mobile/desktop responsive 規則，並建立既有/新頁面採用基線 |
| 3 | Task 7 — provider-agnostic AI enrichment | ⬜ NOT STARTED | 智能 Tag、候選 Notes、雙鏈建議、privacy/consent/cache/provider abstraction，backend tests GREEN |
| 4 | Task 8 — 智能整理 review UI | ⬜ NOT STARTED | 建議檢視、接受/拒絕、AI 狀態、consent UX、manual fallback，Flutter suite / Web build GREEN |
| 5 | Task 9 — Drive Knowledge 正式交付與 production acceptance | ⬜ NOT STARTED | CI、migration、Firebase、Cloud Run、authenticated runtime、真實 Drive integration evidence PASS |
| 6 | Habits 完整產品化 | ⬜ NOT STARTED | 完整 vertical slice：implementation、tests、CI、deployment/runtime、可操作 UI、mobile/desktop acceptance |
| 7 | Shopping 完整產品化 | ⬜ NOT STARTED | 完整 vertical slice：implementation、tests、CI、deployment/runtime、可操作 UI、mobile/desktop acceptance |
| 8 | Calendar 完整產品化 | ⬜ NOT STARTED | 一般使用者 read/list/create/update/delete UX + true-account verification + 完整 vertical-slice evidence |
| 9 | Activity / Execution Log + Integrations 完整產品化 | ⬜ NOT STARTED | 使用者可理解的 Activity / Integration UI + 所需 runtime/integration evidence |
| 10 | Integration / Foundation 尾項收尾 | ⬜ NOT STARTED | Attachment strategy；Bridge/MCP contract；true provider failure / partial-success；Calendar true-account read/list 重驗；historical SQLite migration 僅在 source 存在時執行 |
| 11 | Phase 1 Final Release Gate / 封板 checkpoint | ⬜ NOT STARTED | Implementation / Tests / CI / Deployment / Runtime / Integration / UI flow / mobile+desktop acceptance 證據完整；Drive checkpoint 回寫；Phase 1 才標 DONE |

### 固定回報格式

之後只要問「做到哪裡」，固定回報：

1. `Completed packages: X/11`
2. `Closure progress: Y%`
3. `Current package: #N — 名稱`
4. `Current state: PASS / FAIL / PARTIAL / NOT VERIFIED`
5. `Next concrete gate`

### 已完成但不重複計入這 11 包的歷史主線

以下已在較早 checkpoint 關閉，不重複放入 11 包分母：

- Idempotency
- Authorization / minimum-permission + destructive policy core
- Checklist Cloud
- App Shell
- Task complete UX
- Project UX
- Notes / full-text-search baseline
- Drive Knowledge Task 1–5

## 已建立的主要平台能力

目前 `main` 已具備並經不同層級驗證的核心基線包括：

- Firebase Hosting → Flutter Web / PWA。
- Cloud Run FastAPI Backend。
- PostgreSQL operational source of truth。
- Google identity / protected API baseline。
- Task Cloud CRUD + Web interaction path。
- Project Cloud CRUD、relation guard 與 Gmail → Project。
- Note / Habit / Shopping / Template Cloud API + persistence baseline。
- Gmail metadata + Gmail → Task / Calendar / Project。
- Calendar read/create/update/delete API。
- Drive Bridge ensure compatibility path。
- unified error envelope + request id。
- execution / activity log、failure / partial-success semantics。
- SQLite → PostgreSQL deterministic backfill tooling與 synthetic success/failure runtime gate。
- Calendar destructive confirmation baseline。
- action-id idempotency implementation baseline。
- shared immutable backend image / Artifact Registry cleanup strategy baseline。

上述「平台能力存在」不等於所有產品 UI 已完成；各項真正完成狀態仍以 `acceptance.md` 的 evidence 層級為準。

## 文件與 evidence 分工

- `phase1_delivery_order.md`：目前執行順序。
- `progress.md`：人類可讀的 rollup + 11 包全案封板進度表。
- `todo.md`：active / next backlog。
- `acceptance.md`：逐項 completion truth 與 release evidence。
- `release_checklist.md`：Phase 1 final release gate。
- `wbs.md`：scope decomposition，不代表排程。
- 歷史 batch progress 文件：保留稽核價值，不再當 current status。

## 下一步

目前固定下一步：

1. 將 Task 6 的 Drive Tag UI / Project Tag UI 從 RED 轉 GREEN。
2. Task 6 完整 CI / Web build PASS 後，工作包 #1 打 ✅，封板進度更新為 **1/11 = 9.1%**。
3. 進入工作包 #2：全專案 Design System / UI Style Checkpoint。
