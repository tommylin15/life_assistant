# life_assistant — Active TODO

最後更新：2026-10-07

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #7 — Shopping 完整產品化

狀態：**NOT STARTED**。#6 Habits 已封板；Drive Knowledge #54 regression 亦已由 release `3b75e9e...` / Runtime Acceptance #59 PASS 關閉。下一步檢查既有 Shopping backend / UI / tests，完成可操作 vertical slice 與 mobile / desktop acceptance。

## Just Closed

### #6 — Habits 完整產品化

狀態：**DONE / PASS**；closure progress **6/11 = 54.5%**。

- release `02eda1124885846f41ca32ca185d9e1a5a5ebfe1`；CI #558、Firebase #376、Cloud Run #430、Habits UI #7、Post-deploy Runtime #96 PASS。
- Follow-up cross-feature Drive Knowledge #54 曾 FAIL；修正版 release `3b75e9e288be0d2179cd381281b55210a14ad875` 的 CI #562、Cloud Run #434、Post-deploy #100、Drive Knowledge #59 / run `37595859159` 全 PASS，regression 已關閉。
- 詳細 evidence 見 `progress.md`、`acceptance.md`、`integrations.md`。

## Next

1. #7 — Shopping 完整產品化。
2. #8–#9 — Calendar / Activity + Integrations productization。
3. #10 — Integration / foundation tail closure。
4. #11 — Phase 1 final Release Gate / 封板 checkpoint。

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
