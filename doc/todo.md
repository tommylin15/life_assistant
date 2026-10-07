# life_assistant — Active TODO

最後更新：2026-10-07

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #6 — Habits 完整產品化

狀態：**NOT STARTED**。下一步先檢查既有 backend / UI / tests，完成可操作 vertical slice 與 mobile / desktop acceptance。

## Just Closed

### #5 — Task 9：Drive Knowledge 正式交付與 production acceptance

狀態：**DONE / PASS**；closure progress **5/11 = 45.5%**。

- release `2d08118a13c71c6fec97e8bfba0857b861eefd1e`；Drive Knowledge #47 / run `37568734572` final mandatory gate PASS。
- Picker、三個 live AI provider、真實 Drive fixture 與 production UI 全 PASS；完整 release / secret / fixture evidence 見 `acceptance.md`、`integrations.md`。

## Next

1. #6–#9 — Habits / Shopping / Calendar / Activity + Integrations productization。
2. #10 — Integration / foundation tail closure。
3. #11 — Phase 1 final Release Gate / 封板 checkpoint。

## Non-blocking backlog

以下仍需完成，但只有在成為直接 dependency 或進入對應工作包時才提升優先級：

- Attachment central storage/reference strategy。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。

## Product DONE 規則

使用者功能至少要依工作包需求具備：

1. implementation
2. tests
3. CI
4. deployment
5. runtime / integration
6. UI entry + 可操作 flow
7. mobile / desktop UX acceptance

Backend-only PASS 可標 foundation PASS，但不能等同產品功能 DONE。
