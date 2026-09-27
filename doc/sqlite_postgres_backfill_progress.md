# SQLite → PostgreSQL Historical Backfill Progress

最後更新：2026-09-27

## Scope

本文件只追蹤 Phase 1 的 historical SQLite → PostgreSQL user-data backfill。Cloud Domain Parity Task 1–8 已另行結案，不以該項 runtime parity 代替歷史資料搬遷完成判定。

## Current status

**PARTIAL**

Migration tooling / synthetic dev-test runtime scope：**DONE / PASS**  
Real historical user-data migration：**NOT VERIFIED**

| 項目 | 狀態 | 證據 |
| --- | --- | --- |
| Lossless target schema | PASS | Alembic `20260927_0005`，補齊 Checklist / Tags / Reminders / legacy attachment metadata / Calendar ref / Gmail ref / legacy activity / key-value state / migration ledger，以及 Task history 欄位。 |
| Deterministic SQLite export | PASS | `sqlite_postgres_backfill.export_bundle()`；同一 fixture 連續 export fingerprint / bundle 完全一致。 |
| Transform / source validation | PASS | schema/version/ID/timezone/relationship validation；broken relationship fail-closed。 |
| PostgreSQL import | PASS | dev-test synthetic runtime acceptance 實際寫入 PostgreSQL。 |
| Rerun idempotency | PASS | 第二次 import `inserted=0` 且 `idempotent_skips=source_rows`；migration ledger 防止 drift / target disappearance / collision。 |
| Critical field / relationship verification | PASS | Task status/priority/source fields、Checklist、Note link、Habit completion、Shopping、Tag、Attachment source path、Template payload、migration ledger 均在 dev-test runtime read-back。 |
| Source preservation | PASS | migration pipeline 以 read-only SQLite source export；failure-path runtime acceptance 在故障後重新 export，bundle / fingerprint 不變。 |
| PostgreSQL transaction rollback | PASS | failure-path runtime acceptance 預置 acceptance-only target collision，確認 Task 未寫入且 migration ledger 無殘留。 |
| Success audit evidence | PASS | `execution_logs` action `migration.sqlite_postgres`，synthetic acceptance 驗證兩次 success evidence。 |
| Failure audit runtime evidence | PASS | dev-test 故障注入產生 `TargetCollisionError`，驗證 execution log `status=failure`、`result=failed`、`error_category=TargetCollisionError`。 |
| Acceptance cleanup | PASS | success/failure acceptance 均以 exact acceptance IDs cleanup；failure acceptance 完成後 Project / Task tracked rows = 0。 |
| Real user SQLite source located | NOT VERIFIED | 2026-09-27 搜尋允許的 Drive root `life_assistantGPT`，未找到實際 `life_assistant.db` / backup。 |
| Real historical user-data migration | NOT VERIFIED | 尚無真實 source file 可執行，因此不能宣稱 historical user data 已搬完。 |

## Release evidence

Latest functional release SHA:

`fb59f013bce430c5643b2ebf2f5df7fe8729ddad`

Commit:

`test: add sqlite backfill failure runtime acceptance`

### CI

- CI #280 / run `36321693983`: **PASS**
- backend: PASS
- FastAPI import: PASS
- Alembic offline chain: PASS
- backend tests: PASS
- deployment scripts: PASS
- Flutter analyze / test / Web build / branding verification: PASS

### Firebase Hosting

- Deploy Firebase Hosting #179 / run `36321800021`: **PASS**
- Build / deploy / Hosting runtime verify: PASS

### Cloud Run

- Deploy Cloud Run #233 / run `36321800086`: **PASS**
- Apply verified database migration: PASS
- Backend deploy: PASS
- `/health`: PASS
- `/ready`: PASS
- unauthenticated protected API check: PASS
- authenticated Cloud Domain acceptance: PASS
- SQLite backfill success-path runtime acceptance: PASS
- SQLite backfill failure-path runtime acceptance: PASS

Failure-path acceptance contract：

- 隨機 acceptance-only Project / Task IDs。
- 預先在 PostgreSQL 建立同 Project ID collision。
- `import_bundle()` 必須拋出 `TargetCollisionError`。
- failure 後 SQLite source 再次 export 必須與 before 完全一致。
- collision Project 保持原值。
- Task 不得寫入。
- migration ledger 不得殘留。
- `execution_logs` 必須記錄 failure / failed / `TargetCollisionError`。
- 最後 exact-ID cleanup 並確認 tracked Project / Task rows = 0。

## Transaction-boundary bug fixed during rollout

第一次 online upgrade 0004 → 0005 暴露 Alembic transaction boundary 問題：在 `context.begin_transaction()` 之前執行 session-level advisory lock 會觸發 SQLAlchemy autobegin，使 migration DDL / revision update 可能在 connection close 時 rollback，表現為 release revision mismatch。

修正方式：

- 改用 `pg_advisory_xact_lock`。
- advisory lock 在 Alembic `context.begin_transaction()` 內取得。
- 新增 `backend/tests/test_alembic_online_lock.py` 固定 lock ordering 與 transaction-scoped contract。

修正後 Cloud Run #232、#233 的 verified database migration 與後續 runtime gates 全部 PASS。

## Completion rule

只有在取得實際 legacy SQLite source，完成 backup → export → validate → import → rerun → row/relationship/critical-field verification，並留下 success/failure evidence 後，才能把 **Real historical user-data migration** 標成 DONE。

因此目前：

- **Migration tooling / synthetic runtime：DONE / PASS**
- **Real historical user-data migration：NOT VERIFIED**
- 本文件整體 scope 仍為 **PARTIAL**；不得把 synthetic acceptance 包裝成真實使用者歷史資料已遷移。
