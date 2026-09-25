# 生活助理 App v0.1 — Acceptance Criteria

最後更新：2026-09-25

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
- [x] `gmail.to_project` capability implementation。
- [x] CI #154 PASS。
- [x] Cloud Run #123 deployment / health / ready / 401 verification PASS。

### Final runtime / integration acceptance

- [ ] Authenticated Project CRUD runtime PASS。
- [ ] Project persistence / reread runtime PASS。
- [ ] Gmail → Project true-account runtime PASS。
- [ ] Project mutation → `/activity` end-to-end evidence PASS。

> migration file 已 CI 驗證；目前 deployment workflow 沒有 production `alembic upgrade` evidence，因此不得把「Alembic production apply」標成 PASS。

## Google Calendar

### Implementation / deployment

- [x] read API。
- [x] create API。
- [x] update API。
- [x] delete API。
- [x] create/update/delete execution audit baseline。
- [x] delete capability risk metadata = `destructive_external` / `explicit_user`。

### Final integration acceptance

- [ ] 真實帳號 Calendar read PASS。
- [ ] 真實帳號 create PASS。
- [ ] 真實帳號 update PASS。
- [ ] 真實帳號 delete PASS。
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

- [ ] 真實帳號 metadata read PASS。
- [ ] Gmail → Task PASS。
- [ ] Gmail → Calendar PASS。
- [ ] Gmail → Project PASS。
- [ ] Gmail provider failure → execution evidence PASS。

## Google Drive

### Implementation / deployment

- [x] `drive.file` least-privilege baseline。
- [x] `life_assistant/ChatGPT_Bridge` ensure API。
- [x] explicit UI action 才觸發 ensure baseline。
- [x] execution log + `partial_success` baseline。

### Final integration acceptance

- [ ] 真實帳號 Drive Bridge ensure PASS。
- [ ] failure / partial-success execution evidence PASS。

## Backend Error / Audit

- [x] API error = `error.code / message / request_id` baseline。
- [x] `X-Request-ID` response header。
- [x] validation errors machine-readable baseline。
- [x] unhandled exception 不回傳原始敏感 exception text。
- [x] audit start fail-closed：audit unavailable 時 mutation 不執行。
- [x] audit finalize failure 有 `audit_finalize_failed`，不包裝成 full success。
- [x] `/api/v1/activity` authenticated API baseline。
- [ ] 真實 Google mutation success/failure/partial-success → activity 的 end-to-end runtime PASS。

## SQLite → PostgreSQL Migration

- [x] Legacy SQLite source 保留，未 drop / 清空。
- [x] Task target schema 存在。
- [x] Project target schema 存在。
- [ ] Note / Habit / Shopping / Template 等必要 target schema 完成。
- [ ] deterministic export。
- [ ] dev/test import / upsert。
- [ ] rerun 不重複。
- [ ] row counts / key relationships / critical fields verification。
- [ ] failure 不破壞 SQLite source。
- [ ] success / partial success / failure result evidence。
- [ ] runtime migration evidence。

## 其他 Cloud Domain

- [ ] Note CRUD / search。
- [ ] Habit + completion log。
- [ ] Shopping list/items。
- [ ] Template API。
- [ ] Attachment central storage/reference strategy。

Legacy SQLite 同名能力不等於 Cloud acceptance。

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

## Release Evidence Snapshot — 2026-09-25

- Docs sync commit `0be77b05c40bcdc2434ff4b94689bab49ef5173a`；CI #153 PASS。
- Project/Gmail-to-project commit `0ea1d1fad596bcce4683df82b7d68caa4d7e42be`。
- CI #154：PASS。
- Cloud Run #123：PASS（deploy / health / ready / protected 401）。
- Firebase Hosting #69：PASS（build / deploy / verify）。
- 使用者互動：Google login PASS；Task CRUD PASS。
- Project authenticated CRUD：NOT VERIFIED。
- Gmail / Calendar / Drive true-account integration：NOT VERIFIED。
- SQLite → PostgreSQL full migration：NOT VERIFIED。

## Phase 1 Status

**PARTIAL**。尚不可標 DONE，主要缺口：

- Project authenticated runtime acceptance。
- Google integrations true-account success/failure acceptance。
- remaining Cloud target schemas + full SQLite migration evidence。
- authorization / confirmation / idempotency policy。
- Bridge/MCP Release Gate。

## Phase 1 不阻塞項目

Android/iOS 正式上架、完整 offline-first、SQLite local-cache 雙向 sync、Today Cockpit、Attention/Focus、Routine Library、Global Capture、Plan/Review、Contextual AI、People context 延後至 Phase 1.5 / Phase 2。
