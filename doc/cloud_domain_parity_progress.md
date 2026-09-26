# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26 14:20 Asia/Taipei

對應設計：`doc/cloud_domain_parity_design.md`

對應計畫：`docs/superpowers/plans/2026-09-26-cloud-domain-parity.md`

## 狀態摘要

| Task | Scope | Implementation | Tests | CI | Deployment | Runtime |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL target models + Alembic migration | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 2 | Notes API parity | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 3 | Habits API parity | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 4 | Shopping API parity | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 5 | Templates API parity | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 6 | Project delete guard | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 7 | Full backend verification | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 8 | CI / deployment / runtime acceptance | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |

## Task 1 — PostgreSQL target models + Alembic migration

狀態：**PASS（implementation / local tests）**

本 Task 建立：

- `backend/app/models/note.py`
- `backend/app/models/habit.py`
- `backend/app/models/shopping.py`
- `backend/app/models/template.py`
- `backend/alembic/versions/20260926_0004_cloud_domain_parity.py`
- `backend/tests/test_cloud_domain_models.py`
- 更新 `backend/alembic/env.py` 使 Alembic metadata 載入新 models

驗證證據：

- `python -m unittest tests.test_cloud_domain_models -v`：6/6 PASS
- Python compile：PASS
- migration revision：`20260926_0004`
- `down_revision`：`20260925_0003`

重要 contract：

- Notes `title/body` DB nullable，保留 SQLite migration compatibility。
- Habit / Shopping List 不新增不存在的 historical `updated_at`。
- Shopping Item 不新增 source 不存在的 created/updated timestamp。
- Template `payload_json` 保持 PostgreSQL `TEXT`，不改成 JSONB。
- Habit `is_active`、Shopping Item `is_done/sort_order` 的 server defaults 同時存在於 ORM metadata，避免目前 Cloud Run startup `Base.metadata.create_all()` 與 Alembic schema 出現 drift。
- Habit completion `(habit_id, completed_at DESC)` index 同時存在於 ORM metadata 與 Alembic migration。

尚未驗證：

- GitHub Actions CI：NOT VERIFIED
- Cloud Run deployment：NOT VERIFIED
- PostgreSQL runtime table state：NOT VERIFIED
- dev/test DB `alembic_version` runtime head：NOT VERIFIED
- SQLite → PostgreSQL historical backfill：NOT VERIFIED；目前 repository 尚未有可證明本批四 domain 真實 backfill 的 importer evidence。

## 執行規則

從 Task 1 起，採用以下節奏：

1. 一次只完成一個 Task。
2. Task 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 Task。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
