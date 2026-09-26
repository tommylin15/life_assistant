# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 8 Alembic metadata bootstrap read-only preflight）

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

Task 8 整體狀態：**PARTIAL**。正式 main CI 已通過；production physical schema 的既有 structural verifier 已可到 exit `33`，但更嚴格的 Alembic metadata bootstrap preflight 在 production 回傳 exit `51`，確認仍存在 server-default contract mismatch，因此目前 **NOT STAMP-READY**。不得標示 DONE。

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

### Current production state

- 七張 0004 target tables：present / VERIFIED。
- previously repaired `ix_projects_status` / `ix_projects_name`：present + structural exact / PASS / VERIFIED。
- existing structural schema verifier：PASS to exit-33 gate / VERIFIED。
- stronger stamp-readiness server-default contract：**FAIL / VERIFIED**。
- exact default mismatch location：NOT VERIFIED。
- Alembic version metadata：**FAIL — missing / VERIFIED**。
- metadata stamp readiness：**FAIL / NOT READY**。
- Cloud Run service current release：SKIPPED / blocked。
- Task 8：**PARTIAL**。

### 下一個安全 checkpoint

下一步只做 **server-default mismatch exact diagnosis**：

1. 保持 read-only；
2. 把 exit `51` 拆成可定位 exact table / column 的 non-sensitive diagnostics；
3. 不修改 production defaults；
4. 不建立 / 更新 `alembic_version`；
5. 不做 stamp；
6. 取得 exact mismatch 後，再另行設計 additive `ALTER COLUMN SET DEFAULT` repair contract 與風險判定；
7. 真正 metadata bootstrap / stamp 仍需在所有 stronger preflight 項目 PASS 後，另取得使用者明確確認。

---

## 執行規則

1. 一次只完成一個 Task / checkpoint。
2. checkpoint 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 checkpoint。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
