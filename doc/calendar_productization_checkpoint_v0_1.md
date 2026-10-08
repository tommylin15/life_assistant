# Calendar Productization Checkpoint v0.1 — Package #8

日期：2026-10-08  
狀態：**IN PROGRESS / PARTIAL**  
Phase 1 completed packages：**7 / 11（63.6%）**；#8 尚未計入。

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
| Widget / contract tests | NOT VERIFIED | `test/calendar_page_test.dart` candidate |
| CI Flutter analyze / tests / build | NOT VERIFIED | Requires passing CI on exact SHA |
| Firebase release | NOT VERIFIED | Requires successful deploy on exact SHA |
| Cloud Run API / permission / runtime | NOT VERIFIED | Existing backend baseline; current release must be checked |
| Production desktop UI | NOT VERIFIED | `calendar-ui-acceptance.yml` and Playwright candidate |
| Production mobile UI | NOT VERIFIED | Same workflow; overflow and navigation |
| Real Google account Calendar read/list | NOT VERIFIED | Read-only `calendar-true-account-acceptance.yml` executes after Cloud Run deployment; requires exactly one authorized Calendar account |
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
