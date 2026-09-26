# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-27（Task 8 `projects.status` missing server-default diagnosis）

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

Task 8 整體狀態：**PARTIAL**。正式 main CI 已通過；production physical schema 的既有 structural verifier 已可到 exit `33`，但更嚴格的 Alembic metadata bootstrap preflight 已精確確認 `projects.status` **缺少** Alembic contract 所需的 DB server default `active`，因此目前 **NOT STAMP-READY**。不得標示 DONE。

---

## Tasks 1–7 — implementation / tests / CI

### Task 1 — PostgreSQL target models + Alembic migration

- 狀態：**PASS（implementation / tests / formal main CI）**。
- 建立 Notes / Habits / Shopping / Templates ORM target models。
- Alembic revision：`20260926_0004`，`down_revision=20260925_0003`。
- model contract tests、Alembic offline chain：PASS。
- Historical SQLite → PostgreSQL backfill：NOT VERIFIED。

### Task 2 — Notes API parity

- 狀態：**PASS（implementation / tests / formal main CI）**。
- Notes CRUD、bidirectional links、delete link cleanup、legacy nullable read。
- mutation actions：`note.create` / `note.update` / `note.delete` / `note.link`。
- PostgreSQL runtime CRUD：NOT VERIFIED。

### Task 3 — Habits API parity

- 狀態：**PASS（implementation / tests / formal main CI）**。
- active-only list、create/get/patch、append completion、descending history。
- mutation actions：`habit.create` / `habit.update` / `habit.complete`。
- PostgreSQL runtime completion persistence：NOT VERIFIED。

### Task 4 — Shopping API parity

- 狀態：**PASS（implementation / tests / formal main CI）**。
- Shopping List create/read、item create、nested sorted read、`is_done` toggle。
- mutation actions：`shopping_list.create` / `shopping_item.create` / `shopping_item.toggle`。
- PostgreSQL runtime persistence：NOT VERIFIED。

### Task 5 — Templates API parity

- 狀態：**PASS（implementation / tests / formal main CI）**。
- create/list/get/patch；`payload_json` 維持 opaque `TEXT` string。
- mutation actions：`template.create` / `template.update`。
- PostgreSQL runtime opaque payload round-trip：NOT VERIFIED。

### Task 6 — Project delete guard

- 狀態：**PASS（implementation / tests / formal main CI）**。
- Project 被 Task / Note / Shopping List 參照時 delete 回 `409`。
- PostgreSQL runtime Project delete guard acceptance：NOT VERIFIED。

### Task 7 — Full backend verification

- 狀態：**PASS（implementation / tests / CI）**。
- FastAPI import、Alembic offline chain、Backend full suite、Flutter analyze/tests/Web build/branding、deployment scripts：PASS。

---

## Task 8 — CI / deployment / runtime acceptance

狀態：**PARTIAL — implementation / tests / formal main CI PASS；production metadata bootstrap preflight FAIL；service/runtime blocked**。

Cloud Run migration job：`life-assistant-db-migrate`。

目前 release entrypoint：

`backend/scripts/apply_cloud_domain_parity_release.py`

核心原則：

- fail-closed；
- diagnostics 優先使用 execution / task exit code；
- Logging 權限不足時不為除錯額外增加 IAM；
- schema repair 必須 additive、idempotent、可稽核；
- 不以 drop / truncate / destructive rewrite 隱藏 drift；
- production Alembic metadata bootstrap / stamp 必須在更嚴格 preflight 全 PASS 後，且於實際寫入前取得使用者明確確認。

### Diagnostic history summary

#### Revision / target presence

- CI #228 PASS；Deploy #181 exit `21`。
- module-mode 修正後，Deploy #185 exit `21`：`public.alembic_version` **missing / VERIFIED**。
- baseline verifier：CI #234 PASS；Deploy #187 exit `23`，確認 production 不是乾淨 0003 baseline。
- target presence bitmap：CI #236 PASS；Deploy #189 execution `life-assistant-db-migrate-q85fd` exit **191**。
- `191 = 64 + 127`：七張 `0004` target tables 全部存在 / VERIFIED。

#### Full structural schema diagnosis

- Full unversioned schema path：CI #238 PASS；Deploy #191 exit `31`，定位 baseline mismatch。
- Baseline subtype：CI #240 PASS；Deploy #193 exit `41`，定位 `projects` required indexes。
- Single index subtype：CI #242 PASS；Deploy #195 exit `42`，先定位 `ix_projects_status` missing。
- Combined index diagnosis：CI #244 PASS；Deploy #197 execution `life-assistant-db-migrate-hbjxj` exit **46**。
- Exit `46`：`ix_projects_status` missing + `ix_projects_name` missing；兩者均非 definition mismatch。

### Checkpoint 10 — guarded projects index reconciliation

#### Implementation

- ORM metadata alignment：commit `cd194f5f2644ddb2bc9d4c73e275dfb78790b5b0`。
- guarded reconciliation module：commit `48c56c55c17f10475903f992c7ed9de6ff4cc5fb`。
- release wrapper：commit `de4bdf6db674e85844096df413caf7cee879e07c`。
- workflow entrypoint：commit `bf38d2bf215aaa22379b02a798fbf2b41b7d5c4e`。

Safety contract：versioned DB 不介入；unversioned DB 必須通過完整 preflight；wrong same-name index fail-closed；只建立 missing index；transaction + post-read exact verify；不 stamp。

#### CI / production evidence

- CI #254 run `36250433287`：**PASS**。
- Backend：**162/162 PASS**。
- Alembic / deployment-scripts / Flutter analyze/tests/Web build/branding：PASS。
- Firebase Hosting #153 run `36250556247`：PASS。
- Deploy Cloud Run #207 run `36250556257`。
- execution：`life-assistant-db-migrate-2jbnh`。
- task：`life-assistant-db-migrate-2jbnh-task0`。
- task exit：**33**。

Exit `33` 在既有 verifier 中表示：0001–0004 的 columns/type/nullability/PK/FK presence/required indexes 等 structural contract 通過，但 `alembic_version` 仍不存在。

因此兩個 repaired indexes 已 **PASS / VERIFIED**，但此證據後續被判定不足以直接支撐 stamp，原因見 Checkpoint 11。

---

## Checkpoint 11 — Alembic metadata bootstrap read-only preflight

### Ruling：exit 33 不等於 stamp-ready

重新逐版核對 Alembic `20260925_0001` → `20260926_0004` 後，發現既有 exit-33 verifier 尚未完整驗證 Alembic physical semantics，尤其：

- server defaults；
- migration-required indexes 的 exact definition；
- FK update/delete action、deferrability、initial state、validation state；
- migration 未宣告的 UNIQUE / CHECK / EXCLUDE constraints。

因此本 checkpoint 不把 exit `33` 視為 metadata bootstrap 授權條件，而是新增更嚴格、**唯讀** 的 stamp-readiness preflight。

### Migration defaults included in stronger contract

需驗證的 Alembic server defaults 包含：

- `google_connections.created_at / updated_at = now()`；
- `google_oauth_states.created_at = now()`；
- `execution_logs.started_at = now()`；
- `projects.status = 'active'`、`created_at / updated_at = now()`；
- `notes.created_at / updated_at = now()`；
- `habits.is_active = true`、`created_at = now()`；
- `habit_completions.completed_at = now()`；
- `shopping_lists.created_at = now()`；
- `shopping_items.is_done = false`、`sort_order = 0`；
- `templates.created_at / updated_at = now()`。

此層特別重要，因 ORM 的 Python-side `default=` 與 migration 的 DB `server_default=` 不等價；若 production table 曾由非 Alembic 路徑形成，僅驗 columns/type/nullability 可能無法發現 drift。

### TDD RED

- commit `3b70119901d3d003ff96f515f7d2ec5f61f7dd52`：`test: require fail-closed alembic metadata preflight`。
- CI #255 run `36253459521`：如預期 RED；既有 162 tests PASS，新 tests 因 preflight module / release gate 尚未實作而失敗。
- commit `11250634e2eb0206b832f01614045736b258376c`：`test: pin metadata preflight diagnostic exits`。
- CI #256：如預期 RED。

### GREEN implementation

- commit `ad0f18814c2eef146f9a4e33f636246822fbcd07`：新增 `backend/scripts/preflight_alembic_metadata_bootstrap.py`。
- commit `ed7adda2303adc7002b8ff6c74fec670ee052aaf`：release wrapper 接上 stronger preflight gate。
- CI #258：171/172 PASS；唯一 failure 為 source-guard 測試命中 docstring 中的字面文字，並非 write path。
- root cause 經 systematic debugging 確認為測試 / docstring 語意碰撞。
- commit `0a150b2300de755f29449faac32370083166e45d`：只修 docstring，執行邏輯未改。

Preflight **不包含**：

- Alembic `stamp` command；
- `INSERT INTO alembic_version`；
- `CREATE TABLE alembic_version`；
- business table / business data mutation。

### Stable diagnostic exits

- `50`：stronger preflight 全部 PASS，schema stamp-ready，但仍 **approval required**；故意 non-zero 阻擋 release。
- `51`：server default mismatch。
- `52`：migration-required index exact-definition mismatch。
- `53`：FK semantics mismatch。
- `54`：unexpected UNIQUE / CHECK / EXCLUDE constraint。

以上均低於 target-table bitmap range `64+`，避免分類碰撞。

### Formal CI evidence

CI #259 run `36253749350`，commit `0a150b2300de755f29449faac32370083166e45d`：**PASS**。

- Backend full suite：**172/172 PASS**。
- Alembic offline chain `0001 -> 0002 -> 0003 -> 0004`：PASS。
- deployment-scripts：PASS。
- Flutter analyze：PASS。
- Flutter tests：PASS。
- Flutter Web build：PASS。
- branding verification：PASS。

### Production read-only preflight evidence

Deploy Cloud Run #212：

- run：`36253850208`。
- release commit：`0a150b2300de755f29449faac32370083166e45d`。
- execution：`life-assistant-db-migrate-79xps`。
- task：`life-assistant-db-migrate-79xps-task0`。
- task exit：**51**。
- Cloud Run execution condition 同樣指出 task failed with exit code **51**。

Exit `51` 的固定分類：**BootstrapDefaultMismatchError / server-default contract mismatch**。

因此正式 production evidence 為：

- prior structural verifier（exit 33 所覆蓋 contract）：PASS / VERIFIED；
- stronger stamp-readiness preflight：**FAIL / VERIFIED**；
- failure class：server default mismatch / VERIFIED；
- exact table / column：**NOT VERIFIED**（目前 exit code 僅分類到 default mismatch；Cloud Logging read 仍 `PERMISSION_DENIED`）；
- Alembic metadata bootstrap readiness：**FAIL / NOT READY**；
- `public.alembic_version`：**still missing / VERIFIED**；
- production stamp / metadata write：**NOT EXECUTED**；
- IAM changes：**NOT EXECUTED**；
- Cloud Run service deploy：SKIPPED / migration gate blocked；
- `/health` / `/ready` / current-release auth/API runtime checks：NOT VERIFIED。

這也正式推翻「exit 33 已足以安全 stamp」的假設；目前不得執行 stamp。

### Firebase Hosting side signal（獨立於 DB preflight）

Firebase Hosting #158：run `36253850183`。

- Flutter Web build：PASS。
- `firebase deploy --only hosting`：**PASS / upload + release complete**。
- `Verify Firebase Hosting`：**FAIL**。
- exact failing sub-check：**NOT VERIFIED**；verification script 為 silent assertions，現有 log 只證明 step exit 1。
- 此 failure 不作為 DB preflight exit `51` 的原因，兩者分開追蹤。

因本 checkpoint 目標是 Alembic metadata safety，未在本輪修改 Firebase workflow 或推測 verification root cause。

### Production mutation record — Checkpoint 11

本 checkpoint 對 production：

- business schema mutation：**NONE**；
- business data mutation：**NONE**；
- `alembic_version` create/update：**NONE**；
- stamp：**NONE**；
- IAM / Service Account changes：**NONE**；
- secret rotation：**NONE**。

全部 production DB 檢查均為 catalog read / SELECT 類 read-only preflight。

### Current production state（Checkpoint 11 時點）

- 七張 0004 target tables：present / VERIFIED。
- previously repaired `ix_projects_status` / `ix_projects_name`：present + structural exact / PASS / VERIFIED。
- existing structural schema verifier：PASS to exit-33 gate / VERIFIED。
- stronger stamp-readiness server-default contract：**FAIL / VERIFIED**。
- exact default mismatch location：NOT VERIFIED。
- Alembic version metadata：**FAIL — missing / VERIFIED**。
- metadata stamp readiness：**FAIL / NOT READY**。
- Cloud Run service current release：SKIPPED / blocked。
- Task 8：**PARTIAL**。

### 下一個安全 checkpoint（Checkpoint 11 決議）

下一步只做 **server-default mismatch exact diagnosis**：

1. 保持 read-only；
2. 把 exit `51` 拆成可定位 exact table / column 的 non-sensitive diagnostics；
3. 不修改 production defaults；
4. 不建立 / 更新 `alembic_version`；
5. 不做 stamp；
6. 取得 exact mismatch 後，再另行設計 additive `ALTER COLUMN SET DEFAULT` repair contract 與風險判定；
7. 真正 metadata bootstrap / stamp 仍需在所有 stronger preflight 項目 PASS 後，另取得使用者明確確認。

---

## Checkpoint 12 — exact server-default mismatch diagnosis

### Scope / safety ruling

本 checkpoint 只把 generic exit `51` 拆到 exact `table.column`，保持所有 production DB 操作為 catalog read / SELECT 類 read-only preflight。

不在本 checkpoint：

- `ALTER COLUMN SET/DROP DEFAULT`；
- business table/data mutation；
- `alembic_version` create/update；
- Alembic stamp；
- IAM / Service Account 變更；
- secret rotation。

### TDD RED

- commit `ca567e2ef8e64721d705dad28f400acd7b09d032`：`test: diagnose exact bootstrap default mismatch`。
- CI #260 run `36276925806`：**如預期 RED**。
- backend 共 **173 tests**；既有 172 tests PASS，只有新增 exact mapping test 因 `DEFAULT_MISMATCH_EXIT_CODES` 尚未存在而 ERROR。
- FastAPI import：PASS。
- Alembic offline chain `0001 -> 0002 -> 0003 -> 0004`：PASS。
- deployment-scripts：PASS。

### GREEN implementation

- commit `00773abb7eb4508fc5948daed0c0744e293a862c`：`fix: encode exact bootstrap default mismatch`。
- 以 managed table / column 的既有穩定順序建立 **67 個** exact diagnostic exits。
- 使用 code ranges：`55–63` + `192–249`。
- 保留：
  - `50–54` generic bootstrap classifications；
  - `64–191` target-table presence bitmap；
  - unknown/future `(table, column)` fallback 仍回 generic `51`。
- 本變更只修改 error classifier / mapping；未修改 production catalog query、DDL、DML 或 preflight 判斷順序。

### Formal CI evidence

CI #261 run `36276997510`：**PASS**。

- release commit：`00773abb7eb4508fc5948daed0c0744e293a862c`。
- Backend full suite：**173/173 PASS**。
- exact default mapping contract：PASS。
- FastAPI import：PASS。
- Alembic offline chain `0001 -> 0002 -> 0003 -> 0004`：PASS。
- deployment-scripts：PASS。
- Flutter analyze：PASS。
- Flutter tests：PASS。
- Flutter Web build：PASS。
- branding verification：PASS。

### Production read-only exact diagnosis

Deploy Cloud Run #214：

- run：`36277104933`。
- release commit：`00773abb7eb4508fc5948daed0c0744e293a862c`。
- execution：`life-assistant-db-migrate-q5h7p`。
- task：`life-assistant-db-migrate-q5h7p-task0`。
- task exit：**214**。
- Cloud Run execution condition 同樣明確指出 task failed with exit code **214**。
- Cloud Run backend service deploy：**SKIPPED**。
- `/health`、`/ready`、unauthenticated API current-release checks：**SKIPPED / NOT VERIFIED**。

本 checkpoint 的固定一對一 mapping：

- exit `214` = **`projects.status` server-default mismatch**。

Alembic revision contract 對 `projects.status` 的期望 server default 為 **`'active'`**。

但 production `projects.status` 的實際 `column_default` 原值仍 **NOT VERIFIED**：Cloud Logging read 繼續回 `PERMISSION_DENIED`，而本 checkpoint 刻意不為除錯新增 IAM。因此目前只能正式判定：

- mismatch location：`projects.status` / **VERIFIED**；
- expected normalized default：`active` / **VERIFIED from migration contract**；
- actual production default：**NOT VERIFIED**；
- mismatch kind（missing expected default vs wrong value）：**NOT VERIFIED**。

不得在缺乏 actual evidence 時假設 production 是 `NULL/no default`。

### Firebase Hosting current-release side evidence

Firebase Hosting #160 run `36277104877`：**PASS**。

- Build Flutter Web：PASS。
- Firebase Hosting deploy：PASS。
- Verify Firebase Hosting：PASS。

因此 Checkpoint 11 的 Firebase #158 verification failure 在本 release **未重現**。#158 的 historical exact root cause 仍 NOT VERIFIED；本 checkpoint 不把它改寫成已知 transient root cause。

### Production mutation record — Checkpoint 12

本 checkpoint 對 production：

- server default mutation：**NONE**；
- business schema mutation：**NONE**；
- business data mutation：**NONE**；
- `alembic_version` create/update：**NONE**；
- stamp：**NONE**；
- IAM / Service Account changes：**NONE**；
- secret rotation：**NONE**。

### Current production state（Checkpoint 12 時點）

- prior structural verifier contract：PASS to exit-33 gate / VERIFIED。
- `projects.status` server-default location mismatch：**FAIL / VERIFIED**。
- `projects.status` expected Alembic default：`active` / VERIFIED。
- `projects.status` actual production default：**NOT VERIFIED**。
- remaining server-default columns after first mismatch：**NOT VERIFIED**（preflight fail-fast）。
- required index exact definitions after defaults stage：NOT VERIFIED in stronger preflight for this run（not reached）。
- FK semantics after defaults stage：NOT VERIFIED in stronger preflight for this run（not reached）。
- extra UNIQUE/CHECK/EXCLUDE constraints after defaults stage：NOT VERIFIED in stronger preflight for this run（not reached）。
- `public.alembic_version`：**missing / VERIFIED**。
- metadata stamp readiness：**FAIL / NOT READY**。
- Cloud Run service release：**SKIPPED / blocked**。
- Task 8：**PARTIAL**。

### 下一個安全 checkpoint（Checkpoint 12 決議）

下一步只做 **`projects.status` default mismatch kind 的唯讀診斷**：

1. 將 `projects.status` 的 mismatch 再拆成至少：
   - expected default missing；
   - wrong non-null default value；
2. 不輸出可能含敏感內容的 raw catalog payload；只用穩定 non-sensitive exit classification；
3. 不執行 `ALTER COLUMN SET/DROP DEFAULT`；
4. 不建立 / 更新 `alembic_version`；
5. 不做 stamp；
6. 取得 mismatch kind 後，再另行設計最小、additive/non-data-changing default repair contract；
7. stronger preflight 必須一路通過至 exit `50` 才能視為 stamp-ready；真正 Alembic metadata bootstrap / stamp 仍需另取得使用者明確確認。

---

## Checkpoint 13 — `projects.status` default mismatch kind diagnosis

### Scope / safety ruling

本 checkpoint 只把既有 `projects.status` exact mismatch 再分成兩個 non-sensitive failure reason，production DB 檢查仍維持 read-only：

- exit `250`：expected server default missing；
- exit `251`：wrong non-null server default。

不在本 checkpoint 執行任何 `ALTER COLUMN SET/DROP DEFAULT`、business data mutation、`alembic_version` create/update、Alembic stamp、IAM / Service Account 變更或 secret rotation。

### TDD RED

- commit `c905a7c1cb79de1677e95a5dff574b630306eb5a`：`test: distinguish projects status default drift reason`。
- CI #262 run `36278139878`：**如預期 RED**；backend 共 **176 tests**，只有新增 missing/wrong-value reason tests 失敗，實際 classifier 仍回 location code `214`；FastAPI import與 Alembic offline chain PASS。
- 為確保測到 production 真正使用的 release entrypoint，再以 commit `491b5abb887c2dda61116b71696de3179697b0ec`：`test: exercise release default drift classifier` 將測試指向 `apply_cloud_domain_parity_release.py`。
- CI #263 run `36278218937`：**如預期 RED**；同樣 176 tests 中僅 2 個 reason tests failure（`250 != 214`、`251 != 214`），其餘 174 tests PASS；Alembic / deployment-scripts PASS。

### GREEN implementation

- commit `6795fff07bdf71771bde67b793c1c9b11fa2cf99`：`fix: classify projects status default drift reason`。
- release classifier 僅在 `BootstrapDefaultMismatchError(table='projects', column='status')` 上分流：
  - expected non-null + actual `None` → `250`；
  - actual non-null 且不等於 expected → `251`；
- 其他錯誤全部委派回既有 `metadata_preflight.classify_failure()`。
- 本變更未修改 preflight SQL/catalog query、DDL、DML 或 schema repair 流程。

### Formal CI evidence

CI #264 run `36278253154`：**PASS**。

- release commit：`6795fff07bdf71771bde67b793c1c9b11fa2cf99`。
- Backend full suite：**176/176 PASS**。
- FastAPI import：PASS。
- Alembic offline chain `0001 -> 0002 -> 0003 -> 0004`：PASS。
- deployment-scripts：PASS。
- Flutter analyze：PASS。
- Flutter tests：PASS。
- Flutter Web build：PASS。
- branding verification：PASS。

### Production read-only reason diagnosis

Deploy Cloud Run #217：

- run：`36278355866`。
- release commit：`6795fff07bdf71771bde67b793c1c9b11fa2cf99`。
- execution：`life-assistant-db-migrate-kpztc`。
- task：`life-assistant-db-migrate-kpztc-task0`。
- task exit：**250**。
- Cloud Run execution condition 同樣明確指出 task failed with exit code **250**。
- Cloud Logging read 仍為 `PERMISSION_DENIED`；未為除錯調整 IAM。
- Cloud Run backend service deploy：**SKIPPED**。
- `/health`、`/ready`、unauthenticated API current-release checks：**SKIPPED / NOT VERIFIED**。

Exit `250` 的固定分類與本次 production evidence 共同證明：

- `projects.status` expected Alembic DB server default：`active` / VERIFIED；
- production `projects.status` normalized actual server default：**None / missing / VERIFIED**；
- 不是 wrong non-null default / VERIFIED；
- 不需要也沒有輸出 raw catalog payload。

因此目前 root cause 已由「server-default mismatch」→「`projects.status`」→「**missing DB server default**」逐層收斂完成。

### Firebase Hosting current-release side evidence

Firebase Hosting #163 run `36278355863`：**PASS**。

- Build Flutter Web：PASS。
- Firebase Hosting deploy：PASS。
- Verify Firebase Hosting：PASS。

此 side-signal 與 DB migration gate 分開判定。

### Production mutation record — Checkpoint 13

本 checkpoint 對 production：

- server default mutation：**NONE**；
- business schema mutation：**NONE**；
- business data mutation：**NONE**；
- `alembic_version` create/update：**NONE**；
- stamp：**NONE**；
- IAM / Service Account changes：**NONE**；
- secret rotation：**NONE**。

### Current production state

- prior structural verifier contract：PASS to exit-33 gate / VERIFIED。
- `projects.status` expected Alembic DB server default：`active` / VERIFIED。
- `projects.status` production DB server default：**missing / FAIL / VERIFIED**。
- remaining server-default columns after first mismatch：**NOT VERIFIED**（stronger preflight fail-fast）。
- required index exact definitions after defaults stage：NOT VERIFIED in stronger preflight for this run（not reached）。
- FK semantics after defaults stage：NOT VERIFIED in stronger preflight for this run（not reached）。
- extra UNIQUE/CHECK/EXCLUDE constraints after defaults stage：NOT VERIFIED in stronger preflight for this run（not reached）。
- `public.alembic_version`：**missing / VERIFIED**。
- metadata stamp readiness：**FAIL / NOT READY**。
- Cloud Run service current release：**SKIPPED / blocked**。
- Task 8：**PARTIAL**。

### 下一個安全 checkpoint

下一步可設計並驗證 **最小 additive `projects.status` DB server-default repair**：

1. 先以 TDD 定義 fail-closed repair contract；
2. 只允許在 production 仍為 unversioned、structural verifier PASS、且 `projects.status` default 明確 missing 時執行 `ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'active'`；
3. 不更新既有 rows，不做 backfill；`SET DEFAULT` 只影響後續未指定 `status` 的 INSERT；
4. repair 後立即 read-back verify normalized default = `active`；
5. 接著重新跑 stronger preflight，讓下一個 mismatch 自然浮現；
6. 本步仍不得建立 / 更新 `alembic_version`，不得 stamp；
7. stronger preflight 必須一路通過至 exit `50` 後，真正 metadata bootstrap / stamp 仍需另取得使用者明確確認。

---

## 執行規則

1. 一次只完成一個 Task / checkpoint。
2. checkpoint 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 checkpoint。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
