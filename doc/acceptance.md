# 生活助理 App v0.1 — Acceptance Criteria

最後更新：2026-09-27

> 本文件定義 Phase 1 Platform Release Gate。`[x]` 只代表該條要求層級已有足夠 evidence；Implementation / CI / Deployment PASS 不自動等於 Runtime / Integration PASS。

## Web / Cloud 核心

- [x] Flutter Web build PASS。
- [x] Firebase Hosting dev/test deployment PASS。
- [x] FastAPI Cloud Run deployment PASS。
- [x] PostgreSQL connectivity / Task persistence PASS。
- [x] Web 主線透過 Backend API 存取主資料。
- [x] Google identity + protected API baseline。
- [x] unified error envelope + request id baseline。
- [x] execution/activity log baseline。
- [ ] 手機與 desktop browser 主要介面完整 UX acceptance。

## Task

- [x] Task create / read / update / complete / delete implementation。
- [x] Task Web → Backend → PostgreSQL 使用者互動 CRUD PASS。
- [x] Task mutation execution-log baseline。
- [ ] 日期 / priority / reminder / tags / project 的完整 Web UX acceptance。
- [ ] Checklist Cloud 主線。

## Project

### Implementation / deployment

- [x] `projects` Cloud model。
- [x] Alembic `20260925_0003_projects` migration definition + CI validation。
- [x] list / create / get / update / delete API。
- [x] create / update / delete execution audit。
- [x] delete 有 linked Task 時回 409，避免 orphan。
- [x] delete guard 已擴充 linked Note / Shopping List reference。
- [x] `gmail.to_project` capability implementation。
- [x] CI #154 PASS。
- [x] Cloud Run #123 deployment / health / ready / 401 verification PASS。

### Final runtime / integration acceptance

- [x] Authenticated Project CRUD runtime PASS。
- [x] Project persistence / reread runtime PASS。
- [x] Gmail → Project true-account runtime PASS。
- [x] Project mutation → `/activity` end-to-end evidence PASS。
- [x] linked Note / Shopping List Project delete guard runtime PASS。

> Cloud Domain Parity final release 已在 GitHub Actions `dev-test` environment 完成 Alembic migration gate 與 Cloud Run runtime acceptance。此證據不代表另有一套未定義的 production environment 已驗證。

## Google Calendar

### Implementation / deployment

- [x] read API。
- [x] create API。
- [x] update API。
- [x] delete API。
- [x] create/update/delete execution audit baseline。
- [x] delete capability risk metadata = `destructive_external` / `explicit_user`。
- [x] Acceptance Center 已補 create → update → list/read → delete 驗收流程並部署。

### Final integration acceptance

- [ ] 真實帳號 Calendar read PASS。
- [x] 真實帳號 create PASS。
- [x] 真實帳號 update PASS。
- [x] 真實帳號 delete PASS。
- [x] synthetic provider failure → execution evidence runtime PASS。
- [ ] 真實 provider failure 有 execution evidence。
- [ ] destructive confirmation enforcement PASS。

## Gmail

### Implementation / deployment

- [x] metadata / snippet read API。
- [x] Gmail → Task。
- [x] Gmail → Calendar。
- [x] Gmail → Project。
- [x] conversion mutation execution audit baseline。
- [x] Gmail → Calendar 不猜時間；request 必須提供 start/end + timezone。

### Final integration acceptance

- [x] 真實帳號 metadata read PASS。
- [x] Gmail → Task PASS。
- [x] Gmail → Calendar PASS。
- [x] Gmail → Project PASS。
- [x] synthetic Gmail provider failure → execution evidence runtime PASS，且失敗時不建立 Task。
- [ ] 真實 Gmail provider failure → execution evidence PASS。

## Google Drive

### Implementation / deployment

- [x] `drive.file` least-privilege baseline。
- [x] `life_assistant/ChatGPT_Bridge` ensure API。
- [x] explicit UI action 才觸發 ensure baseline。
- [x] execution log + `partial_success` baseline。

### Final integration acceptance

- [x] 真實帳號 Drive Bridge ensure PASS。
- [x] synthetic root-success / bridge-failure → `partial_success` execution evidence runtime PASS。
- [ ] 真實 provider failure / partial-success execution evidence PASS。

## Backend Error / Audit

- [x] API error = `error.code / message / request_id` baseline。
- [x] `X-Request-ID` response header。
- [x] validation errors machine-readable baseline。
- [x] unhandled exception 不回傳原始敏感 exception text。
- [x] audit start fail-closed：audit unavailable 時 mutation 不執行。
- [x] audit finalize failure 有 `audit_finalize_failed`，不包裝成 full success。
- [x] `/api/v1/activity` authenticated API baseline。
- [x] 真實 Google mutation success → activity end-to-end runtime PASS。
- [x] synthetic Google mutation failure / partial-success → activity end-to-end runtime PASS。
- [ ] 真實 Google mutation failure / partial-success → activity end-to-end runtime PASS。

## SQLite → PostgreSQL Migration

- [x] Legacy SQLite source 保留，未 drop / 清空。
- [x] Task target schema 存在。
- [x] Project target schema 存在。
- [x] Note / Habit / Shopping / Template 必要 target schema 完成並在 dev-test runtime 驗證。
- [x] Checklist / Tags / Reminders / legacy attachment metadata / Calendar ref / Gmail ref / legacy activity / key-value state / migration ledger target schema 完成。
- [x] deterministic export implementation + synthetic runtime evidence。
- [x] dev/test import / upsert runtime evidence。
- [x] rerun 不重複：第二次 import `inserted=0`、全部轉為 idempotent skip。
- [x] row counts / key relationships / critical fields synthetic runtime verification。
- [x] failure 不破壞 SQLite source：runtime 故障注入後 before/after export 完全一致。
- [x] PostgreSQL failure transaction rollback runtime evidence：collision 後 Task / migration ledger 無殘留。
- [x] success result / execution-log runtime evidence。
- [x] failure execution-log runtime evidence：`TargetCollisionError` → `failure / failed`。
- [x] success/failure synthetic dev-test runtime migration evidence與 exact-ID cleanup。
- [ ] 真實使用者 historical SQLite source 已定位並完成 backup / migration / verification。

> 詳細證據見 `doc/sqlite_postgres_backfill_progress.md`。目前 **migration tooling / synthetic dev-test runtime = DONE / PASS**；但允許的 Drive root `life_assistantGPT` 尚未找到實際 `life_assistant.db` / backup，因此 **Real historical user-data migration = NOT VERIFIED**，不可宣稱真實歷史資料已搬完。

## 其他 Cloud Domain

- [x] Note CRUD / links Cloud API + persistence runtime acceptance。
- [ ] Notes full-text search Cloud implementation（Cloud Domain Parity 設計明確排除於該批次）。
- [x] Habit + completion log Cloud API + persistence runtime acceptance。
- [x] Shopping list/items Cloud API + persistence runtime acceptance。
- [x] Template API + opaque `payload_json` round-trip runtime acceptance。
- [ ] Attachment central storage/reference strategy。

Legacy SQLite 同名能力不等於 Cloud acceptance；上述 `[x]` 依 Cloud Domain Parity final runtime evidence 判定。

## ChatGPT Bridge / MCP

- [x] Drive Bridge 被明確定位為 legacy / fallback path。
- [x] Google capability metadata baseline。
- [x] Backend execution/activity foundation。
- [ ] versioned Bridge / MCP API contract。
- [ ] input/output schema validation。
- [ ] permission / risk / confirmation enforcement。
- [ ] request_id + action_id idempotency。
- [ ] proposed action review / execution / result contract。
- [ ] Bridge / MCP failure 不破壞 PostgreSQL 主資料的 integration evidence。
- [ ] omniAgent 只能透過版本化 API/MCP contract，不依賴 private DB implementation。

## Security

- [x] Google tokens encrypted-storage baseline。
- [x] OAuth state validation。
- [x] least-privilege Google scope baseline。
- [x] API errors 不直接洩漏 secret/token baseline。
- [ ] Backend authorization / minimum-permission policy 完整驗證。
- [ ] destructive/sensitive action final policy gate。
- [ ] Cloud mutation idempotency policy。

## Release Evidence Snapshot — 2026-09-27

### True-account integration checkpoint — 2026-09-26

- Acceptance Center / Drive integration final commit `7f7da43eacce23054c91429bceaf39b536c8a75c`。
- CI #186：PASS；Flutter Analyze / Test / Build Web / branding verification PASS，13 tests PASS。
- Firebase Hosting #102：PASS（build / deploy / runtime verify），release SHA = `7f7da43eacce23054c91429bceaf39b536c8a75c`。
- Cloud Run #156：workflow PASS；本次無 Backend 變更，deploy / runtime steps 依 change detection 正確 skipped。
- 使用者真實帳號驗收：Project create/update/reread/delete PASS。
- 使用者真實帳號驗收：Gmail metadata read、Gmail → Task / Project / Calendar PASS。
- 使用者真實帳號驗收：Calendar create/update/delete PASS。
- 使用者真實帳號驗收：Drive Bridge ensure PASS。
- Acceptance Center Activity Log evidence PASS；`[ACCEPTANCE TEST]` 測試資料 cleanup PASS。
- 尚未由本次真實驗收覆蓋：Calendar list/read、真實 provider failure / Drive partial-success、destructive confirmation enforcement。

### Cloud Domain Parity final checkpoint — 2026-09-27

- Functional release SHA：`19b56fb0a865b4e5b6260c13a40e04e66ef64676`。
- CI #275 / run `36289075250`：PASS。
- Firebase Hosting #174 / run `36289173006`：PASS。
- Cloud Run #228 / run `36289173011`：PASS。
- PostgreSQL migration execution `life-assistant-db-migrate-h67ll`：PASS。
- Cloud Run revision `life-assistant-api-00069-rz7`：100% traffic；`/health`、`/ready`、unauthenticated API 401 protection PASS。
- Authenticated Cloud Domain runtime acceptance execution `life-assistant-cloud-domain-acceptance-55ng2`：PASS。
- Note / Habit / Shopping / Template persistence、Project relation guard、execution log、exact-ID cleanup：PASS。
- Cloud Domain Parity Task 1–8：DONE / PASS。

### SQLite → PostgreSQL synthetic backfill checkpoint — 2026-09-27

- Base migration release SHA：`b968b7fa2347bed5db9fab6a75bd6a09c573844d`。
- Failure-path acceptance release SHA：`fb59f013bce430c5643b2ebf2f5df7fe8729ddad`。
- CI #280 / run `36321693983`：PASS；backend / Alembic offline chain / backend tests / deployment scripts / Flutter analyze-test-build-branding 全 PASS。
- Firebase Hosting #179 / run `36321800021`：PASS。
- Cloud Run #233 / run `36321800086`：PASS。
- verified database migration：PASS。
- backend deploy、`/health`、`/ready`、unauthenticated API 401 protection：PASS。
- authenticated Cloud Domain acceptance：PASS。
- SQLite backfill success-path runtime acceptance：PASS。
- SQLite backfill failure-path runtime acceptance：PASS；驗證 source-preservation、transaction rollback、failure audit、exact cleanup。
- Alembic online migration transaction boundary 已修正：`pg_advisory_xact_lock` 在 `context.begin_transaction()` 內取得，並有 contract test 防 regression。
- Migration tooling / synthetic runtime：DONE / PASS。
- 真實使用者 historical SQLite source：NOT VERIFIED；目前沒有可執行的實際 source file evidence。

### Calendar read/list readiness + Google synthetic failure checkpoint — 2026-09-27

- Calendar Acceptance Center implementation commit：`0e5c39a802b93f8c8474031315b4928b8a14cf04`；analyzer follow-up fix：`57c02fa7436f8e3da5b38e2f95591545ef350e7c`。
- CI #282 / run `36323289613`：PASS；backend / Alembic / deployment scripts / Flutter Analyze / Test / Web build / branding 全 PASS。
- Firebase Hosting #181 / run `36323402003`：PASS。
- Cloud Run #235 / run `36323401985`：PASS；migration / deploy / health / ready / 401 / Cloud Domain / SQLite success+failure gates 全 PASS。
- Calendar Acceptance Center 已能對測試 event 執行 create → update → list/read 同 event ID + current summary → delete；但**尚未由使用者真實 Google 帳號重新執行此新版流程**，故「真實帳號 Calendar read」仍為 NOT VERIFIED。
- Google synthetic failure gate release SHA：`2ba53d0a2cb7916aaa3f71d4e0727357706fc83c`。
- CI #283 / run `36328471745`：PASS；backend / deployment scripts / Flutter Analyze / Test / Web build / branding 全 PASS。
- Firebase Hosting #182 / run `36328601966`：PASS。
- Cloud Run #236 / run `36328601944`：PASS。
- PostgreSQL migration execution `life-assistant-db-migrate-lz8zx`：PASS。
- Cloud Run revision `life-assistant-api-00073-lcb`：100% traffic；`/health` = `{"status":"ok"}`、`/ready` = `{"status":"ok","database":"ok"}`、unauthenticated API 401 protection PASS。
- Authenticated Cloud Domain acceptance execution `life-assistant-cloud-domain-acceptance-2thsn`：PASS。
- Google failure-path runtime acceptance execution `life-assistant-google-failure-acceptance-tfdf4`：PASS。
- 該 runner 使用真實 FastAPI + 真實 PostgreSQL，只替換 outbound Google provider call 做 deterministic failure injection；驗證 Calendar `failure`、Gmail `failure` + no internal Task write、Drive root-success / bridge-failure → `partial_success`、`http_503` error category、`/activity` readback、request/finish metadata 與 exact cleanup。任一 assertion 失敗 runner 即 exit 1；本次 Cloud Run Job 成功完成。
- SQLite success-path execution `life-assistant-sqlite-backfill-acceptance-cwvwn`：PASS；failure-path execution `life-assistant-sqlite-backfill-failure-acceptance-xgs8m`：PASS。
- Cloud Run deploy 仍出現既有非阻塞 `--allow-unauthenticated` IAM policy re-apply warning；revision 仍成功 100% serving，health/ready/401 checks PASS，未做額外 IAM 變更。
- **Synthetic Google failure / partial-success runtime：DONE / PASS。真實 Google provider failure / partial-success：NOT VERIFIED。**

## Phase 1 Status

**PARTIAL**。Cloud target schema/API/runtime parity、SQLite→PostgreSQL migration tooling / synthetic runtime acceptance，以及 Google provider synthetic failure / partial-success runtime acceptance 已完成，但 Phase 1 仍不可標 DONE，主要缺口：

- Real historical SQLite user-data migration：尚未取得實際 source file，故 NOT VERIFIED。
- Calendar 真實帳號 read/list 尚未以新版 Acceptance Center 重跑；真實 Google provider failure / Drive partial-success 仍 NOT VERIFIED（synthetic failure-path runtime 已 PASS）。
- authorization / confirmation / idempotency policy，包含 destructive confirmation enforcement。
- Bridge/MCP Release Gate。
- Task checklist / 完整 Web UX、Notes search、Attachment strategy 等剩餘 Phase 1 product acceptance。

## Phase 1 不阻塞項目

Android/iOS 正式上架、完整 offline-first、SQLite local-cache 雙向 sync、Today Cockpit、Attention/Focus、Routine Library、Global Capture、Plan/Review、Contextual AI、People context 延後至 Phase 1.5 / Phase 2。
