# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 8 projects index reconciliation design）

對應設計：`doc/cloud_domain_parity_design.md`

對應計畫：`docs/superpowers/plans/2026-09-26-cloud-domain-parity.md`

## 狀態摘要

| Task | Scope | Implementation | Tests | CI | Deployment | Runtime |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL target models + Alembic migration | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 2 | Notes API parity | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 3 | Habits API parity | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 4 | Shopping API parity | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 5 | Templates API parity | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 6 | Project delete guard | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 7 | Full backend verification | PASS | PASS | PASS | NOT VERIFIED | NOT VERIFIED |
| 8 | CI / deployment / runtime acceptance | PASS | PASS | PASS | FAIL | FAIL |

Task 8 整體狀態：**PARTIAL**。不得標示 DONE。

---

## Tasks 1–7 — 已完成 implementation / tests / CI

### Task 1 — PostgreSQL target models + Alembic migration

狀態：**PASS（implementation / tests / formal main CI）**

- 建立 Notes / Habits / Shopping / Templates ORM target models。
- Alembic revision：`20260926_0004`，`down_revision=20260925_0003`。
- model contract tests：PASS。
- Alembic offline chain：PASS。
- Runtime DB metadata / historical SQLite backfill：仍依 Task 8 evidence 判定，不以程式完成代替 runtime acceptance。

### Task 2 — Notes API parity

狀態：**PASS（implementation / tests / formal main CI）**

- Notes CRUD、bidirectional links、delete link cleanup、legacy nullable read。
- mutation action types：`note.create` / `note.update` / `note.delete` / `note.link`。
- PostgreSQL runtime CRUD：NOT VERIFIED。

### Task 3 — Habits API parity

狀態：**PASS（implementation / tests / formal main CI）**

- active-only list、create/get/patch、append completion、descending history。
- 不新增 delete / activate / deactivate。
- mutation action types：`habit.create` / `habit.update` / `habit.complete`。
- PostgreSQL runtime completion persistence：NOT VERIFIED。

### Task 4 — Shopping API parity

狀態：**PASS（implementation / tests / formal main CI）**

- Shopping List create/read、item create、nested sorted read、`is_done` toggle。
- `project_id` 原樣保存，本批不做 project existence validation。
- 不新增 delete / quantity / price / store。
- mutation action types：`shopping_list.create` / `shopping_item.create` / `shopping_item.toggle`。
- PostgreSQL runtime persistence：NOT VERIFIED。

### Task 5 — Templates API parity

狀態：**PASS（implementation / tests / formal main CI）**

- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`
- `payload_json` 維持 opaque `TEXT` string，不 parse / normalize / reserialize。
- 不新增 delete / apply / version-history endpoint。
- mutation action types：`template.create` / `template.update`。
- provider 固定 `life_assistant`；execution summary 不包含 payload 本文。
- PostgreSQL runtime opaque payload round-trip：NOT VERIFIED。

### Task 6 — Project delete guard

狀態：**PASS（implementation / tests / formal main CI）**

- `DELETE /api/v1/projects/{project_id}` 在 Project 被 Task / Note / Shopping List 參照時回 `409`。
- guard 發生在 `project.delete` execution record 建立之前。
- 本 Task 不新增 Project FK、cascade 或跨-domain destructive behavior。
- PostgreSQL runtime Project delete guard acceptance：NOT VERIFIED。

### Task 7 — Full backend verification

狀態：**PASS（implementation / tests / CI verification）**

- FastAPI import：PASS。
- Alembic offline chain：PASS，包含 `20260925_0003 -> 20260926_0004`。
- Backend full suite：PASS。
- Flutter analyze / tests / Web build / branding verification：PASS。
- GCP deployment scripts syntax：PASS。
- Historical SQLite → PostgreSQL backfill：NOT VERIFIED；沒有 importer execution evidence，不宣稱 PASS。

---

## Task 8 — CI / deployment / runtime acceptance

狀態：**PARTIAL — implementation / tests / formal main CI PASS；production migration contract FAIL；service/runtime blocked**

### Runtime migration gate

Cloud Run migration job：`life-assistant-db-migrate`。

正式 deployment 在 Cloud Run service deploy 前先執行 migration contract；runner：

`backend/scripts/apply_cloud_domain_parity_migration.py`

原則：

- fail-closed；
- 不以 stamp / drop / truncate 隱藏 drift；
- production diagnostics 優先使用 execution / task exit code；
- Cloud Logging 權限不足時不為除錯額外增加 IAM；
- diagnosis 階段不修改 production schema / data / Alembic metadata。

### Diagnostic history

#### 1. Generic contract diagnosis

- main CI #228：PASS；backend 118/118 PASS。
- Deploy Cloud Run #181：FAIL；migration task exit `21`。
- 先前 script-path import failure exit `1` 已由 module mode `python -m scripts.apply_cloud_domain_parity_migration` 排除。

#### 2. Contract subtype split

固定分類：

- `20`：database / SQLAlchemy error。
- `21`：revision validation failure。
- `22`：Alembic subprocess failure。
- `23`：pre-created target-table drift。
- `24`：target schema / PK / FK / index mismatch。
- `25`：preserved table / row-count mismatch。
- `29`：unexpected runtime failure。

Evidence：

- RED commit：`58fd8347822fb90baf645b7a90e9589ae100a3dc`；CI #229 如預期 RED。
- GREEN commit：`90875fdeadfba93b2a334e7d951a28c10f136eeb`；CI #230 PASS；backend 121/121 PASS。
- Deploy #183：exit `21`，確認 production failure 在 revision validation。

#### 3. Revision-state subtype split

- `21`：`alembic_version` table missing。
- `26`：revision row count invalid。
- `27`：unexpected current revision。
- `28`：post-migration revision mismatch。

Evidence：

- CI #232：PASS。
- Deploy #185：exit **21**。
- Production：`public.alembic_version` **不存在 / VERIFIED**。
- 未 stamp、未修改 revision row。

#### 4. Read-only baseline verification

Baseline revisions `0001–0003`：

- `google_connections`
- `google_oauth_states`
- `execution_logs`
- `projects`

驗證 columns / type / nullability / PK / required indexes。

- `30`：baseline tables missing。
- `31`：baseline schema mismatch。
- `32`：baseline verified but unversioned。

Evidence：

- RED CI #233：如預期 RED。
- GREEN commit：`6d7261f06fc0c71e23ac22321a4d8d1eb2cc2876`。
- CI #234：PASS；backend 133/133 PASS。
- Deploy #187：exit **23**，證明 unversioned DB 已有至少一張 `0004` target table，因此不能把 production 當成乾淨 `0003` 直接 stamp。

#### 5. Exact target-table presence bitmap

Target order / bit：

- `notes` = 1
- `note_links` = 2
- `habits` = 4
- `habit_completions` = 8
- `shopping_lists` = 16
- `shopping_items` = 32
- `templates` = 64

Diagnostic exit = `64 + bitmap`。

Evidence：

- RED commit：`4f3ae9e31aceb7b62fd31287fc6007b7a19c3f9c`；CI #235 如預期 RED。
- GREEN commit：`1a94cf2141260170af6f7a63067d761c4df1b741`。
- CI #236：PASS；backend 136/136 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #135：PASS。
- Deploy #189：execution `life-assistant-db-migrate-q85fd`；task exit **191**。

`191 = 64 + 127`：七張 `0004` target tables **全部存在 / VERIFIED**。

但 table presence 不等於 schema exact equivalence，因此仍不能 stamp。

#### 6. Full unversioned schema path

路徑改為：

- partial target subset → bitmap fail-closed；
- all seven target tables present → 先驗證 baseline `0001–0003` exact shape，再驗證 `0004` exact schema；
- baseline mismatch → `31`；
- target mismatch → `24`；
- 若 `0001–0004` 全部 exact match、但 metadata 缺失 → `33`，仍不自動 stamp。

Evidence：

- RED commit：`c6d3dcbf105b41d26883271d93b9b7a325c20189`；CI #237 如預期 RED。
- GREEN commit：`0ef210a6a8f953598456151a994e25e142861624`。
- CI #238：PASS；backend 139/139 PASS。
- Firebase Hosting #137：PASS。
- Deploy #191：execution `life-assistant-db-migrate-sqmz4`；task exit **31**。

Production root state 因此確認為 baseline schema mismatch；當時 exact table / mismatch type 尚未知。

#### 7. Exact baseline table + mismatch-class subtype

- `34`：`google_connections` shape mismatch。
- `35`：`google_connections` required-index mismatch。
- `36`：`google_oauth_states` shape mismatch。
- `37`：`google_oauth_states` required-index mismatch。
- `38`：`execution_logs` shape mismatch。
- `39`：`execution_logs` required-index mismatch。
- `40`：`projects` shape mismatch。
- `41`：`projects` required-index mismatch。

Evidence：

- RED commit：`1c9f4cea83c506b977da512056149914cf428f02`；CI #239 如預期 RED。
- GREEN commit：`b5bf6ddaf98e43d15f40a0f7a26e516c77889723`。
- CI #240：PASS；backend 142/142 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #139：PASS。
- Deploy #193：run `36240544928`；execution `life-assistant-db-migrate-hcx8n`；task exit **41**。

因 verifier 依序通過前三張 baseline table，再於 `projects` index 檢查失敗，所以已驗證：

- `google_connections` columns/type/nullability/PK：PASS / VERIFIED。
- `google_oauth_states` shape + required indexes：PASS / VERIFIED。
- `execution_logs` shape + required indexes：PASS / VERIFIED。
- `projects` columns/type/nullability/PK：PASS / VERIFIED。
- `projects` required indexes：FAIL / VERIFIED。

#### 8. Exact single `projects` required-index subtype

- `42`：`ix_projects_status` missing。
- `43`：`ix_projects_status` definition mismatch。
- `44`：`ix_projects_name` missing。
- `45`：`ix_projects_name` definition mismatch。

Evidence：

- RED commit：`76371e7472e1e3ba18f617dc0dbd0e26a7be62a8`；CI #241 backend 如預期 RED，147 tests 中新增 5 個 assertions ERROR。
- GREEN commit：`30f8ac5a70e7e6ec739ab49511c49ec3d75b8f0f`。
- CI #242：PASS；backend **147/147 PASS**；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #141（run `36242072583`）：PASS。
- Deploy Cloud Run #195（run `36242072582`）：FAIL。
- Execution：`life-assistant-db-migrate-94jpj`。
- Task：`life-assistant-db-migrate-94jpj-task0`。
- Exit：**42** = `ix_projects_status` missing。

該版 validator 在第一個 index failure 即停止，因此當時 `ix_projects_name` 仍 NOT VERIFIED。

#### 9. Combined `projects` index diagnosis

本 checkpoint 改成一次收集兩個 `projects` required-index 狀態。單一 mismatch 仍沿用 `42–45`；兩個同時 mismatch 使用：

- `46`：status missing + name missing。
- `47`：status missing + name definition mismatch。
- `48`：status definition mismatch + name missing。
- `49`：status definition mismatch + name definition mismatch。

全部低於 target-table bitmap range（64+），避免診斷碼碰撞。

TDD / CI evidence：

- RED commit：`c60cb1b11e8fbbe11a324eab0b4d670287b7c69a`（`test: diagnose combined projects index drift`）。
- CI #243：backend 共 **152 tests**；只有新增的 5 個 combined-index tests 因新 mapping / exception 尚未實作而 ERROR；既有 147 tests PASS；Alembic validation / deployment-scripts PASS。
- GREEN commit：`0388efa53822eb7ba762f58e8745fe2348a99091`（`fix: diagnose both projects indexes`）。
- CI #244（run `36248619499`）：**PASS**。
- Backend full suite：**152/152 PASS**。
- Alembic offline chain：PASS，`0001 -> 0002 -> 0003 -> 0004`。
- Flutter analyze / tests / Web build / branding verification：PASS。
- deployment-scripts：PASS。
- Firebase Hosting #143（run `36248731171`）：**PASS**。

Production evidence：

- Deploy Cloud Run #197：run `36248731070`，release commit `0388efa53822eb7ba762f58e8745fe2348a99091`。
- Migration execution：`life-assistant-db-migrate-hbjxj`。
- Migration task：`life-assistant-db-migrate-hbjxj-task0`。
- `status.lastAttemptResult.exitCode`：**46**。
- Cloud Run execution condition 同樣指出 task failed with exit code **46**。
- `46` 的唯一分類：
  - `ix_projects_status`：**missing / FAIL / VERIFIED**。
  - `ix_projects_name`：**missing / FAIL / VERIFIED**。
- 兩者都不是 definition mismatch。
- Migration gate 正確阻擋後續 Cloud Run service deploy；service URL / `/health` / `/ready` / unauthenticated API checks 均 skipped。
- Logging read 仍 `PERMISSION_DENIED`；未變更 IAM。

### Migration contract vs ORM metadata discrepancy

GitHub Source of Truth 顯示：

- `backend/alembic/versions/20260925_0003_projects.py` 明確建立：
  - `ix_projects_status` on `projects(status)`；
  - `ix_projects_name` on `projects(name)`。
- `backend/app/models/project.py` 目前沒有 `index=True` 或等價的 explicit `Index(...)` metadata。

判定：

- 正式歷史 migration contract 要求兩個 index；
- ORM metadata 未同步表達該 contract；
- 不應修改既有 `20260925_0003` 歷史 migration 來掩蓋差異；
- 後續應讓 ORM metadata / contract tests 與既有 migration 對齊，但 ORM 修正本身不等於 production DB repair。

### Repair / reconciliation design（本 checkpoint 僅設計，不執行 production mutation）

Production 目前是 **unversioned + pre-existing schema**，因此不能直接把一般 Alembic forward migration 當成修復手段，也不能先 stamp。

建議安全順序：

1. **建立 dedicated pre-stamp reconciliation path**，只處理已被 production evidence 證實缺失的 `ix_projects_status` / `ix_projects_name`。
2. 對每個 index 先做 exact catalog preflight：
   - 若名稱不存在 → 才允許 additive create；
   - 若同名 index 已存在且 definition 不符 → fail-closed，不自動 drop / replace；
   - 不用 blind `IF NOT EXISTS` 掩蓋錯誤 definition。
3. Repair implementation 必須可重跑、可稽核、明確區分「already exact / created / conflict」。
4. 同步補齊 Project ORM metadata，使其明確表達兩個 index，並以 tests 防止 migration/ORM contract 再次分叉。
5. Index repair 後重新跑完整 **read-only 0001–0004 verifier**：
   - baseline 必須全部 exact match；
   - 七張 `0004` target tables 必須通過 columns / type / nullability / PK / FK / required-index exact verification。
6. 只有 verifier 達到「full schema verified but unversioned」狀態（目前 exit `33` contract）後，才可評估 Alembic metadata bootstrap / `stamp 20260926_0004`。
7. **production stamp 不在本 checkpoint 執行**。在真正寫入 Alembic metadata 前，必須取得使用者明確確認。
8. Metadata 恢復後，才回到正常的 Alembic forward migration lifecycle。

是否使用 `CREATE INDEX CONCURRENTLY` 暫不先決定：需先以 production table size / lock tolerance / transaction model 為依據；不得只為避免 lock 就直接引入 concurrent-index transaction 複雜度。

### Current production state

- `public.alembic_version`：**missing / VERIFIED**。
- 七張 `0004` target tables：**all present / VERIFIED**。
- `google_connections` baseline shape：**PASS / VERIFIED**。
- `google_oauth_states` baseline shape + required indexes：**PASS / VERIFIED**。
- `execution_logs` baseline shape + required indexes：**PASS / VERIFIED**。
- `projects` columns/type/nullability/PK：**PASS / VERIFIED**。
- `ix_projects_status`：**missing / FAIL / VERIFIED**。
- `ix_projects_name`：**missing / FAIL / VERIFIED**。
- `0004` target schema exact equivalence：**NOT VERIFIED**，因 baseline index gate 尚未通過。
- Cloud Run service current release：**FAIL / blocked by migration gate**。
- `/health`：current release **NOT VERIFIED**。
- `/ready`：current release **NOT VERIFIED**。
- unauthenticated API protection：current release **NOT VERIFIED**。
- authenticated Notes / Habits / Shopping / Templates runtime CRUD：**NOT VERIFIED**。
- Project delete guard runtime acceptance：**NOT VERIFIED**。
- historical SQLite → PostgreSQL backfill：**NOT VERIFIED**。

### Safety / mutation record

截至本 checkpoint，production diagnosis 仍維持 read-only：

- 未執行 `alembic stamp`。
- 未建立 / 修改 `alembic_version`。
- 未 drop / truncate / recreate production table。
- 未 create / drop / alter / reindex production index。
- 未修改 production data。
- 未增加 Cloud Logging IAM 權限。

因此目前仍 **禁止直接 stamp `20260925_0003` 或 `20260926_0004`**。

### Progress-document lineage correction

先前 Task 8 詳細進度曾存在 commit `c3f8518cee82924db58f84dfe13c64f78d52e5e9`，但本 checkpoint 檢查 main 時發現 `doc/cloud_domain_parity_progress.md` 仍停在 Task 7 舊版。

本 checkpoint 已先將該 Task 8 history 以既有 blob 恢復到目前 main，再用本文件整併 checkpoint 9 evidence，避免正式 progress document 與 GitHub implementation/runtime evidence 分叉。

### 下一個安全 checkpoint

下一步才進 implementation：

- TDD 實作 controlled pre-stamp index reconciliation path；
- 補 Project ORM explicit index metadata 與 migration/ORM parity tests；
- CI 驗證。

下一 checkpoint **不先 stamp**。是否讓 repair path 實際對 production 建立兩個 index，必須先完成 implementation/tests/CI 與必要的 production preflight，再依風險與證據決定執行方式。

---

## 執行規則

1. 一次只完成一個 Task / checkpoint。
2. checkpoint 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 checkpoint。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
