# life_assistant — Active TODO

最後更新：2026-10-08

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### CI/CD V2 — active user-requested infrastructure work

**RESUMED / OPEN / NOT CLOSED**. Cloud Build 2nd Gen main push CI only; explicit
full-SHA manual Release → candidate/Preview → real acceptance → live/post-deploy.
Runbook: `deployment_runbook.md`. True main-push and manual Release evidence,
cost comparison, owner isolation and all existing provider/UI gates remain
mandatory. No scheduler timing changes; no OmniAgent/Janus implementation work.

暫停 checkpoint：Release `af461348-13ee-4f43-833a-428f06f4e813` CANCELLED；
Candidate `00174-luw` 0%，正式 `00173-gpf` 100%。Migration 與四項 core
execution 已 PASS；Firebase Preview/Live、其餘 runtime/UI/provider gates 與
cleanup 尚未完成。詳見 `acceptance.md` 最後 checkpoint。2026-10-08 使用者已要求接續
CI/CD V2；本輪先補後端單獨變更的 Candidate Preview 安全契約。新的 Push CI、
完整 SHA manual Release、GCP 殘留 execution/readback、Preview/Live 與 providers
均須重新取證；不得把歷史 PASS 當成此次 release PASS。

### Paused after #7 — per user instruction

狀態：**#7 Shopping = DONE / PASS；7/11 = 63.6%**。本對話不啟動 #8。

獨立 cross-feature health：歷史 #63 / run `37625447402` exit `91` = Gemini only；更新一輪 #70 / run `37702785541` exit `93` = Gemini + OpenRouter，Groq 不在 failure mask。此項保持 OPEN，不影響 #7 的直接完成證據。Diagnostic candidate `8dedf655` 已加入分別測試，CI #574 PASS；新 deployment / live acceptance 尚待驗證。

## Just Closed

### #7 — Shopping 完整產品化

狀態：**DONE / PASS**；closure progress **7/11 = 63.6%**。

- final release `1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d`。
- CI #566 / run `37621843816`、Firebase #384 / run `37622140411`、Cloud Run #438 / run `37622140547`、Shopping UI #4 / run `37622504893`、Post-deploy Runtime #104 / run `37624483194`：PASS。
- Shopping list/create item/category/toggle/progress、responsive UI、More navigation、mobile/desktop production acceptance、真實 PostgreSQL persistence evidence 完整。
- 詳細 evidence 見 `progress.md`、`acceptance.md`。

## Next

1. #8 — Calendar 完整產品化：**NOT STARTED；新對話才開始**。
2. #9 — Activity / Execution Log + Integrations productization。
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
- Drive Knowledge provider-health regression：#63 exit `91`（historical Gemini-only），#70 exit `93`（Gemini + OpenRouter），均仍為歷史 FAIL evidence。Codex-first consumer adapter 已在 main 送 CI/runtime 驗收，completion 為 PARTIAL。只呼叫 omniAgent 私有 shared Cloud Run；其認證由共用服務專屬 `omniagent-shared-codex-auth` 管理，life_assistant 不新建、不讀取、不複製任何 Codex Secret，舊 `janus-mart-codex-auth` 不作為消費端來源。

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
