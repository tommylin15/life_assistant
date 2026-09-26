# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 8 guarded pre-stamp projects index reconciliation）

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
| 8 | CI / deployment / runtime acceptance | PASS | PASS | PASS | FAIL | NOT VERIFIED |

Task 8 整體狀態：**PARTIAL**。目前 production schema contract 已驗證 exact，但 Alembic metadata 尚未恢復，因此 migration gate 仍阻擋 Cloud Run service release；不得標示 DONE。

---

## Tasks 1–7 — 已完成 implementation / tests / CI

### Task 1 — PostgreSQL target models + Alembic migration

狀態：**PASS（implementation / tests / formal main CI）**

- 建立 Notes / Habits / Shopping / Templates ORM target models。
- Alembic revision：`20260926_0004`，`down_revision=20260925_0003`。
- model contract tests：PASS。
- Alembic offline chain：PASS。
- Historical SQLite → PostgreSQL backfill：NOT VERIFIED；沒有 importer execution evidence，不宣稱 PASS。

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

---

## Task 8 — CI / deployment / runtime acceptance

狀態：**PARTIAL — implementation / tests / formal main CI PASS；production schema exact PASS；Alembic metadata missing；service/runtime blocked**

### Runtime migration gate

Cloud Run migration job：`life-assistant-db-migrate`。

原始診斷 runner：

`backend/scripts/apply_cloud_domain_parity_migration.py`

本 checkpoint 後 release entrypoint：

`backend/scripts/apply_cloud_domain_parity_release.py`

原則：

- fail-closed；
- 不以 drop / truncate / destructive rewrite 隱藏 drift；
- production diagnostics 優先使用 execution / task exit code；
- Cloud Logging 權限不足時不為除錯額外增加 IAM；
- schema repair 必須 additive、idempotent、可稽核；
- production stamp 不在本 checkpoint 執行。

### Diagnostic history

#### 1. Generic contract diagnosis

- main CI #228：PASS；backend 118/118 PASS。
- Deploy Cloud Run #181：FAIL；migration task exit `21`。
- 先前 script-path import failure exit `1` 已由 module mode 排除。

#### 2. Contract subtype split

主要固定分類：

- `20`：database / SQLAlchemy error。
- `21`：revision validation / missing revision table。
- `22`：Alembic subprocess failure。
- `23`：pre-created target-table drift。
- `24`：target schema / PK / FK / index mismatch。
- `25`：preserved table / row-count mismatch。
- `26`：revision row count invalid。
- `27`：unexpected current revision。
- `28`：post-migration revision mismatch。
- `29`：unexpected runtime failure。

Evidence：

- RED commit `58fd8347822fb90baf645b7a90e9589ae100a3dc`；CI #229 如預期 RED。
- GREEN commit `90875fdeadfba93b2a334e7d951a28c10f136eeb`；CI #230 PASS；backend 121/121 PASS。
- Deploy #183：exit `21`。
- CI #232：PASS。
- Deploy #185：exit **21**，確認 production `public.alembic_version` **missing / VERIFIED**。

#### 3. Read-only baseline verification

Baseline revisions `0001–0003`：

- `google_connections`
- `google_oauth_states`
- `execution_logs`
- `projects`

驗證 exact columns / type / nullability / PK / required indexes。

- `30`：baseline tables missing。
- `31`：baseline schema mismatch。
- `32`：baseline verified but unversioned。

Evidence：

- RED CI #233：如預期 RED。
- GREEN commit `6d7261f06fc0c71e23ac22321a4d8d1eb2cc2876`。
- CI #234：PASS；backend 133/133 PASS。
- Deploy #187：exit **23**，證明 unversioned DB 已有至少一張 `0004` target table，因此不能把 production 當成乾淨 `0003` 直接 stamp。

#### 4. Exact target-table presence bitmap

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

- RED commit `4f3ae9e31aceb7b62fd31287fc6007b7a19c3f9c`；CI #235 如預期 RED。
- GREEN commit `1a94cf2141260170af6f7a63067d761c4df1b741`。
- CI #236：PASS；backend 136/136 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #135：PASS。
- Deploy #189：execution `life-assistant-db-migrate-q85fd`；task exit **191**。

`191 = 64 + 127`：七張 `0004` target tables **全部存在 / VERIFIED**。

#### 5. Full unversioned schema path

路徑：

- partial target subset → bitmap fail-closed；
- all seven target tables present → 先驗證 baseline `0001–0003` exact shape，再驗證 `0004` exact schema；
- baseline mismatch → `31`；
- target mismatch → `24`；
- 若 `0001–0004` 全部 exact、但 metadata 缺失 → `33`，仍不自動 stamp。

Evidence：

- RED commit `c6d3dcbf105b41d26883271d93b9b7a325c20189`；CI #237 如預期 RED。
- GREEN commit `0ef210a6a8f953598456151a994e25e142861624`。
- CI #238：PASS；backend 139/139 PASS。
- Firebase Hosting #137：PASS。
- Deploy #191：execution `life-assistant-db-migrate-sqmz4`；task exit **31**。

#### 6. Exact baseline table / mismatch class

- `34` / `35`：`google_connections` shape / index mismatch。
- `36` / `37`：`google_oauth_states` shape / index mismatch。
- `38` / `39`：`execution_logs` shape / index mismatch。
- `40` / `41`：`projects` shape / index mismatch。

Evidence：

- RED commit `1c9f4cea83c506b977da512056149914cf428f02`；CI #239 如預期 RED。
- GREEN commit `b5bf6ddaf98e43d15f40a0f7a26e516c77889723`。
- CI #240：PASS；backend 142/142 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #139：PASS。
- Deploy #193 run `36240544928`；execution `life-assistant-db-migrate-hcx8n`；task exit **41**。

因此已驗證前三張 baseline contract PASS，且 `projects` columns/type/nullability/PK PASS；問題縮小到 projects required indexes。

#### 7. Exact single / combined `projects` index diagnosis

Single mapping：

- `42`：`ix_projects_status` missing。
- `43`：`ix_projects_status` definition mismatch。
- `44`：`ix_projects_name` missing。
- `45`：`ix_projects_name` definition mismatch。

Combined mapping：

- `46`：status missing + name missing。
- `47`：status missing + name definition mismatch。
- `48`：status definition mismatch + name missing。
- `49`：status definition mismatch + name definition mismatch。

Evidence：

- exact-index RED commit `76371e7472e1e3ba18f617dc0dbd0e26a7be62a8`；CI #241 如預期 RED。
- GREEN commit `30f8ac5a70e7e6ec739ab49511c49ec3d75b8f0f`；CI #242 PASS；backend 147/147 PASS。
- Deploy #195：execution `life-assistant-db-migrate-94jpj`；exit **42**。
- combined RED commit `c60cb1b11e8fbbe11a324eab0b4d670287b7c69a`；CI #243 如預期 RED。
- combined GREEN commit `0388efa53822eb7ba762f58e8745fe2348a99091`；CI #244 run `36248619499` PASS；backend 152/152 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #143 run `36248731171`：PASS。
- Deploy Cloud Run #197 run `36248731070`：FAIL；execution `life-assistant-db-migrate-hbjxj`；task exit **46**。

Exit `46` 唯一分類：

- `ix_projects_status`：**missing / FAIL / VERIFIED**。
- `ix_projects_name`：**missing / FAIL / VERIFIED**。
- 兩者都不是 definition mismatch。

### Migration contract vs ORM metadata discrepancy

GitHub Source of Truth 顯示：

- `backend/alembic/versions/20260925_0003_projects.py` 明確建立 `ix_projects_status(status)` 與 `ix_projects_name(name)`；
- 當時 `backend/app/models/project.py` 沒有宣告這兩個 indexes。

Ruling：

- 歷史 migration `20260925_0003` 不回頭改寫；
- ORM metadata 應與既有 Alembic contract 對齊；
- production 只允許 additive repair 缺失 index；同名但 definition 錯誤必須 fail-closed，不自動 drop / replace。

---

## Checkpoint 10 — Guarded pre-stamp projects index reconciliation

### TDD RED

第一輪 contract：

- commit `890420a9f3a4c4149e0641e5fe397b6eb664a8e4`：`test: define projects index reconciliation contract`。
- CI #247：如預期 RED；backend 158 tests，既有 152 tests PASS；新增 tests 因 ORM metadata 未對齊 / reconciliation helper 尚不存在而失敗。

架構收斂：

- commit `70881bfdcac2e9ecb1f6ee63ceeb358b6d18bf55`：測試改綁獨立 `reconcile_projects_indexes.py`。
- commit `e70628eb5fec15bdd2299fa39aea29e38cd7aadf`：`test: require pre-stamp reconciliation release wrapper`。
- CI #249：如預期 RED；workflow 尚未切 release wrapper。

最終 safety RED：

- commit `98775464d47d9a547510aa6aecf94ac39eeeb63e`：`test: enforce reconciliation preflight before ddl`。
- CI #250 run `36250281191`：**如預期 RED**。
- backend 共 **162 tests**；新增 reconciliation / wrapper / ORM contract 因 helper、wrapper、metadata 尚未實作而 FAIL / ERROR；既有功能 tests 與 Alembic offline chain 無新 regression。

### GREEN implementation

ORM metadata alignment：

- commit `cd194f5f2644ddb2bc9d4c73e275dfb78790b5b0`：`fix: align project orm indexes with alembic`。
- `Project.__table_args__` 正式宣告：
  - `Index("ix_projects_status", "status")`
  - `Index("ix_projects_name", "name")`

獨立 reconciliation module：

- commit `48c56c55c17f10475903f992c7ed9de6ff4cc5fb`：`fix: add guarded projects index reconciliation`。
- 新增 `backend/scripts/reconcile_projects_indexes.py`。
- safety contract：
  1. versioned DB 不進 special repair；
  2. 必須是 unversioned DB；
  3. 必須全部七張 `0004` target tables 已存在；
  4. `0001–0003` baseline columns/type/nullability/PK exact；
  5. non-project baseline required indexes exact；
  6. project index 若存在但 definition 不 exact → fail-closed，**DDL 前中止**；
  7. 在任何 DDL 前先跑完整 `0004` `_verify_schema`；
  8. 只對 missing index 執行固定 identifier 的 additive `CREATE INDEX IF NOT EXISTS`；
  9. 使用 transaction；exception rollback；
  10. DDL 後重新讀 catalog 並 exact post-verify；不得用 `IF NOT EXISTS` 隱藏 wrong same-name index。

Release wrapper：

- commit `de4bdf6db674e85844096df413caf7cee879e07c`：`fix: add guarded cloud parity release wrapper`。
- 新增 `backend/scripts/apply_cloud_domain_parity_release.py`。
- 執行順序：guarded reconciliation → existing migration verifier。
- existing migration classifier / stable exit-code contract 保留。
- **不執行 Alembic stamp**。

Workflow：

- commit `bf38d2bf215aaa22379b02a798fbf2b41b7d5c4e`：`fix: run guarded index reconciliation before migration`。
- Cloud Run migration job entrypoint 改為：
  - `python -m scripts.apply_cloud_domain_parity_release`

### GREEN CI evidence

正式 main CI #254：run `36250433287`，release commit `bf38d2bf215aaa22379b02a798fbf2b41b7d5c4e`：**PASS**。

- FastAPI import：PASS。
- Alembic offline chain `0001 -> 0002 -> 0003 -> 0004`：PASS。
- Backend full suite：**162/162 PASS**。
- reconciliation / ORM / workflow tests：PASS。
- deployment-scripts：PASS。
- Flutter analyze：PASS。
- Flutter tests：PASS。
- Flutter Web build：PASS。
- branding verification：PASS。
- Firebase Hosting #153 run `36250556247`：**PASS**，包含 deploy 與 Hosting verification。

### Production evidence — guarded repair reaches full schema equivalence

Deploy Cloud Run #207：

- run：`36250556257`。
- release commit：`bf38d2bf215aaa22379b02a798fbf2b41b7d5c4e`。
- migration execution：`life-assistant-db-migrate-2jbnh`。
- migration task：`life-assistant-db-migrate-2jbnh-task0`。
- execution spec 已驗證使用：`python -m scripts.apply_cloud_domain_parity_release`。
- task exit：**33**。
- Cloud Run execution condition 同樣明確指出 task failed with exit code **33**。

Exit `33` 的固定定義：**revisions `0001–0004` schema contract 全部 exact，但 `alembic_version` metadata 仍不存在**。

由於 Deploy #197 在 repair 前已明確證明兩個 projects indexes 都 missing（exit 46），而本版 release wrapper 只有在完整 fail-closed preflight 通過後才建立 missing indexes，再交回既有完整 verifier；因此 Deploy #207 能到達 exit 33，已正式驗證 repair 後：

- `ix_projects_status`：**present + exact / PASS / VERIFIED**。
- `ix_projects_name`：**present + exact / PASS / VERIFIED**。
- `google_connections` baseline schema：**exact / PASS / VERIFIED**。
- `google_oauth_states` baseline schema + indexes：**exact / PASS / VERIFIED**。
- `execution_logs` baseline schema + indexes：**exact / PASS / VERIFIED**。
- `projects` baseline columns/type/nullability/PK + required indexes：**exact / PASS / VERIFIED**。
- 七張 `0004` target tables 的 columns / PK / FK / required indexes：**exact / PASS / VERIFIED**。
- production `0001–0004` schema representation：**exact / PASS / VERIFIED**。
- `public.alembic_version`：**still missing / FAIL / VERIFIED**。

Cloud Logging read 仍 `PERMISSION_DENIED`；本 checkpoint 未增加 IAM。Exit code 與 execution/task status 已足以形成 non-sensitive runtime evidence。

### Production mutation record

本 checkpoint 對 production 的唯一允許 schema mutation 是 guarded additive repair：

- 建立缺失的 `ix_projects_status`；
- 建立缺失的 `ix_projects_name`。

未執行：

- `alembic stamp`；
- create / update `alembic_version`；
- drop / truncate / recreate table；
- drop / replace existing index；
- production data mutation；
- IAM / Service Account 權限變更；
- secret rotation。

### Current production state

- Schema revisions `0001–0004` physical contract：**PASS / VERIFIED**。
- Alembic version metadata：**FAIL — missing / VERIFIED**。
- Cloud Run migration gate：**FAIL by design**，因 exit 33 仍視為不可 release。
- Cloud Run service deployment（本 release）：**SKIPPED / blocked**。
- `/health`（本 release）：**NOT VERIFIED**。
- `/ready`（本 release）：**NOT VERIFIED**。
- unauthenticated API protection（本 release）：**NOT VERIFIED**。
- authenticated Notes / Habits / Shopping / Templates runtime CRUD：**NOT VERIFIED**。
- Project delete guard runtime acceptance：**NOT VERIFIED**。
- Historical SQLite → PostgreSQL backfill：**NOT VERIFIED**。

Task 8 目前：**PARTIAL**。

### 下一個安全 checkpoint

下一步是 **Alembic metadata bootstrap / stamp safety design + TDD**：

1. 只允許在 exit-33 等價條件成立時 bootstrap metadata；
2. 必須再次完整驗證 `0001–0004` exact schema；
3. 必須明確確認 `alembic_version` 仍不存在；
4. bootstrap 只允許建立 Alembic metadata 並標記 `20260926_0004`，不得重跑 migrations / 改 business tables / 改 data；
5. bootstrap 後再次讀回 revision 與完整 schema；
6. 再由 normal migration runner 驗證 `TARGET_REVISION` + schema exact；
7. production 實際 stamp / metadata bootstrap **不在本 checkpoint 自動執行**；在真正寫入 production Alembic metadata 前必須取得使用者明確確認；
8. metadata 恢復且 migration gate PASS 後，才進 Cloud Run service deploy 與 `/health` / `/ready` / auth/API runtime acceptance。

---

## 執行規則

1. 一次只完成一個 Task / checkpoint。
2. checkpoint 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 checkpoint。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
