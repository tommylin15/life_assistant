# Life — Active TODO (2026-10-10)

## 本批開發與驗收安排（2026-10-10 最新）

- 新交接表、穩定去重、活動卡片、兩個入口及個人動作已在工作樹實作；開發驗證與 deployed／runtime 驗收分開記錄。細節見 [活動規格](curated_activity_user_features.md)。
- 活動能否開放一般使用者由 admin 在後台設定。AI 管理補強暫緩，僅 AI 管理相關能力限 admin；不把這項限制套用到全部新功能。
- 下一輪合併新活動功能、後台及個人首頁做正式上線驗收。真實 Sheet write scope／版本回執、GCP Job、Google Calendar 與新 SHA 的 CI／staging 尚待驗證；舊版測試站登入已完成。


## 測試站驗收更新（2026-10-10；優先於下方歷史快照）

- **固定測試站發布與真實 owner Google 登入驗收：PASS / 已完成。** [V3 run 38030697455](https://github.com/tommylin15/life_assistant/actions/runs/38030697455) 的 real database/auth、Preview、fixed staging preflight，以及「Promote exact Preview to independent fixed staging live and verify owner OAuth」均 success。使用者於本次對話確認 https://life-assistant-v3-stage-tl15.web.app 已能正常登入使用。
- 測試站 `release.txt` 實際讀回 `3fb06169ad01a065fef60eecc2010c459970746e`，與上述成功發布 SHA 一致。先前 wrong_callback、Missing session 與未驗收敘述是修復前歷史，不再列為目前登入 blocker。
- **後續版本發布是獨立狀態：** main `4219510cf2764c7b7bce9286ec2374d9ca36a1df` 的 CI success，但 [run 38037092043](https://github.com/tommylin15/life_assistant/actions/runs/38037092043) 在 real database/auth acceptance failure，尚未執行 Preview 或固定 staging 發布。不可據此把既有可用測試站改標 FAIL；也不可把測試站已驗收推定為最新 main 或 production 已發布。
- 下一步仍是新交接 Sheet → Life Job → PostgreSQL → ACK/ERROR 的實作與真實驗收，以及活動產品待辦；不要求重做已完成版本的測試站登入驗收。

**Release status PARTIAL.** P0/P1 implementation foundations are in main; production E2E acceptance is NOT VERIFIED.

| Priority | Task | Status |
|---|---|---|
| P0 | Dedicated curated table, bounded ChatGPT batch POST, HTTPS validation, idempotent upsert, signed-in GET | Implemented in source; ephemeral PG CI PASS on previous candidate; production NOT VERIFIED |
| P0 | Flutter curated UI, category/region/date/server filters, 1–5 stars, cost/benefit and registration unknowns | Basic list and city/star UI implemented; comprehensive device verification NOT VERIFIED |
| P0 | Drive 交接表 READY → Life GCP Job 讀取 → event_key/content_hash PostgreSQL upsert → Sheet ACKED/ERROR、30天保留、owner/Flutter readback | **APPROVED / NOT VERIFIED**；既有 direct API 僅相容 |
| P1 | Owner curated summary/errors and global feature rollout | Baseline source implemented; full error dashboard and controlled public rollout incomplete |
| P1 | User personal bottom/rail/drawer and Home layout/card preferences | Source implemented; real device and accessibility acceptance NOT VERIFIED |
| Deferred | Drive AI admin provider allowlist/pause, health and usage | 既有 admin source 保留；補強與 provider／budget 驗收暫緩，不阻擋一般功能上線 |
| Acceptance | Exact main SHA CI and new release API/DB/UI/handoff/rollback | Staging release + true owner OAuth PASS for 3fb0616; main 4219510 CI PASS, subsequent release DB/auth FAIL; new handoff/production acceptance outstanding |
| Operations | Read-only GCP old external Source Job/Scheduler status | Cloud Run Job exists per inventory #38012860019; Scheduler in `us-central1` **PASS (no matching jobs)** per #38013575831; other-region/external callers NOT VERIFIED |

| P1 product | One-parent event card grouping distinct offers/sessions; two user entries 限時機會／活動探索 with overlapping membership, evidence-aware advance-opening display and original links | **SOURCE IMPLEMENTED / runtime NOT VERIFIED** — [canonical spec](curated_activity_user_features.md) |
| P1 data/API contract | Stable event_key and parent/offer grouping, opening times, evidence and refundable deposit semantics via additive 0016 migration | **SOURCE IMPLEMENTED / 本機 PostgreSQL PASS；release DB NOT VERIFIED** |
| P1 personal actions | Opt-in account-owned watchlist, Task, Calendar information marks versus registration reminders versus confirmed schedule; group duplicate alerts and keep users isolated | **SOURCE IMPLEMENTED / 真實 Calendar NOT VERIFIED**；提醒為 Calendar popup |
| Future | Travel itinerary candidate handoff from curated events and accepted registrations | **DESIGN EXTENSION ONLY / NOT IMPLEMENTED** |

**CANCELLED, not pending**: Life 端 MoC/TDX/EventGo/yii 來源 crawler、舊來源 Excel scanner、Queue/claim/lease、第二輪 AI、舊來源14天驗收、額外發布閘。**新 Sheet ACKED 是匯入回執，不是舊 Queue ACK。** 保留 legacy migrations/data。

Follow [consolidated P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md).
