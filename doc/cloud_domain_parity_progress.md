# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 8 projects required-index drift diagnosis）

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

## Task 1 — PostgreSQL target models + Alembic migration

狀態：**PASS（implementation / tests / formal main CI）**

- 建立 Notes / Habits / Shopping / Templates ORM target models。
- Alembic revision：`20260926_0004`，`down_revision=20260925_0003`。
- model contract tests：6/6 PASS。
- Python compile：PASS。
- Task 8 formal main CI 已持續覆蓋本批 backend regression。
- Runtime DB metadata / historical SQLite backfill：NOT VERIFIED。

## Task 2 — Notes API parity

狀態：**PASS（implementation / tests / formal main CI）**

- Notes CRUD、bidirectional links、delete link cleanup、legacy nullable read。
- `note.create` / `note.update` / `note.delete` / `note.link`。
- 正式 main CI regression：PASS。
- PostgreSQL runtime CRUD：NOT VERIFIED。

## Task 3 — Habits API parity

狀態：**PASS（implementation / tests / formal main CI）**

- active-only list、create/get/patch、append completion、descending history。
- 不新增 delete / activate / deactivate。
- `habit.create` / `habit.update` / `habit.complete`。
- 正式 main CI regression：PASS。
- PostgreSQL runtime completion persistence：NOT VERIFIED。

## Task 4 — Shopping API parity

狀態：**PASS（implementation / tests / formal main CI）**

- Shopping List create/read、item create、nested sorted read、`is_done` toggle。
- `project_id` 原樣保存，本批不做 project existence validation。
- 不新增 delete / quantity / price / store。
- `shopping_list.create` / `shopping_item.create` / `shopping_item.toggle`。
- 正式 main CI regression：PASS。
- PostgreSQL runtime Shopping persistence：NOT VERIFIED。

## Task 5 — Templates API parity

狀態：**PASS（implementation / tests / formal main CI）**

- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`
- `payload_json` 維持 opaque `TEXT` string，不 parse / normalize / reserialize。
- 不新增 template delete / apply / version-history endpoint。
- mutation action types：`template.create` / `template.update`。
- provider 固定 `life_assistant`。
- execution summaries 不包含 `payload_json` 本文。
- 正式 main CI regression：PASS。
- PostgreSQL runtime Template persistence / opaque payload round-trip：NOT VERIFIED。

## Task 6 — Project delete guard

狀態：**PASS（implementation / tests / formal main CI）**

- `DELETE /api/v1/projects/{project_id}` 在 Project 被 Task / Note / Shopping List 參照時回 `409`。
- guard 發生在 `project.delete` execution record 建立之前；被阻擋的刪除不建立 delete execution record。
- 本 Task 不新增 Project FK、cascade 或跨 domain destructive behavior。
- 正式 main CI regression：PASS。
- PostgreSQL runtime Project delete guard acceptance：NOT VERIFIED。

## Task 7 — Full backend verification

狀態：**PASS（implementation / tests / CI verification）**

- FastAPI import：PASS。
- Alembic offline chain：PASS，包含 `20260925_0003 -> 20260926_0004`。
- Backend full suite：PASS。
- Flutter analyze / tests / Web build / branding verification：PASS。
- GCP deployment scripts syntax：PASS。
- Historical SQLite → PostgreSQL backfill：NOT VERIFIED；本批未建立/執行 importer，不宣稱 PASS。

## Task 8 — CI / deployment / runtime acceptance

狀態：**PARTIAL — implementation / tests / formal main CI PASS；production migration contract FAIL；service/runtime blocked**

### Implementation / CI evidence

- 修正 deploy workflow 在批次 fast-forward 時可能錯誤跳過 backend release 的問題。
- Cloud Run migration job：`life-assistant-db-migrate`，在 Cloud Run service deploy 前先驗證 / 執行 migration contract。
- migration runner：`backend/scripts/apply_cloud_domain_parity_migration.py`。
- runner 對 revision / pre-created target tables / target schema / preserved table row counts 採 fail-closed；不以 stamp / drop / truncate 隱藏 drift。
- migration job 使用 module mode：`python -m scripts.apply_cloud_domain_parity_migration`。
- 加入 execution / task exit-code diagnostics；在既有 Logging IAM 不足時仍能取得非敏感 production evidence。
- 本 Task 未增加 Cloud Logging IAM 權限。

### Diagnostic history

#### 1. Generic contract diagnosis

- 正式 main CI #228：PASS；backend 118/118 PASS。
- Deploy Cloud Run #181：FAIL；migration task exit `21`。
- 先前 script-path 啟動造成 classifier 前 import failure 的 exit `1` 已透過 module mode 排除。

#### 2. Contract subtype split

exit mapping：

- `20`：database / SQLAlchemy error。
- `21`：revision validation failure。
- `22`：Alembic subprocess failure。
- `23`：pre-created target table drift。
- `24`：target schema / PK / FK / index mismatch。
- `25`：preserved table / row-count mismatch。
- `29`：unexpected runtime failure。

TDD evidence：

- RED commit：`58fd8347822fb90baf645b7a90e9589ae100a3dc`。
- CI #229：backend 如預期 RED。
- GREEN commit：`90875fdeadfba93b2a334e7d951a28c10f136eeb`。
- CI #230：PASS；backend 121/121 PASS。
- Deploy Cloud Run #183：FAIL；task exit `21`，確認 production failure 在 revision validation。

#### 3. Revision-state subtype split

revision-state exit mapping：

- `21`：`alembic_version` table missing。
- `26`：`alembic_version` row count invalid。
- `27`：unexpected current revision。
- `28`：post-migration revision mismatch。

- CI #232：PASS。
- Deploy Cloud Run #185：FAIL，task exit **21**。
- Production evidence：`public.alembic_version` **不存在**。
- 未執行 stamp、revision-row edit 或其他 DB metadata 寫入。

#### 4. Read-only baseline verification

針對 unversioned production DB，加入 revisions `0001–0003` baseline read-only validation：

- baseline tables：`google_connections`、`google_oauth_states`、`execution_logs`、`projects`。
- 驗證 exact columns / type / nullability / primary key / required indexes。
- `30`：baseline tables missing。
- `31`：baseline schema mismatch。
- `32`：baseline verified but unversioned。

TDD / CI：

- RED CI #233：如預期失敗。
- GREEN commit：`6d7261f06fc0c71e23ac22321a4d8d1eb2cc2876`。
- CI #234：PASS；backend 133/133 PASS。
- Deploy Cloud Run #187：FAIL；task exit **23**。

因 verifier 當時先檢查 target-table presence，exit 23 證明 unversioned DB 中至少一張 `0004` target table 已存在，因此不能把 DB 當成乾淨 `0003` baseline 直接 stamp。

#### 5. Exact target-table presence bitmap

為在不增加 Logging IAM 的前提下確認 target table presence，加入穩定 bitmap：

- bit 0 `notes`
- bit 1 `note_links`
- bit 2 `habits`
- bit 3 `habit_completions`
- bit 4 `shopping_lists`
- bit 5 `shopping_items`
- bit 6 `templates`
- diagnostic exit = `64 + bitmap`

TDD / CI：

- RED commit：`4f3ae9e31aceb7b62fd31287fc6007b7a19c3f9c`；CI #235 如預期 RED。
- GREEN commit：`1a94cf2141260170af6f7a63067d761c4df1b741`。
- CI #236：PASS；backend 136/136 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #135：PASS。
- Deploy Cloud Run #189：FAIL；execution `life-assistant-db-migrate-q85fd`；task exit **191**。

`191 = 64 + 127`，七個 bits 全部存在，因此 production 已驗證：

- `alembic_version` 不存在；
- `notes`、`note_links`、`habits`、`habit_completions`、`shopping_lists`、`shopping_items`、`templates` 七張 target tables 全部存在。

但 table presence 不等於 schema exact match，因此仍不能 stamp。

#### 6. Full unversioned schema path

調整診斷路徑：

- partial target subset：仍 fail-closed，回 bitmap；
- all seven target tables present：先驗證 `0001–0003` baseline exact shape，再驗證 `0004` target exact shape；
- baseline mismatch：exit `31`；
- target mismatch：exit `24`；
- 若 `0001–0004` 全部 exact match、但 metadata 缺失：exit `33`，仍不自動 stamp。

TDD / CI：

- RED commit：`c6d3dcbf105b41d26883271d93b9b7a325c20189`；CI #237 backend 如預期 FAIL。
- GREEN commit：`0ef210a6a8f953598456151a994e25e142861624`。
- CI #238：PASS；backend 139/139 PASS。
- Firebase Hosting #137：PASS。
- Deploy Cloud Run #191：FAIL；execution `life-assistant-db-migrate-sqmz4`；task exit **31**。

此時 production root state 確認為 baseline schema mismatch，但 exact table / mismatch 類型仍未知。

#### 7. Exact baseline table + mismatch-class subtype

為把 generic exit `31` 再唯讀細分，加入固定 subtype mapping：

- `34`：`google_connections` columns/type/nullability/PK shape mismatch。
- `35`：`google_connections` required-index mismatch。
- `36`：`google_oauth_states` columns/type/nullability/PK shape mismatch。
- `37`：`google_oauth_states` required-index mismatch。
- `38`：`execution_logs` columns/type/nullability/PK shape mismatch。
- `39`：`execution_logs` required-index mismatch。
- `40`：`projects` columns/type/nullability/PK shape mismatch。
- `41`：`projects` required-index mismatch。

`31` 保留作 generic baseline-schema fallback；`34–41` 均低於 `64+bitmap` 診斷區間。

TDD / CI evidence：

- RED commit：`1c9f4cea83c506b977da512056149914cf428f02`（`test: identify baseline schema drift subtype`）。
- CI #239 backend：**如預期 RED**；142 tests 中新增的 9 個 subtype assertions 因新 exception / mapping 尚未實作而 ERROR；既有 contract tests、Alembic validation、deployment-scripts 未出現新 regression。
- GREEN commit：`b5bf6ddaf98e43d15f40a0f7a26e516c77889723`（`fix: classify baseline schema drift subtype`）。
- CI #240：**PASS**。
- Backend full suite：**142/142 PASS**。
- Alembic offline chain：PASS，`0001 -> 0002 -> 0003 -> 0004`。
- Flutter analyze / tests / Web build / branding verification：PASS。
- deployment-scripts：PASS。
- Firebase Hosting #139：**PASS**。

### Latest production evidence — `projects` required-index mismatch

Deploy Cloud Run #193：**FAIL**，run ID `36240544928`，release commit `b5bf6ddaf98e43d15f40a0f7a26e516c77889723`。

- Migration execution：`life-assistant-db-migrate-hcx8n`。
- Migration task：`life-assistant-db-migrate-hcx8n-task0`。
- Migration task `status.lastAttemptResult.exitCode`：**41**。
- Cloud Run execution condition 同樣明確指出 task failed with exit code `41`。
- `41` 的唯一分類：**`projects` required-index mismatch**。
- Logging read 仍 `PERMISSION_DENIED`；未變更 IAM。

因 baseline verifier 的固定執行順序為：

1. `google_connections` shape → required indexes；
2. `google_oauth_states` shape → required indexes；
3. `execution_logs` shape → required indexes；
4. `projects` shape → required indexes；

而 production 最後在 `projects` required-index check 才回 `41`，因此本輪可進一步確認：

- `google_connections` columns/type/nullability/PK：**PASS / VERIFIED**。
- `google_connections` required indexes：目前 contract 為空集合，因此無額外 required-index failure。
- `google_oauth_states` columns/type/nullability/PK：**PASS / VERIFIED**。
- `google_oauth_states` required indexes：**PASS / VERIFIED**。
- `execution_logs` columns/type/nullability/PK：**PASS / VERIFIED**。
- `execution_logs` required indexes：**PASS / VERIFIED**。
- `projects` columns/type/nullability/PK：**PASS / VERIFIED**。
- `projects` required indexes：**FAIL / VERIFIED**。

目前 `projects` contract 要求：

- `ix_projects_status` definition 含 `(status)`；
- `ix_projects_name` definition 含 `(name)`。

exit `41` 只證明上述至少一個 required index **missing 或 definition mismatch**；目前尚不能從 exit code 判定究竟是 `ix_projects_status`、`ix_projects_name`，或兩者同時有問題。

因 baseline validation 在 target `0004` schema validation 之前 fail，七張 `0004` target tables 的 **exact schema equivalence 仍 NOT VERIFIED**。

### Current production state

- `public.alembic_version`：**missing / VERIFIED**。
- 七張 `0004` target tables：**all present / VERIFIED**。
- `google_connections` baseline shape：**PASS / VERIFIED**。
- `google_oauth_states` baseline shape + required indexes：**PASS / VERIFIED**。
- `execution_logs` baseline shape + required indexes：**PASS / VERIFIED**。
- `projects` baseline columns/type/nullability/PK：**PASS / VERIFIED**。
- `projects` required indexes：**FAIL / VERIFIED**。
- exact failing projects index：**NOT VERIFIED**。
- `0004` target schema exact equivalence：**NOT VERIFIED**。

### Safety / mutation record

本輪 production diagnosis 全程維持 read-only contract inspection：

- 未執行 `alembic stamp`。
- 未建立或修改 `alembic_version`。
- 未 drop / truncate / recreate production table。
- 未新增 / 修改 production index。
- 未改 production data。
- 未增加 Cloud Logging IAM 權限。

因此目前仍 **禁止把 production DB stamp 成 `20260925_0003` 或 `20260926_0004`**；現有 evidence 尚未證明完整 schema equivalence。

### 尚未完成的 Task 8 acceptance

- Cloud Run service deployment：**FAIL / blocked by migration gate**。
- `/health`：本次 release **NOT VERIFIED**。
- `/ready`：本次 release **NOT VERIFIED**。
- unauthenticated API protection：本次 release **NOT VERIFIED**。
- authenticated Notes / Habits / Shopping / Templates runtime CRUD：**NOT VERIFIED**。
- Project delete guard runtime acceptance：**NOT VERIFIED**。
- historical SQLite → PostgreSQL backfill：**NOT VERIFIED**；本批沒有 importer execution evidence，不宣稱 PASS。

Task 8 目前：**PARTIAL**，不得標示 DONE。

下一個安全 checkpoint：繼續唯讀細分 `projects` required-index mismatch，至少辨識 `ix_projects_status` 與 `ix_projects_name` 哪一個失敗；如有必要再區分 missing vs definition mismatch。取得 exact index drift 後，才設計 additive repair migration。不得先 stamp 或直接修改 production schema。

## 執行規則

1. 一次只完成一個 Task / checkpoint。
2. checkpoint 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 checkpoint。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
