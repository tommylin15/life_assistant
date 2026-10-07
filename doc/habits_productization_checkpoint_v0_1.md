# Habits Productization Checkpoint v0.1

日期：2026-10-07  
狀態：**DONE / PASS**  
Phase 1 package：**#6**  
Final release SHA：`02eda1124885846f41ca32ca185d9e1a5a5ebfe1`

## Scope

本 checkpoint 封板 Habits 完整 vertical slice：

- Flutter Web 正式入口：`/more/habits`
- Habit list / create / update
- recurrence / reminder
- completion mutation
- append-only completion history
- loading / empty / error state
- responsive mobile / desktop UX
- backend PostgreSQL persistence + activity evidence
- CI / Firebase / Cloud Run / post-deploy / production browser acceptance

既有 backend contract 沒有新增 delete / deactivate mutation；本工作包不自行擴張該 contract。

## Implementation

- `lib/web/habit_api.dart`
- `lib/web/habits_page.dart`
- `lib/web/more_page.dart` navigation
- `lib/web/web_app.dart` route
- Flutter widget/navigation tests
- `.github/scripts/verify_habits_ui_production.mjs`
- `.github/workflows/habits-ui-acceptance.yml`
- backend productization contract tests

### Flutter semantics follow-up

Production acceptance 發現 Flutter Web 將整張 Habit card 與 action semantics 合併，會讓 automation 無法可靠代表真實操作。

- `28f1bddc34f0e87c8eb757ce446ad8d9e54ec7c4`：隔離 completion / history action semantics。
- `02eda1124885846f41ca32ca185d9e1a5a5ebfe1`：acceptance 使用元素 bounding box 中心的 Flutter pointer event，驗證真實 engine interaction。

這些修正最後由 production acceptance 證明有效。

## Evidence

| Gate | Evidence | Result |
|---|---|---|
| Implementation | Habits Web/API/route/tests | PASS |
| CI | #558 / run `37577319168` | PASS |
| Firebase | #376 / run `37577494901` | PASS |
| Habits production UI | #7 / run `37577765718` | PASS |
| Cloud Run deployment/runtime | #430 / run `37577494982` | PASS |
| Post-deploy regression | #96 / run `37579244566` | PASS |
| Desktop UX | list/create/edit/complete/history | PASS |
| Mobile UX | navigation/controls/no-overflow gate | PASS |
| PostgreSQL runtime | habit create/update/complete/completions/activity | PASS |

Cloud Run #430 同時通過 migration、health、DB readiness、401 protection、authenticated cloud-domain、checklist、action-id idempotency、Google failure-path、SQLite backfill success/failure 與 image cleanup。

Post-deploy #96 同時通過 Notes product、Project Drive、Drive AI enrichment runtime regression。

## Cross-feature regression disclosure

同一 final release 的 **Drive Knowledge Runtime Acceptance #54 / run `37578066375` = FAIL**。

目前 evidence 顯示：

- Picker app-id contract：PASS
- real Drive fixture path：可用
- exact Firebase release：PASS
- OAuth config：PASS
- production Drive Knowledge UI：PASS
- live external AI production acceptance：FAIL

因此：

- Package #6 Habits 的所有 required gates完整，狀態為 **DONE / PASS**。
- Task 9 的 historical #47 PASS 不可用來宣稱 latest release 的 Drive Knowledge 仍為 PASS。
- latest-release Drive Knowledge health 必須標 **FAIL**，留待獨立 regression follow-up。
- Phase 1 整體仍為 **PARTIAL**。

## Closure

- Completed packages：**6/11**
- Closure progress：**54.5%**
- Next planned package：**#7 Shopping 完整產品化**
- Global release health note：Drive Knowledge #54 regression 尚未收斂。
