# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 3）

對應設計：`doc/cloud_domain_parity_design.md`

對應計畫：`docs/superpowers/plans/2026-09-26-cloud-domain-parity.md`

## 狀態摘要

| Task | Scope | Implementation | Tests | CI | Deployment | Runtime |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL target models + Alembic migration | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 2 | Notes API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 3 | Habits API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 4 | Shopping API parity | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
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

本 Task 建立 / 更新：

- `backend/app/api/habits.py`
- `backend/app/models/schemas.py`：新增 `HabitCreate` / `HabitUpdate` / `HabitOut` / `HabitCompletionOut`
- `backend/app/main.py`：註冊 `/api/v1/habits`
- `backend/tests/test_habits.py`

API contract：

- `GET /api/v1/habits`：只回 `is_active = true`
- `POST /api/v1/habits`
- `GET /api/v1/habits/{habit_id}`
- `PATCH /api/v1/habits/{habit_id}`
- `POST /api/v1/habits/{habit_id}/complete`
- `GET /api/v1/habits/{habit_id}/completions`

重要行為：

- Create 必須提供 `title` 與 `recurrence_rule`；`reminder_time` 可省略。
- PATCH 只允許 `title` / `recurrence_rule` / `reminder_time`；空 PATCH 拒絕，`title=null` / `recurrence_rule=null` 拒絕，`reminder_time=null` 可清除提醒。
- 不新增 delete / activate / deactivate API。
- 每次 complete 建立新的 UUID `HabitCompletion`，不覆寫舊 completion。
- completion history 以 `completed_at DESC` 排序。
- mutation action types：`habit.create` / `habit.update` / `habit.complete`。
- provider 固定 `life_assistant`。

TDD / verification evidence：

- RED：Habit schemas、router、main registration 尚不存在時，contract tests 如預期失敗；既有 model default contract 已獨立 PASS。
- GREEN：`python -m unittest tests.test_habits -v`：14/14 PASS。
- Regression（warnings-as-errors）：`python -m unittest tests.test_cloud_domain_models tests.test_notes tests.test_habits -v`：32/32 PASS。
- Python compile（Task 3 touched code/tests）：PASS。

尚未驗證：

- GitHub Actions CI：NOT VERIFIED
- Cloud Run deployment：NOT VERIFIED
- PostgreSQL runtime Habit CRUD / completion persistence：NOT VERIFIED
- execution log runtime visibility：NOT VERIFIED

## 執行規則

1. 一次只完成一個 Task。
2. Task 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 Task。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
