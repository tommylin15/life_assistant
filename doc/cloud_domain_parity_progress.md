# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 8 production baseline schema mismatch diagnosis）

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
- Task 8 formal main CI #228 已覆蓋本批 backend regression，CI：PASS。
- Runtime DB revision/table state、historical SQLite backfill：NOT VERIFIED。

## Task 2 — Notes API parity

狀態：**PASS（implementation / tests / formal main CI）**

- Notes CRUD、bidirectional links、delete link cleanup、legacy nullable read。
- `note.create` / `note.update` / `note.delete` / `note.link`。
- Notes tests：12/12 PASS；Task 1–2 regression：18/18 PASS。
- Task 8 formal main CI #228：PASS。
- PostgreSQL runtime CRUD：NOT VERIFIED。

## Task 3 — Habits API parity

狀態：**PASS（implementation / tests / formal main CI）**

- active-only list、create/get/patch、append completion、descending history。
- 不新增 delete / activate / deactivate。
- `habit.create` / `habit.update` / `habit.complete`。
- Habits tests：14/14 PASS；Task 1–3 regression：32/32 PASS。
- Task 8 formal main CI #228：PASS。
- PostgreSQL runtime completion persistence：NOT VERIFIED。

## Task 4 — Shopping API parity

狀態：**PASS（implementation / tests / formal main CI）**

- Shopping List create/read、item create、nested sorted read、`is_done` toggle。
- `project_id` 原樣保存，本批不做 project existence validation。
- 不新增 delete / quantity / price / store。
- `shopping_list.create` / `shopping_item.create` / `shopping_item.toggle`。
- Shopping tests：14/14 PASS；Shopping + execution-log：17/17 PASS；Task 1–4 regression：49/49 PASS。
- Task 8 formal main CI #228：PASS。
- PostgreSQL runtime Shopping persistence：NOT VERIFIED。

## Task 5 — Templates API parity

狀態：**PASS（implementation / tests / formal main CI）**

本 Task 建立 / 更新：

- `backend/app/api/templates.py`
- `backend/app/models/schemas.py`：新增 `TemplateCreate` / `TemplateUpdate` / `TemplateOut`
- `backend/app/main.py`：註冊 `/api/v1/templates`
- `backend/tests/test_templates.py`

API contract：

- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`

重要行為：

- Create 必須提供 `name` / `template_type` / `payload_json`。
- PATCH 只允許 `name` / `template_type` / `payload_json`；空 PATCH 與三欄 explicit null 都拒絕。
- request 長度限制與 DB 欄位一致：name 500、template_type 64。
- `payload_json` 保持 opaque `TEXT` string；不 `json.loads`、不 serialize、不 normalize、不重排 JSON key。
- JSON-like payload 與任意非 JSON 字串皆 lossless round-trip。
- 不新增 template delete / apply / version-history endpoint。
- mutation action types：`template.create` / `template.update`。
- provider 固定 `life_assistant`。
- execution summaries 不包含 `payload_json` 本文。

TDD / verification evidence：

- RED：Template schemas、router、main registration 尚不存在時，contract tests 如預期失敗。
- GREEN：Templates tests 12/12 PASS。
- Templates + execution-log regression（warnings-as-errors）：15/15 PASS。
- Full Task 1–5 regression（warnings-as-errors）：61/61 PASS。
- Python compile：PASS。
- JSON parse/serialize static scan：PASS。
- Task 8 formal main CI #228：PASS。

尚未驗證：

- Cloud Run deployment：NOT VERIFIED（Task 8 migration gate 先失敗，因此 service release 未執行）。
- PostgreSQL runtime Template create/update/read persistence：NOT VERIFIED。
- opaque payload runtime round-trip：NOT VERIFIED。
- execution log runtime visibility：NOT VERIFIED。

## Task 6 — Project delete guard

狀態：**PASS（implementation / tests / formal main CI）**

本 Task 更新：

- `backend/app/api/projects.py`
- `backend/tests/test_projects.py`

Delete guard contract：

- `DELETE /api/v1/projects/{project_id}` 在 Project 被 Task 參照時回 `409`。
- Project 被 Note 參照時回 `409`。
- Project 被 Shopping List 參照時回 `409`。
- 三類都無關聯時，維持既有 Project delete path。
- guard 發生在 `project.delete` execution record 建立之前；被阻擋的刪除不建立 delete execution record，也不執行 `db.delete(project)`。
- 每一類只用 `select(<Entity>.id).where(<Entity>.project_id == project_id).limit(1)` 做存在性查詢。
- 本 Task 不新增 Project FK、cascade 或跨 domain destructive behavior。

TDD / verification evidence：

- RED commit：`3680844cb81b1be6c3529ba76ed8895e9ee28f47`。
- RED GitHub Actions CI run #206 / backend：Task guard PASS；linked Note、linked Shopping List、no-linked 三個新案例如預期 FAIL；backend 共 104 tests，3 failures。
- GREEN implementation commit：`c7a2cdb2062aaa7f9ef43a079c6213c92d3fd4a5`。
- GREEN GitHub Actions CI run #207 / backend：import PASS、Alembic offline chain PASS、backend full suite 104/104 PASS。
- Task 6 四個 Project delete guard cases：4/4 PASS。
- Task 8 formal main CI #228：PASS。

Task 6 尚未驗證：

- Cloud Run deployment：NOT VERIFIED（Task 8 migration gate 先失敗）。
- PostgreSQL runtime Project delete guard acceptance：NOT VERIFIED。

## Task 7 — Full backend verification

狀態：**PASS（pre-main implementation / tests / CI verification）**

驗證內容：

- FastAPI import：PASS。
- Alembic offline chain：PASS，包含 `20260925_0003 -> 20260926_0004`。
- Backend full suite：104/104 PASS（Task 7 時點）。
- Flutter analyze：PASS。
- Flutter tests：PASS。
- Flutter Web build：PASS。
- Branding web-build verification：PASS。
- GCP deployment scripts syntax：PASS。
- GitHub Actions PR CI #208：backend / flutter / deployment-scripts 全部 PASS。
- Task 7 final documentation head GitHub Actions PR CI #209：backend / flutter / deployment-scripts 全部 PASS。

Contract review：

- Notes endpoints、legacy nullable read、link idempotency/self-link/delete cleanup：符合核准 spec。
- Habits active-only list、append-only completions、無 delete/activate/deactivate mutation：符合核准 spec。
- Shopping list/item endpoint 與 `is_done`-only PATCH：符合核准 spec。
- Template `payload_json` 維持 opaque string，無 delete/apply/versioning：符合核准 spec。
- 新 domain mutation provider 固定 `life_assistant`，action types 與 spec 一致。
- Note body / Template payload 不進 execution summary。
- Project delete guard 對 Task / Note / Shopping List 皆為 409，無新增 FK/cascade。
- 未發現 Tasks 1–6 需要額外修正的 defect；Task 7 沒有修改 production code。

環境限制與狀態分類：

- 目前 ChatGPT container 無法解析 `github.com`，因此無法在 container 另跑一份 local clone；這一層不冒充 local PASS。
- 上述可重跑驗證由 GitHub Actions 對 Task 1–7 最終 branch 執行並取得 PASS。
- Historical SQLite → PostgreSQL backfill：NOT VERIFIED；本批仍未建立/執行 importer，不宣稱 PASS。

## Task 8 — CI / deployment / runtime acceptance

狀態：**PARTIAL — implementation / tests / formal main CI PASS；production migration contract FAIL；service/runtime blocked**

### Implementation / CI evidence

- 修正原 deploy workflow 只檢查 `HEAD^..HEAD`、在批次 fast-forward 時可能錯誤跳過 backend release 的問題。
- 新增 Cloud Run migration job `life-assistant-db-migrate`，在 Cloud Run service deploy 前先驗證 / 執行 Alembic target migration。
- migration runner：`backend/scripts/apply_cloud_domain_parity_migration.py`。
- runner 對 revision / pre-created target tables / target schema / preserved table row counts 採 fail-closed；不以 stamp / drop / truncate 隱藏 drift。
- migration job 使用 module mode：`python -m scripts.apply_cloud_domain_parity_migration`。
- 加入 migration execution / task diagnostics；在既有 Logging IAM 不足時，仍可用 Cloud Run task exit code做非敏感診斷；本 Task 未增加 Cloud Logging IAM 權限。

### Diagnostic history

#### 1. Generic contract diagnosis

- 正式 main CI #228：PASS；backend 118/118 PASS。
- Deploy Cloud Run #181：FAIL；migration task exit `21`。
- 先前 Python script-path 啟動造成 classifier 前 import failure 的 exit `1` 已透過 module mode 排除。

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

- RED commit：`58fd8347822fb90baf645b7a90e9589ae100a3dc`（`test: split migration contract failure classes`）。
- CI #229 backend 如預期 RED：121 tests 中 7 errors。
- GREEN commit：`90875fdeadfba93b2a334e7d951a28c10f136eeb`（`fix: expose migration contract failure subtypes`）。
- CI #230：backend / flutter / deployment-scripts 全部 PASS；backend 121/121 PASS。
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
- 因此排除 row-count / unexpected-current / post-migration mismatch。
- 未執行 stamp、revision row edit 或其他 DB metadata 寫入。

#### 4. Read-only baseline verification

為避免對 unversioned production DB 猜測式 stamp，加入 revisions `0001–0003` baseline table read-only validation：

- baseline tables：`google_connections`、`google_oauth_states`、`execution_logs`、`projects`。
- 驗證 exact columns / type / nullability / primary key / required indexes。
- `30`：baseline tables missing。
- `31`：baseline schema mismatch。
- `32`：baseline verified but unversioned。

TDD / CI：

- RED CI #233：如預期失敗。
- GREEN commit：`6d7261f06fc0c71e23ac22321a4d8d1eb2cc2876`（`fix: verify unversioned migration baseline`）。
- CI #234：PASS；backend 133/133 PASS。
- Deploy Cloud Run #187：FAIL；task exit **23**。

由於當時 verifier 先檢查 target-table presence，exit 23 證明 unversioned DB 中至少一張 `0004` target table 已存在；因此不可能把 DB 當成乾淨 `0003` baseline 直接 stamp。

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
- GREEN commit：`1a94cf2141260170af6f7a63067d761c4df1b741`（`fix: encode unversioned target table drift`）。
- CI #236：PASS；backend 136/136 PASS；Alembic / Flutter / deployment-scripts PASS。
- Firebase Hosting #135：PASS。
- Deploy Cloud Run #189：FAIL；migration execution `life-assistant-db-migrate-q85fd`；task `life-assistant-db-migrate-q85fd-task0`；task exit **191**。

`191 = 64 + 127`，127 七個 bits 全部存在，因此 production 已驗證：

- `alembic_version` 不存在；
- `notes`、`note_links`、`habits`、`habit_completions`、`shopping_lists`、`shopping_items`、`templates` **七張 target tables 全部存在**。

但「table presence」不等於「schema exact match」，因此仍不能 stamp。

#### 6. Full unversioned schema path

下一個 checkpoint 將原本「看到任何 target table 就停止」的短路調整成：

- partial target subset：仍 fail-closed，回 bitmap；
- all seven target tables present：先驗證 `0001–0003` baseline exact shape，再驗證 `0004` target exact shape；
- baseline mismatch 維持 exit `31`；
- target mismatch 維持 exit `24`；
- 若 `0001–0004` 全部 exact match、但 metadata 缺失，才回新的 diagnostic exit `33`，且仍不自動 stamp。

TDD evidence：

- RED commit：`c6d3dcbf105b41d26883271d93b9b7a325c20189`（`test: verify full unversioned schema path`）。
- CI #237：backend 在 `Test backend` 如預期 FAIL；Alembic validation 與 deployment-scripts PASS。
- GREEN commit：`0ef210a6a8f953598456151a994e25e142861624`（`fix: verify full unversioned schema`）。
- CI #238：**PASS**。
- Backend full suite：**139/139 PASS**。
- Alembic offline chain：PASS，`0001 -> 0002 -> 0003 -> 0004`。
- deployment-scripts：PASS。
- Flutter analyze / tests / Web build / branding verification：PASS。
- Firebase Hosting #137：**PASS**。

### Latest production evidence — baseline schema mismatch

Deploy Cloud Run #191：**FAIL**，run ID `36238540861`，release commit `0ef210a6a8f953598456151a994e25e142861624`。

- Migration execution：`life-assistant-db-migrate-sqmz4`。
- Migration task：`life-assistant-db-migrate-sqmz4-task0`。
- Migration task `status.lastAttemptResult.exitCode`：**31**。
- Cloud Run execution condition 同樣明確指出 task failed with exit code `31`。
- `31` 的唯一分類：**baseline schema mismatch**。
- 因 validator 已先確認 baseline table presence 才會進 shape check，因此這不是「baseline table missing」的 exit `30`。
- 因 baseline 驗證先於 `0004` target shape 驗證，這次 exit `31` 尚不能判定 `0004` target schema 是否 exact match。
- Logging read 仍 `PERMISSION_DENIED`；未變更 IAM。

目前可以確定的 production state：

- `public.alembic_version`：**missing / VERIFIED**。
- 七張 `0004` target tables：**all present / VERIFIED**。
- `0001–0003` baseline tables：能進入 baseline shape validation，因此 baseline presence 未觸發 exit 30；**至少一個 baseline table 的 columns/type/nullability/PK/required-index contract 不一致 / VERIFIED**。
- baseline mismatch 的 exact table / exact field / exact index：**NOT VERIFIED**。
- `0004` target schema exact equivalence：**NOT VERIFIED**（因 baseline check 先 fail）。

### Safety / mutation record

本輪 production diagnosis 全程維持 read-only contract inspection：

- 未執行 `alembic stamp`。
- 未建立或修改 `alembic_version`。
- 未 drop / truncate / recreate production table。
- 未改 production data。
- 未增加 Cloud Logging IAM 權限。

因此目前 **禁止把 production DB stamp 成 `20260925_0003` 或 `20260926_0004`**；現有 evidence 不支持這種 metadata assertion。

### 尚未完成的 Task 8 acceptance

- Cloud Run service deployment：**FAIL / blocked by migration gate**。
- `/health`：本次 release **NOT VERIFIED**。
- `/ready`：本次 release **NOT VERIFIED**。
- unauthenticated API protection：本次 release **NOT VERIFIED**。
- authenticated Notes / Habits / Shopping / Templates runtime CRUD：**NOT VERIFIED**。
- Project delete guard runtime acceptance：**NOT VERIFIED**。
- historical SQLite → PostgreSQL backfill：**NOT VERIFIED**；本批沒有 importer execution evidence，不宣稱 PASS。

Task 8 目前：**PARTIAL**，不得標示 DONE。

下一個安全診斷步驟：把 exit `31` 再做唯讀細分，至少能由 Cloud Run task exit code辨識「哪一張 baseline table」以及「columns/type/nullability/PK vs required index」哪一類不一致；先取得 production exact drift evidence，再決定是否需要 additive repair migration。不得先 stamp 或直接修改 production schema。

## 執行規則

1. 一次只完成一個 Task / checkpoint。
2. checkpoint 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 checkpoint。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
