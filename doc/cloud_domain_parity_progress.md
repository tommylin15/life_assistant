# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 4）

對應設計：`doc/cloud_domain_parity_design.md`

對應計畫：`docs/superpowers/plans/2026-09-26-cloud-domain-parity.md`

## 狀態摘要

| Task | Scope | Implementation | Tests | CI | Deployment | Runtime |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL target models + Alembic migration | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 2 | Notes API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 3 | Habits API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 4 | Shopping API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 5 | Templates API parity | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 6 | Project delete guard | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 7 | Full backend verification | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 8 | CI / deployment / runtime acceptance | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |

## Task 1 — PostgreSQL target models + Alembic migration

狀態：**PASS（implementation / local tests）**

主要證據：

- 建立 Notes / Habits / Shopping / Templates ORM target models。
- Alembic revision：`20260926_0004`，`down_revision=20260925_0003`。
- `python -m unittest tests.test_cloud_domain_models -v`：6/6 PASS。
- Python compile：PASS。

仍為 NOT VERIFIED：GitHub Actions CI、Cloud Run deployment、PostgreSQL runtime table state、runtime `alembic_version`、SQLite → PostgreSQL historical backfill。

## Task 2 — Notes API parity

狀態：**PASS（implementation / local tests）**

主要內容：

- `backend/app/api/notes.py`
- Note request/response schemas
- `/api/v1/notes` router registration
- Note CRUD / bidirectional links / link cleanup
- execution actions：`note.create` / `note.update` / `note.delete` / `note.link`

驗證證據：

- Notes：12/12 PASS。
- Task 1 + Task 2 regression：18/18 PASS。
- Python compile：PASS。

仍為 NOT VERIFIED：GitHub Actions CI、Cloud Run deployment、PostgreSQL runtime CRUD/persistence、execution-log runtime visibility。

## Task 3 — Habits API parity

狀態：**PASS（implementation / local tests）**

主要內容：

- `backend/app/api/habits.py`
- Habit request/response schemas
- `/api/v1/habits` router registration
- active-only list / create / get / patch / complete / completion history
- execution actions：`habit.create` / `habit.update` / `habit.complete`

驗證證據：

- Habits：14/14 PASS。
- Task 1–3 regression（warnings-as-errors）：32/32 PASS。
- Python compile：PASS。

仍為 NOT VERIFIED：GitHub Actions CI、Cloud Run deployment、PostgreSQL runtime Habit CRUD/completion persistence、execution-log runtime visibility。

## Task 4 — Shopping API parity

狀態：**PASS（implementation / local tests）**

本 Task 建立 / 更新：

- `backend/app/api/shopping.py`
- `backend/app/models/schemas.py`：新增 `ShoppingListCreate` / `ShoppingItemCreate` / `ShoppingItemUpdate` / `ShoppingItemOut` / `ShoppingListOut`
- `backend/app/main.py`：註冊 Shopping router
- `backend/tests/test_shopping.py`

API contract：

- `GET /api/v1/shopping-lists`
- `POST /api/v1/shopping-lists`
- `GET /api/v1/shopping-lists/{list_id}`
- `POST /api/v1/shopping-lists/{list_id}/items`
- `PATCH /api/v1/shopping-items/{item_id}`

重要行為：

- Shopping List `name` 必須提供；`project_id` 可選，原樣保存且本批不做 project existence validation。
- Shopping Item `name` 必須提供；`category` 可選。
- request 長度限制與 DB 欄位一致：list/item name 500、category 255。
- `ShoppingItemUpdate` 只接受 `is_done`，空 PATCH、`is_done=null` 或額外欄位都拒絕。
- list response 巢狀 items，依 `sort_order ASC` 排序；同 sort order 以 id 提供穩定次序。
- item creation 先確認 list 存在，不存在回 404。
- item toggle 只改 `is_done`，不改 `name` / `category` / `list_id`。
- 不新增 delete / quantity / price / store API。
- mutation action types：`shopping_list.create` / `shopping_item.create` / `shopping_item.toggle`。
- provider 固定 `life_assistant`。

TDD / verification evidence：

- RED：Shopping schemas、router、main registration 尚不存在時，contract tests 如預期失敗。
- GREEN：`python -m unittest tests.test_shopping -v`：14/14 PASS。
- Regression slice：`python -m unittest tests.test_shopping tests.test_execution_log -v`：17/17 PASS。
- Full Task 1–4 regression（warnings-as-errors）：49/49 PASS。
- Python compile（Task 4 touched code/tests）：PASS。

GitHub 寫入說明：

- 本 Task 因 connector 的 Contents API 先建立 `shopping.py`，後續再補 schemas、main registration、tests 與進度文件，因此形成數個連續 commit。
- 未進行 force-push 或 history rewrite。
- Task 4 只在所有組件補齊後才標示 PASS。

尚未驗證：

- GitHub Actions CI：NOT VERIFIED
- Cloud Run deployment：NOT VERIFIED
- PostgreSQL runtime Shopping CRUD / nested read / toggle persistence：NOT VERIFIED
- execution log runtime visibility：NOT VERIFIED

## 執行規則

1. 一次只完成一個 Task。
2. Task 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 Task。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
