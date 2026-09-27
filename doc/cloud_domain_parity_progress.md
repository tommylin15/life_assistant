# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-27（Task 8 deployment + runtime acceptance 完成）

對應設計：`doc/cloud_domain_parity_design.md`

專案治理：`doc/PROJECT_RULES.md`

> `docs/superpowers/` 內容依 `doc/PROJECT_RULES.md` 僅屬 historical / legacy artifact，不是目前工作流程或 Source of Truth。

## 最終狀態

Cloud Domain Parity Task 1–8：**DONE**。

這個 DONE 只代表本文件定義的 Cloud Domain Parity 範圍完成，不代表整個 `life_assistant` 專案全部完成。

GitHub Actions 的部署 environment 實際名稱為 **`dev-test`**。本文件自此使用「dev-test deployed environment」描述本輪 GCP/PostgreSQL runtime evidence；舊 checkpoint 中使用 production 一詞者視為歷史文字，不應解讀為另一套已驗證 production environment。

| Task | Scope | Implementation | Tests | CI | Deployment | Runtime |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL target models + Alembic migration | PASS | PASS | PASS | PASS | PASS |
| 2 | Notes API parity | PASS | PASS | PASS | PASS | PASS |
| 3 | Habits API parity | PASS | PASS | PASS | PASS | PASS |
| 4 | Shopping API parity | PASS | PASS | PASS | PASS | PASS |
| 5 | Templates API parity | PASS | PASS | PASS | PASS | PASS |
| 6 | Project delete guard | PASS | PASS | PASS | PASS | PASS |
| 7 | Full backend verification | PASS | PASS | PASS | PASS | PASS |
| 8 | CI / deployment / runtime acceptance | PASS | PASS | PASS | PASS | PASS |

Historical SQLite → PostgreSQL user-data backfill remains a separate migration concern and is **NOT VERIFIED** by this Cloud Domain Parity acceptance run. It does not invalidate the target-schema/API/runtime parity evidence recorded here.

---

## Final release evidence

### Release commit

- Functional release SHA：`19b56fb0a865b4e5b6260c13a40e04e66ef64676`
- Message：`fix: gate deploy on cloud domain runtime acceptance`
- `main` was at this SHA when final Task 8 runtime evidence was collected.

### Formal CI

CI #275 / run `36289075250`：**PASS**。

- backend：PASS
- FastAPI import：PASS
- Alembic offline chain：PASS
- backend full test suite：PASS
- deployment scripts：PASS
- Flutter analyze：PASS
- Flutter tests：PASS
- Flutter Web build：PASS
- branding verification：PASS

The final CI includes the runtime-acceptance contract tests requiring:

- `backend/scripts/run_cloud_domain_parity_acceptance.py`;
- the acceptance gate in `.github/workflows/deploy-cloud-run.yml`;
- the acceptance gate to run only after health / readiness / unauthenticated-protection checks.

### Firebase Hosting

Deploy Firebase Hosting #174 / run `36289173006`：**PASS**。

### Cloud Run + PostgreSQL migration

Deploy Cloud Run #228 / run `36289173011`：**PASS**。

Migration job：`life-assistant-db-migrate`

Successful execution：`life-assistant-db-migrate-h67ll`

The migration gate completed successfully before the backend service deploy.

### Backend deploy

Cloud Run service：`life-assistant-api`

Revision：`life-assistant-api-00069-rz7`

Traffic：100% routed to the revision above.

Runtime checks in the same deployment workflow：

- `/health` → `{"status":"ok"}`：PASS
- `/ready` → `{"status":"ok","database":"ok"}`：PASS
- unauthenticated `/api/v1/tasks` → HTTP 401：PASS

`gcloud run deploy --allow-unauthenticated` emitted an IAM-policy warning while trying to re-apply the existing `allUsers` binding. This did **not** block this deployment: the new revision received 100% traffic and the unauthenticated `/health` and `/ready` probes succeeded. No additional IAM change was made as part of closing Task 8.

---

## Authenticated cloud-domain runtime acceptance

The final deploy uses an explicit Cloud Run acceptance job:

- job：`life-assistant-cloud-domain-acceptance`
- execution：`life-assistant-cloud-domain-acceptance-55ng2`
- result：**PASS**

The job runs from the **same container image just deployed to `life-assistant-api`**. It exercises real FastAPI route code and real PostgreSQL sessions in the dev-test deployed environment.

Only the `current_user` dependency is replaced by a fixed acceptance identity. This deliberately avoids requiring or exposing a personal Google OAuth token. Therefore this acceptance proves Cloud Domain API/database behavior, not the browser Google OAuth login flow itself.

### Acceptance coverage

#### Project delete guard

- create Project：PASS
- create linked Note：PASS
- delete Project while linked Note exists → 409：PASS
- unlink Note：PASS
- create linked Shopping List：PASS
- delete Project while linked Shopping List exists → 409：PASS
- remove acceptance Shopping rows by exact IDs：PASS
- delete Project after references are removed → 204：PASS

#### Notes

- create Note A / Note B：PASS
- patch Note and read back persisted values：PASS
- create bidirectional note link：PASS
- linked-note reread：PASS
- delete Notes through API：PASS

#### Habits

- create Habit：PASS
- patch Habit：PASS
- append two distinct completion rows：PASS
- read completion history and verify both persisted rows：PASS

#### Shopping

- create Shopping List：PASS
- create Shopping Item：PASS
- toggle `is_done`：PASS
- nested Shopping List reread confirms persisted toggle：PASS

#### Templates

- create Template：PASS
- patch `payload_json`：PASS
- exact opaque string round-trip after reread：PASS

#### Execution / Activity Log

For the acceptance identity, the runner verifies successful execution evidence for every mutation family exercised by the run：**PASS**。

#### Cleanup

Acceptance artifacts are tagged `[ACCEPTANCE TEST]`, tracked by exact IDs, and cleanup runs in a `finally` path.

Cleanup contract：

- Note links：exact acceptance note IDs only
- Notes：exact IDs only
- Habit completions：exact IDs only
- Habits：exact IDs only
- Shopping items/lists：exact IDs only
- Templates：exact IDs only
- Projects：exact IDs only
- post-cleanup DB read verifies no tracked acceptance rows remain

Final acceptance job exit was success, therefore the runner reached a PASS state including its exact-ID cleanup verification.

---

## Migration / schema diagnosis history

Task 8 required several guarded checkpoints before the final pass. Important historical evidence is retained below in compressed form.

### 1. Unversioned physical schema identified

Earlier releases established that:

- `public.alembic_version` was missing;
- the seven `20260926_0004` target tables already existed;
- the database therefore could not be treated as a clean Alembic 0003 baseline.

### 2. Missing Project indexes repaired

Diagnostics isolated missing:

- `ix_projects_status`
- `ix_projects_name`

The repair path was additive and idempotent, with exact-definition verification. Subsequent structural verification passed.

### 3. Stronger Alembic metadata preflight added

The stronger preflight validates more than columns/type/nullability, including:

- migration-required DB server defaults;
- exact required index definitions;
- FK update/delete actions and FK semantics;
- absence of unexpected UNIQUE / CHECK / EXCLUDE constraints.

This intentionally prevented treating the earlier structural exit `33` as sufficient evidence for metadata bootstrap.

### 4. `projects.status` DB default drift diagnosed and repaired

The preflight narrowed the mismatch to:

- table/column：`projects.status`
- expected Alembic server default：`active`
- deployed DB state：server default missing

The repair was limited to setting the missing DB server default; it did not rewrite or backfill existing business rows.

### 5. PostgreSQL FK action driver representation normalized

After the default repair, FK verification exposed a driver-representation issue rather than actual schema drift: PostgreSQL internal `"char"` action codes could be returned as bytes-like values by the async driver.

Commit `4f367bc74a28ee415b4cd81dd32e5b2d4a9e23b0` normalizes `bytes` / `bytearray` / `memoryview` / string forms before FK contract comparison. This allowed the same physical FK semantics to compare correctly across driver representations.

### 6. Guarded Alembic metadata bootstrap

Commit `4475a11f23f67d995a1616fa8086d625dde9ee21` added the guarded metadata bootstrap.

Safety properties：

- approval is revision-scoped to `20260926_0004`;
- uses the same advisory lock as migration execution;
- while holding the lock, re-runs the complete physical-schema preflight;
- writes only standard `public.alembic_version` metadata when the DB is unversioned and fully verified;
- an already-versioned DB at the target revision is an idempotent no-op;
- any mismatch fails closed;
- no application-table or business-data rewrite is part of the bootstrap.

The subsequent migration execution completed successfully, proving the database reached the expected Alembic target revision state.

---

## Current Task 8 verdict

### Implementation

**PASS**

### Tests

**PASS**

### Formal main CI

**PASS — CI #275**

### Database migration / metadata

**PASS — `life-assistant-db-migrate-h67ll`**

### Cloud Run deployment

**PASS — Deploy #228 / revision `life-assistant-api-00069-rz7`**

### Runtime health / readiness / auth protection

**PASS**

### Cloud domain CRUD / persistence / Project guard / execution log

**PASS — `life-assistant-cloud-domain-acceptance-55ng2`**

### Acceptance cleanup

**PASS**

### Firebase Hosting

**PASS — #174**

## Final Task 8 status

**DONE / PASS**

No remaining blocker exists inside the Cloud Domain Parity Task 1–8 scope.

---

## Remaining items outside this DONE scope

These are not blockers for Cloud Domain Parity Task 8, but remain separate work if/when their own task is opened:

- Historical SQLite → PostgreSQL user-data backfill verification：NOT VERIFIED
- current-release browser Google OAuth interactive login flow：not exercised by the automated Cloud Domain acceptance job
- Gmail / Calendar / Drive live-account acceptance：separate integration scope
- future native Android/iOS packaging：outside current Web/PWA Phase 1 mainline

## Execution rules going forward

1. Current implementation / CI / deployment truth comes from GitHub and runtime evidence.
2. Status remains separated into implementation / tests / CI / deployment / runtime / integration.
3. Partial success must not be reported as full success.
4. Destructive migration, destructive production data/resource deletion, major IAM expansion, secret rotation, or force-push still require explicit confirmation.
5. Normal code/test/commit/CI/CD and non-destructive deployment continue through `main → GitHub Actions → GCP → runtime validation`.
