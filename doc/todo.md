# life_assistant — Active TODO

最後更新：2026-09-28

> 本檔只保留**目前 active / next / non-blocking backlog**。正式執行順序以 `phase1_delivery_order.md` 為準；完成狀態與 runtime evidence 以 `acceptance.md` 為準。不要再在本檔維護另一套歷史完成清單或 release evidence snapshot。

## Current

### 1. Cloud mutation idempotency 收尾

- action-id idempotency implementation baseline 已進 `main`（commit `470d54c236286dc364fd920cc52e79deee685c09`）。
- 確認 migration / CI / deployment / runtime acceptance evidence 完整。
- evidence 完整前，產品層不得自行標示 DONE。

## Next — UI-critical foundation

### 2. Authorization / minimum-permission + destructive/sensitive policy 核心版

- Backend authorization / minimum-permission baseline。
- 共用 destructive / sensitive action policy gate。
- Calendar delete confirmation 作為既有 reference pattern，不重做。
- 只先完成 Phase 1 主要 UI 直接依賴的 policy，不要求先完成所有未來 MCP / Agent policy。

### 3. Checklist Cloud 主線

- PostgreSQL persistence。
- Backend/API contract。
- tests / CI / deployment / runtime evidence。
- Flutter Web 可直接使用的 checklist path。

## Next — UI Vertical Slice A

### 4. App Shell

- Tasks
- Projects
- Notes
- Habits
- Shopping
- Calendar
- Integrations / Settings
- mobile / desktop responsive shell

### 5. Task 完整 UX

- create / edit / complete / delete
- due date / time
- priority
- reminder
- tags
- project
- checklist
- loading / empty / error / data states
- mobile + desktop UX acceptance

### 6. Project UX

- project list
- create / edit / delete
- linked Task visibility / relation flow
- delete guard 的可理解錯誤呈現
- mobile + desktop UX acceptance

## Then — UI Vertical Slice B

1. Notes；同批補 full-text search。
2. Habits。
3. Shopping。
4. Calendar 一般使用者 read/list/create/update/delete UI。
5. Activity / Execution Log 與 Integrations 的使用者可理解呈現。

## Non-blocking backlog

以下仍需完成，但不再阻塞前述 UI vertical slices，除非成為直接 dependency：

- Attachment central storage/reference strategy；在附件 UI 開工前收斂。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。

## Product DONE 規則

使用者功能至少要同時具備：

1. implementation
2. tests
3. CI
4. deployment
5. runtime / integration
6. UI entry + 可操作 flow
7. mobile / desktop UX acceptance

Backend-only PASS 可標 foundation PASS，但不能等同產品功能 DONE。
