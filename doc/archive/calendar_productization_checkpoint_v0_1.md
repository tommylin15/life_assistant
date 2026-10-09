# Calendar Productization Checkpoint v0.1 — Package #8

日期：2026-10-08  
狀態：**DONE / PASS（2026-10-09 final addendum supersedes earlier checkpoints）**  
Phase 1 completed packages：**8 / 11（72.7%）**；#8 已列入。

## Scope / implementation candidate

- 正式 Flutter route：`/calendar`，移除 placeholder。
- Backend 現有 Google Calendar `/integrations/google/calendar/events` list/create/update/delete API 不重做；前端僅透過 FastAPI ApiClient 存取，不儲存 OAuth credentials。
- UI：月份/指定日期瀏覽、時段與全天行程顯示、建立／修改時段行程、刪除二次明示確認、Google 未連線提示、loading/empty/error/retry、手機與桌面版。
- Timezone：新建／編輯時間序列化為 UTC RFC3339 `Z`；全天 `date` 用本地 civil date 呈現且 `end.date` 為 exclusive。
- 不強制把全天既有行程轉成時段事件；全天事件目前支援檢視與刪除，編輯需在後續契約擴充，不得無聲變更其語義。
- Google Cloud account/provider failure 不得被 UI mock 偽裝成真實讀取 PASS。

## Mandatory acceptance gates

| Gate | Status | Evidence |
|---|---|---|
| Implementation | PARTIAL | Calendar API facade + Flutter page + `/calendar` route candidate |
| Widget / contract tests | PASS | CI #578; Calendar widget and backend contract tests |
| CI Flutter analyze / tests / build | PASS | CI #578 / run 37709427943 on candidate 1a78749 |
| Firebase release | NOT VERIFIED | #395 PASS older candidate; latest #396 in progress |
| Cloud Run API / permission / runtime | NOT VERIFIED | #449 previous candidate in progress; latest #450 pending |
| Production desktop UI | NOT VERIFIED | #2/#3 FAIL due old Flutter semantics locator; correction at 1a78749 pending new acceptance |
| Production mobile UI | NOT VERIFIED | Same workflow; overflow and navigation |
| Real Google account Calendar read/list | NOT VERIFIED | #1 skipped after previous Cloud Run cancellation; awaiting live read on successful deployment |
| Destructive confirmation | NOT VERIFIED | Flutter confirm dialog, confirmed header; runtime enforcement requires validation |
| #63/#70 Drive Knowledge AI | FAIL (independent) | Gemini/OpenRouter regression; not a #8 hard blocker |

## Closure rules

Package #8 **cannot** be marked DONE until tests, CI, deployment, runtime/integration, desktop/mobile production UI, and true-account Calendar read/list validation all have verifiable evidence. A mocked Playwright provider validates UI flows only, not Google API account access. Do not increment 7/11 prematurely.

## Known gap

Google all-day edit (preserving `date` rather than converting to `dateTime`) is not yet implemented. Resolve before claiming fully comprehensive Calendar CRUD for all event types, or explicitly scope acceptance to timed event mutations and surface all-day limitation to users.

## Live Calendar read/list runner

- `backend/scripts/run_calendar_true_account_read_acceptance.py` calls the real Google Calendar events API using existing encrypted owner-scoped OAuth credentials injected by Cloud Run; read-only and no event mutation.
- The runner logs PASS / FAIL / NOT_VERIFIED plus aggregate count, never event text, user sub, or token.
- To avoid arbitrary owner selection, missing or multiple connected Calendar owners produce NOT_VERIFIED (exit 2) rather than a fabricated PASS.
- Workflow reuses `life-assistant-core-acceptance` Cloud Run Job after successful Cloud Run deployment; it does not create another long-lived job.


2026-10-08 checkpoint update
- CI #575 FAIL: Flutter create/edit timing. Split tests without removing behavior, CI #576 PASS, #577 PASS, #578 PASS.
- Production Calendar UI #2 FAIL exact semantic label locator despite visible rendered UI; #3 used older script and failed. Fix commit 1a787494fecdecba33a8a231be1b22375d23b870 awaiting fresh production UI evidence.
- Firebase #394 and #395 PASS older commits; exact latest SHA #396 NOT VERIFIED while deploying.
- Cloud Run #448 cancelled because superseded. #449 in progress; #450 pending. Runtime and true Google account read remain NOT VERIFIED.
- #63 and #70 Gemini/OpenRouter AI regression OPEN/FAIL, excluded from Calendar-specific gates per user decision.
- Package #8 remains PARTIAL; completed packages 7/11 = 63.6%.

## 2026-10-08 Calendar #8 continued diagnostics

- Exact release `84e9246b29659c6f11bcf71778af40fa3c4f7366`: CI #579 PASS, Firebase #397 PASS, Cloud Run #451 / run 37710888617 PASS (migration, cloud-domain, checklist, idempotency, Google provider failure-path, SQLite normal/failure).
- Calendar UI #5 / run 37711145190 FAIL **after** month/all-day PASS, create/timezone PASS, update PASS. Delete button label for renamed event not found even after scrolling; confirm/delete/mobile not reached. Do not call #8 UI PASS.
- Calendar True Account #4 / run 37712486403 FAIL: Cloud Run job task exit 1. Direct reason not established because current CI identity receives Cloud Logging PERMISSION_DENIED. No IAM changes authorized or made here.
- Follow-up change: categorised exit codes (reauthorization 21, insufficient scope 22, upstream 23, unavailable 24, invalid output 26, DB 31, runtime 32), plus Flutter web semantic-tree diagnostics and renamed-action widget regression assertion. Fail-closed behavior remains.
- Post-deploy #117 still ongoing at this checkpoint and must be read back separately.
- Package status: PARTIAL (7/11 completed = 63.6%). #63 Gemini/OpenRouter remains independent OPEN/FAIL, not a Calendar gate.

## 2026-10-09 V3 Calendar release and nested-Navigator defect

- Exact V3 release SHA: `22a7ce68b18ee8b3a63bee630687ef0f4372240e`.
- [V3 Release #37877453040](https://github.com/tommylin15/life_assistant/actions/runs/37877453040): **PASS**. Immutable GHCR image, 0% candidate, health/ready/auth, real database acceptance, hosting Preview, promoted live gates, rollback rehearsal, and latest-10 revision retention PASS.
- [Firebase Hosting #37879523958](https://github.com/tommylin15/life_assistant/actions/runs/37879523958): **PASS** on same SHA.
- [Calendar True Account #37879525880](https://github.com/tommylin15/life_assistant/actions/runs/37879525880): **PASS** on same SHA (real authorized read/list, no mutations). Historical True Account #4 FAIL is superseded by this success; do not mislabel prior failure as permanent.
- [Calendar UI #37879748204](https://github.com/tommylin15/life_assistant/actions/runs/37879748204): **FAIL** after list/all-day, create/timezone and update PASS. Production browser could not complete confirmed delete.
- Read-only same-production browser probes `37882121944`, `37882239050`, `37882379553` confirmed first delete action exists and works, cancel leaves no provider mutation, but subsequent confirmation did not dispatch DELETE; after dialog dismissal Flutter semantic tree could be empty.
- Root-cause code finding: `lib/web/calendar_page.dart` constructed dialog with root Navigator default, but used the Calendar page's possibly nested `context` to `Navigator.pop`. Product fix `3e607ca146184e778613cf28b80ec7db6566efdb` now pops with `dialogContext`; adds nested-Navigator widget regression plus browser no-reload cancel-confirm acceptance.
- All-day event create/update preservation of `date` and exclusive `end.date` implemented in commits `44f9d6d` and `97c6bf3`; local/CI tests were PASS, but new root-Navigator fix requires a fresh CI + V3 release and UI acceptance.
- **Package #8 = PARTIAL, Phase 1 remains 7/11 (63.6%).** No DONE until new exact-SHA CI, V3/Firebase production, desktop/mobile UI delete/cancel/all-day and real account acceptance all PASS. Distinguish mocked UI provider test from true Google read/list.


## 2026-10-09 Final Calendar #8 closure — DONE / PASS

- Source / release SHA: `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7` (同一完整 SHA 綁定 CI / V3 / Firebase / Calendar UI / Google read-list)。
- **Implementation / tests / CI — PASS:** [CI #37882690249](https://github.com/tommylin15/life_assistant/actions/runs/37882690249) backend tests、Flutter analyze/widgets/Drive nav/Web build、deployment scripts；全天日期 `start_date/end_date` 保持 Google `end.date` exclusive；對話框 `dialogContext` 修復巢狀 Navigator。
- **V3 GHCR → Cloud Run + runtime — PASS:** [V3 #37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014) immutable digest、Trivy、0%-traffic candidate、健康/資料庫/Auth、Preview、真實 pre-promotion integration、100% promotion/live、rollback rehearsal/restore、`life-assistant-api` 最新 **10 revisions** retention PASS。
- **Firebase Hosting — PASS:** [#37885328134](https://github.com/tommylin15/life_assistant/actions/runs/37885328134) exact-SHA release file, Flutter Web production, Task/Project UI regression gates。
- **真實 Google Calendar 授權 read/list（唯讀）— PASS:** [#37885330178](https://github.com/tommylin15/life_assistant/actions/runs/37885330178) 已有 owner-scoped Cloud Run Job runtime 成功結果；不宣稱曾對真實使用者行程執行 create/update/delete。
- **正式桌面／手機 Calendar UI（mocked Google responses）— PASS:** [#37885544932](https://github.com/tommylin15/life_assistant/actions/runs/37885544932) log: `month_list_allday`、`create_tz`、`update`、`confirmed_delete`、`all_day_edit`、`mobile_navigation_controls` 與 `calendar_ui_acceptance=PASS`。刪除驗證含「取消時無 mutation」及明示確認 header；此 UI 模擬不等同真實 Google mutation E2E。
- **Bootstrap E2E orchestration — PASS:** [#37882690327](https://github.com/tommylin15/life_assistant/actions/runs/37882690327) 逐步驗證 V3 + Firebase + Calendar UI + True Account gates，同 SHA 全成功。
- **特定界線：** #8 Calendar 依核准的 read/list 真實帳號 + mocked browser mutation 流程驗收封板；尚未以正式 Google 帳號執行真實 create/update/delete（風險較高的外部寫入），這不冒充已驗證。Drive Knowledge Gemini/OpenRouter 歷史 #63/#70 failure 仍是獨立跨功能 health backlog，不隨 Calendar 封板自動消失。

- **Release decision: #8 DONE / PASS，Phase 1 8/11 = 72.7%，全案仍 PARTIAL。** 上文過去 FAIL / NOT VERIFIED 為歷史快照，以上同 SHA 最新證據優先。不影響 #9–#11 或獨立 provider regression 的 Gate。
