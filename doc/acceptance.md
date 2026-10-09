# 生活助理 App v0.1 — Acceptance Criteria

最後更新：2026-10-09（Calendar #8 同 SHA 正式封板證據；其他歷史功能/最終 Gate 不重新判定）

> 本文件定義 Phase 1 Platform Release Gate。`[x]` 只代表該條要求層級已有足夠 evidence；Implementation / CI / Deployment PASS 不自動等於 Runtime / Integration PASS。

## 2026-10-09 P1 staging / P0 免費活動聯合驗收 — PARTIAL

這是 **run-specific** 真實證據，和 Calendar #8 歷史 DONE 不衝突；不以 source commit 或 CI PASS 替代尚未執行的 staging / production release。

- [x] **PASS（staging 固定 live 的現有版本 readback）** — [read-only run 37944737101](https://github.com/tommylin15/life_assistant/actions/runs/37944737101)：獨立 staging live Hosting version `e3a6dd23aec06848`、前端完整 SHA `eb9f60c3413a8e5216318888a6456a1c464d8cab`；REST Hosting 的 `/api/**`、`/auth/**` 同 tag `v3-eb9f60c341` 精確對應 `life-assistant-api-00197-fug`，未登入 API/Auth 401 PASS。
- [x] **PASS（現場問題分類）** — [read-only run 37945021056](https://github.com/tommylin15/life_assistant/actions/runs/37945021056)：目前 staging `/auth/login` 回 **PRODUCTION_CALLBACK**，P1 真實固定 staging Google OAuth **FAIL／尚未通過**；P0 `/api/v1/free-events/status` staging 和 production **404**，新 owner-only 聚合 API 尚未發布，不可說 production row count 已驗證。
- [x] **PASS（source/CI 層，有效範圍僅限 code）** — staging Host whitelist/OAuth + incremental token exchange、SHA Preview→同版 staging live 受控 clone / 版本級 pinned rewrite readback / 技術回復、單獨 `v3-staging-restore.yml`、read-only `v3-p0-p1-joint-acceptance.yml` 已加入 GitHub main。CI [37945673591](https://github.com/tommylin15/life_assistant/actions/runs/37945673591) 成功；後續每次 main SHA 需再核對同版 CI，不能挪用舊 PASS。
- [ ] **NOT VERIFIED — 本次新 SHA V3 candidate / Preview**：沒有新 source SHA 對應 GHCR digest + 0%-traffic candidate + pinned Preview 真實成功證據。
- [ ] **NOT VERIFIED — staging live 新版／回復演練**：workflow 的 `apply` 尚未實際執行；保留目前既存 staging version，未改 production Hosting 或 Cloud Run 流量。
- [ ] **NOT VERIFIED — Google OAuth 真實 E2E**：必須確認現有 Google OAuth Web Client 同時允許 production 與固定 staging callback，經真正 Google 登入、callback、session cookie、`/auth/me` 驗證，且有可稽核的 staging OAuth acceptance evidence；不得用單純 307/401 或 CI test 取代。
- [ ] **NOT VERIFIED — P0 真實資料**：Owner session 需實際取得 aggregate observation / events / opportunities / strict verified-only UI rows 和去重證據；現行 Cloud Logging permission FAIL 仍是獨立問題。14 天品質仍 PARTIAL。
- [ ] **NOT VERIFIED — P0/P1 一起驗收**：run `v3-p0-p1-joint-acceptance.yml` 必須驗證本次實際 live SHA / pins、staging OAuth redirect、P0 401、安全及正式流量不變；其成功本身也**不等於** OAuth 真登入或 owner PostgreSQL 統計已通過。

**Overall:** P1 = PARTIAL；P0 = PARTIAL；Phase 1 原 11 包仍 8/11（72.7%），不得標示 DONE。

## Package #8 — Calendar 正式封板（2026-10-09）

- [x] **DONE / PASS — Calendar #8**，原 11 個 Phase 1 工作包完成數：**8/11（72.7%）**。所有以下 Gate 綁定同一 release SHA `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7`。
- Source / release SHA: `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7` (同一完整 SHA 綁定 CI / V3 / Firebase / Calendar UI / Google read-list)。
- **Implementation / tests / CI — PASS:** [CI #37882690249](https://github.com/tommylin15/life_assistant/actions/runs/37882690249) backend tests、Flutter analyze/widgets/Drive nav/Web build、deployment scripts；全天日期 `start_date/end_date` 保持 Google `end.date` exclusive；對話框 `dialogContext` 修復巢狀 Navigator。
- **V3 GHCR → Cloud Run + runtime — PASS:** [V3 #37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014) immutable digest、Trivy、0%-traffic candidate、健康/資料庫/Auth、Preview、真實 pre-promotion integration、100% promotion/live、rollback rehearsal/restore、`life-assistant-api` 最新 **10 revisions** retention PASS。
- **Firebase Hosting — PASS:** [#37885328134](https://github.com/tommylin15/life_assistant/actions/runs/37885328134) exact-SHA release file, Flutter Web production, Task/Project UI regression gates。
- **真實 Google Calendar 授權 read/list（唯讀）— PASS:** [#37885330178](https://github.com/tommylin15/life_assistant/actions/runs/37885330178) 已有 owner-scoped Cloud Run Job runtime 成功結果；不宣稱曾對真實使用者行程執行 create/update/delete。
- **正式桌面／手機 Calendar UI（mocked Google responses）— PASS:** [#37885544932](https://github.com/tommylin15/life_assistant/actions/runs/37885544932) log: `month_list_allday`、`create_tz`、`update`、`confirmed_delete`、`all_day_edit`、`mobile_navigation_controls` 與 `calendar_ui_acceptance=PASS`。刪除驗證含「取消時無 mutation」及明示確認 header；此 UI 模擬不等同真實 Google mutation E2E。
- **Bootstrap E2E orchestration — PASS:** [#37882690327](https://github.com/tommylin15/life_assistant/actions/runs/37882690327) 逐步驗證 V3 + Firebase + Calendar UI + True Account gates，同 SHA 全成功。
- **特定界線：** #8 Calendar 依核准的 read/list 真實帳號 + mocked browser mutation 流程驗收封板；尚未以正式 Google 帳號執行真實 create/update/delete（風險較高的外部寫入），這不冒充已驗證。Drive Knowledge Gemini/OpenRouter 歷史 #63/#70 failure 仍是獨立跨功能 health backlog，不隨 Calendar 封板自動消失。
- [ ] **NOT VERIFIED（非本次 Calendar read/list 封板契約）**：正式 Google 帳號真正 create/update/delete 事件的無副作用、明示同意之 E2E。未執行真實 destructive API，不能因 mocked UI PASS 宣稱實際 mutation E2E PASS。
- [ ] **OPEN / FAIL — 獨立跨功能**：Drive Knowledge #63/#70 歷史 Gemini/OpenRouter 回歸，需另跑最新部署的 real provider gate；未包含在 #8 封板。
- 原始 Phase 1 #9–#11 與 Final Release Gate 仍 **PARTIAL / NOT VERIFIED**；不因 Calendar 封板將全案標為 DONE。

## CI/CD V3 舊資產清理驗收（與產品 Phase 1 功能驗收分開）

- [x] **PASS** — GitHub Actions → 公開 GHCR → Cloud Run promoted release。歷史成功 [run 37795789924](https://github.com/tommylin15/life_assistant/actions/runs/37795789924)，release SHA `25ff10c61abc15e557996b6070e02abf3b54a97b`。
- [x] **PASS** — Cloud Run `life-assistant-api-00183-hax` 現為 Ready，所用 GHCR digest 為 `sha256:b06254c2db22489295c2a82928ea19a6352193fd7b0c72f1041040f22bc0d7b1`。
- [x] **PASS** — 5 個歷史 Cloud Build Trigger 均 `disabled=true`，非直接刪除 trigger 定義。
- [x] **PASS** — 指定 3 個舊 GCS CI/CD Buckets 均自 bucket list 消失且個別 404；8→5，保留 5 個 `dev-*`。
- [x] **PASS** — 指定 3 個舊 AR Docker Repositories 自 list 消失；4→1，保留 `janus-postgres`，目前 1 Digest。
- [x] **PASS** — 刪後 GCP 即時 readback [run 37867249614](https://github.com/tommylin15/life_assistant/actions/runs/37867249614)，GCS 已刪 Bucket / AR 唯一保留 repository / triggers / API readiness 均驗證；清理盤點已可將已刪 Bucket 的 404 報為 `DELETED`。
- [ ] **NOT VERIFIED** — `janus-postgres/postgres:16.15` 是否仍被 GCE VM 或非 Cloud Run database container 使用。依保護資料庫／應用資料原則，未驗證前不刪。
- [ ] **NOT VERIFIED** — 每個 Cloud Run Service 即時 Revision 最終數量及新的正式 release 專屬 E2E integration；不能只因 CI/CD 清理 PASS 就宣稱 Phase 1 DONE。
- **Evidence register**：[`v3_cleanup_and_cutover_inventory.md`](v3_cleanup_and_cutover_inventory.md)；摘要 [`progress.md`](progress.md)。原先 58 AR Digest、77 GCS objects 是清理前候選統計，最終證據是已刪 Bucket/Repository 不存在；不得推定逐項 deletion audit event。

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
- [x] Calendar DELETE backend confirmation gate 已實作並部署；confirmation 綁定 `calendar.delete` action + target event id。
- [x] Flutter client 不再自動宣稱 confirmation；只有 explicit-confirmed path 才送 confirmation header。
- [x] Acceptance Center 已補 create → update → list/read → delete 驗收流程並部署。

### Final integration acceptance

- [ ] 真實帳號 Calendar read PASS。
- [x] 真實帳號 create PASS。
- [x] 真實帳號 update PASS。
- [x] 真實帳號 delete PASS。
- [x] synthetic provider failure → execution evidence runtime PASS。
- [ ] 真實 provider failure 有 execution evidence。
- [x] destructive confirmation enforcement PASS。

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

### Task 9 — Drive Knowledge production delivery checkpoint（2026-10-07）

- [x] Runtime-loaded Google Picker production config PASS；專用 key 限制 `picker.googleapis.com` 與正式 Hosting / `docs.google.com` referrers；app id `131494961796`。
- [x] 三個 external AI provider 各自真實 API acceptance PASS。
- [x] 真實 Picker-selected Drive fixture：metadata、readable text、one-time Note import、source relation 與 exact cleanup PASS。
- [x] Exact release image / Firebase release、synthetic backend runtime、OAuth redirect、production desktop/mobile UI 與 final mandatory gate PASS。

- Production release SHA：`2d08118a13c71c6fec97e8bfba0857b861eefd1e`；ready revision `life-assistant-api-00154-xrt`。
- CI #551 / run `37568284598`、Firebase Hosting #369 / run `37568479243`、Notes UI run `37568672137`：PASS。
- Cloud Run #423 / run `37568479305`：PASS；ready revision、core persistence、checklist、action-id、Google failure-path 與 synthetic SQLite backfill / failure-path 回歸驗收全 PASS。
- Drive Knowledge Runtime Acceptance #47 / run `37568734572`：**PASS，所有 mandatory gates 通過**。
- Exact image digest：`sha256:4817dd48cd1302cde83699cc91c764fd1de721a31689fecc7203603e28bec9d4`；exact Firebase release、OAuth redirect、desktop/mobile production UI：PASS。
- Picker config execution `life-assistant-postdeploy-acceptance-xslp9`、synthetic execution `life-assistant-postdeploy-acceptance-dzspg`、真實 Drive execution `life-assistant-postdeploy-acceptance-hlpg2`：PASS。
- Live AI execution `life-assistant-postdeploy-acceptance-sqlx5`：succeeded `1`、failed `0`、exit `0`。Gemini `latest-3-flash`（成功模型 `3.6 Flash` / `3.8 Flash`）、Groq `openai/gpt-oss-120b`、OpenRouter `openrouter/free` 兩個 stage 各自 PASS。
- Runtime 只讀取 `life-assistant-bundle:latest`，現在僅 version `7` enabled，versions `1–6` destroyed；沒有其他 bundle 的 runtime dependency。
- 真實 fixture 已透過 Picker 登記，驗收帳號與 file ID 已設於 GitHub `dev-test`；來源文件保持不變，驗收只清理自己建立的本地 Note / Tag。識別碼與其他專案 secret 清理 evidence 見 `integrations.md`。
- 歷史 #45 live AI 因免費 endpoint 不支援嚴格 JSON Schema 回覆 `404` 而 FAIL；commit `2d08118` 改為 OpenRouter JSON mode + schema prompt，保留後端欄位 / candidate ID 驗證與 `data_collection=deny`。#47 已覆蓋修復後正式版本。

**Task 9 historical closure release `2d08118...` / #47 = DONE / PASS；latest health 已由 release `3b75e9e...` 的 Drive Knowledge #59 / run `37595859159` 再次驗證 PASS。Package #5 歷史封板 evidence 保留，current Drive Knowledge production health 亦為 PASS。**

## Habits productization checkpoint — Package #6（2026-10-07）

- [x] 正式 Web entry：`/more/habits`。
- [x] Habit list / create / update UI。
- [x] recurrence / reminder UI。
- [x] completion mutation 與 append-only completion history UI。
- [x] loading / empty / error states。
- [x] mobile + desktop production acceptance。
- [x] 真實 PostgreSQL runtime：habit create/update/complete/completions/activity persistence。
- [x] exact release CI / Firebase / Cloud Run / post-deploy evidence。

Evidence：

- Final release SHA：`02eda1124885846f41ca32ca185d9e1a5a5ebfe1`。
- CI #558 / run `37577319168`：PASS。
- Firebase Hosting #376 / run `37577494901`：PASS。
- Habits UI Acceptance #7 / run `37577765718`：PASS；desktop list/create/edit/complete/history + mobile navigation/controls。
- Deploy Cloud Run #430 / run `37577494982`：PASS；authenticated cloud-domain acceptance 亦 PASS。
- Post-deploy Runtime Acceptance #96 / run `37579244566`：PASS。
- Semantics product fix：`28f1bddc34f0e87c8eb757ce446ad8d9e54ec7c4`；final Flutter pointer acceptance：`02eda1124885846f41ca32ca185d9e1a5a5ebfe1`。

**Package #6 = DONE / PASS；Phase 1 closure = 6/11 = 54.5%。下一工作包為 #7 Shopping。**

### Latest-release cross-feature health note

- Habits release `02eda1124885846f41ca32ca185d9e1a5a5ebfe1` 的 Drive Knowledge Runtime Acceptance #54 / run `37578066375` 曾為 **FAIL**；failure scope 僅 live external AI production acceptance，其餘 Picker / real Drive fixture / exact Firebase / OAuth / production UI 皆有 PASS evidence。
- 原 #54 / rerun 的 Cloud Run task exit `85` 只能證明 provider call failure；GitHub deployment identity 無 Cloud Logging read 權限，因此未將單一 provider 根因臆測為已知。
- Remediation：`89d54011` 加入 bounded transient retry；`a44617bc` 讓 live acceptance 測完所有 configured providers 並以 provider failure mask 暴露失敗；`668aa0db` / `3b75e9e2` 補齊 runtime resilience / retry tests。
- Release `3b75e9e288be0d2179cd381281b55210a14ad875`：CI #562 / run `37592497897`、Firebase #380 / run `37592780715`、Cloud Run #434 / run `37592780705`、Post-deploy Runtime #100 / run `37594646099` 均 **PASS**。
- Drive Knowledge Runtime Acceptance #59 / run `37595859159`：**PASS**；production config、synthetic runtime、real Google Drive fixture、live external AI、exact Firebase release、OAuth redirect、production UI 與 final mandatory gate 全 PASS。Live external AI execution `life-assistant-postdeploy-acceptance-n8zk9` successful。
- 因此 **#54 regression = CLOSED / PASS**；current latest-release Drive Knowledge health 已恢復全綠，可繼續 #7 Shopping。

## Shopping productization checkpoint — Package #7（2026-10-07）

- [x] 正式 Web entry：`/more/shopping`。
- [x] Shopping list create / list UI。
- [x] Shopping item create UI。
- [x] item category presentation。
- [x] item done / undone mutation 與清單完成進度。
- [x] loading / empty / error states。
- [x] mobile + desktop production acceptance。
- [x] 真實 PostgreSQL runtime：Shopping list/item create、toggle 與 reread persistence。
- [x] exact release CI / Firebase / Cloud Run / post-deploy evidence。

Evidence：

- Final release SHA：`1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d`。
- CI #566 / run `37621843816`：PASS。
- Firebase Hosting #384 / run `37622140411`：PASS。
- Shopping UI Acceptance #4 / run `37622504893`：PASS；desktop list/category/progress、create list、create item、toggle item，以及 mobile More → Shopping navigation/controls 全 PASS。
- Deploy Cloud Run #438 / run `37622140547`：PASS；authenticated cloud-domain acceptance 真實走 PostgreSQL，Shopping persistence path PASS；其餘既有 Cloud Run regression gates 亦 PASS。
- Post-deploy Runtime Acceptance #104 / run `37624483194`：PASS。
- 同 release Habits UI #15 / run `37622504844` 與 Notes UI #149 / run `37622504904`：PASS。
- Mobile acceptance 初次 failure 根因為 Flutter `ListTile` merged semantics：精確字串 `購物清單` 無法匹配 title+subtitle semantic label。Final fix `1dd0b1f...` 改用已在 Habits 驗證過的 regex semantics locator 並加入 `/more/shopping` route assertion；production acceptance PASS。

**Package #7 = DONE / PASS；Phase 1 closure = 7/11 = 63.6%。**

### Independent latest-release Drive Knowledge health note

- Historical Drive Knowledge Runtime Acceptance #63 / run `37625447402`：attempt 1、2 均 **FAIL**；當時 task exit `91` = Gemini-only failure。
- Newer Drive Knowledge #70 / run `37702785541`（release `6331b27`）**FAIL**，live external AI task exit `93` = `90 + Gemini(1) + OpenRouter(2)`；Groq 不在 failure mask 中。#63 的單-provider 結論不得套用到 #70。尚無兩家各自 HTTP / output 根因 evidence。
- Diagnostic code release candidate `8dedf655f007d3e21d647f06c7a7552322c8abce` adds direct Gemini / OpenRouter probes after the aggregate failure. CI #574 / run `37705390278` PASS；deployment / new live acceptance remain **NOT VERIFIED** until the workflow chain completes.
- 同一 #63 的 production config、synthetic Drive Knowledge runtime、real Google Drive fixture、exact Firebase release、OAuth redirect、Drive Knowledge production UI 均 PASS。
- 此 issue 維持 **OPEN / FAIL**；不更改 mandatory Drive Knowledge acceptance 標準、不以 fallback success 冒充 Gemini direct health PASS。它不取消已具完整 direct evidence 的 Shopping Package #7 DONE，但 Phase 1/latest-release cross-feature health 不得宣稱全綠。


### Shared Codex-first consumer checkpoint — 2026-10-08

- User-selected provider order for Drive AI: **omniAgent private Codex Cloud Run → Gemini → Groq → OpenRouter**, retaining explicit consent, original provider direct-health gates and local output validation. New server-side `SharedCodexEnrichmentProvider` and account-scoped stable ownerId are implemented on `main`.
- Secret boundary: **only** the omniAgent shared service accesses the existing `omniagent-shared-codex-auth`. life_assistant has no direct access or copies; legacy `janus-mart-codex-auth` is **not** reused by life_assistant. No new Codex Secret created.
- Runtime activation is `CODEX_PRIMARY_ENABLED=true` for Cloud Run API and Drive acceptance job; implementation supports `false` fail-closed in other contexts. Dedicated caller SA and audience-bound ID token are mandatory. Explicit Codex model remains unset until provider entitlement is verified; shared service default applies.
- Test implementation: `backend/tests/test_shared_codex_provider.py` covers isolated owner UUID, identity audience, request envelope, 429 backoff, 400/401/403/502, bad output and fallback order. Shared runtime probe `scripts.run_shared_codex_identity_acceptance` checks anonymous denial, wrong-project 403 and actual completed HTTP 200 with response trace. The existing mandatory Drive Knowledge flow additionally directly tests Codex health when enabled.
- Consumer status **PARTIAL**: backend unit tests in CI #583 were **PASS**; complete CI, exact release deployment, correct Cloud Run *service/job* identities and IAM, real signed HTTP 200, true product E2E, and mobile/desktop UI verification are **NOT VERIFIED** until live evidence is available. Don't infer consumer DONE from omniAgent's own service acceptance.
- Context: historical Drive Knowledge #63 exit 91 (Gemini), newer #70 exit 93 (Gemini+OpenRouter) remain historical failures; Codex adoption alone cannot rewrite either as PASS.


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

## Release Evidence Snapshot — 2026-09-28

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
- 尚未由本次真實驗收覆蓋：Calendar list/read、真實 provider failure / Drive partial-success；destructive confirmation enforcement 已於 2026-09-28 的 dev-test runtime checkpoint 補齊。

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

### Calendar destructive confirmation enforcement checkpoint — 2026-09-28

- Backend enforcement commit：`610ee93c83c1a4ef0929cfee2e937eb6098e34ce`；final explicit-confirmed Flutter client path + analyzer fix release SHA：`afa02e150f64b7204bd070747f298e91bef295fa`。
- CI #286 / run `36335471982`：PASS；backend / Alembic / deployment scripts / Flutter Analyze / Test / Web build / branding 全 PASS。
- Firebase Hosting #185 / run `36335593932`：PASS。
- Cloud Run #239 / run `36335593931`：PASS。
- PostgreSQL migration execution `life-assistant-db-migrate-lk5v5`：PASS。
- Cloud Run revision `life-assistant-api-00075-7fg`：100% traffic；`/health` = `{"status":"ok"}`、`/ready` = `{"status":"ok","database":"ok"}`、unauthenticated API 401 protection PASS。
- Authenticated Cloud Domain acceptance execution `life-assistant-cloud-domain-acceptance-9ggvl`：PASS。
- Google failure + destructive-confirmation acceptance execution `life-assistant-google-failure-acceptance-9twg6`：PASS。
- Runtime gate 驗證 Calendar DELETE 未帶 confirmation 時回 `409 confirmation_required` 且 outbound provider call = 0；帶 `explicit_user:calendar.delete:<event_id>` 後 HTTP 204、outbound provider call = 1，並只留下 1 筆 `calendar.delete / success / deleted` activity evidence。
- Flutter `ApiClient.deleteCalendarEvent()` 不會自動送 confirmation；Acceptance Center 在使用者先確認整體驗收後才走 `deleteCalendarEventConfirmed()` explicit-confirmed path。
- SQLite success-path execution `life-assistant-sqlite-backfill-acceptance-8hv2l`：PASS；failure-path execution `life-assistant-sqlite-backfill-failure-acceptance-g84n9`：PASS。
- Cloud Run deploy 仍有既有非阻塞 `--allow-unauthenticated` IAM policy re-apply warning；revision 仍 100% serving，health/ready/401 checks PASS，未做額外 IAM 變更。
- **Calendar destructive confirmation enforcement：DONE / PASS。此證據不代表所有 destructive/sensitive action 的 final policy gate 已完成。**



### CI/CD stuck-recovery checkpoint — 2026-10-06

- [x] 共用 Cloud Run Job wait 具 bounded execution：`RUN_JOB_MAX_WAIT_SECONDS` 預設 660 秒。
- [x] wait 期間具可觀測 heartbeat：`RUN_JOB_HEARTBEAT_SECONDS` 預設 30 秒。
- [x] success / timeout / failure 分別輸出 `cloud_run_job_wait=PASS / TIMEOUT / FAIL` 並保留 failure diagnostics。
- [x] Deploy Cloud Run job 具 outer `timeout-minutes: 90`。
- [x] workflow-run concurrency group 已依 upstream conclusion 隔離，避免 ineligible/skipped workflow_run 與有效 success run 共用同一 cancellation group。
- [x] runtime evidence：Deploy Cloud Run #419 中多個 `life-assistant-core-acceptance` execution 實際持續輸出 30 秒 heartbeat，最後均輸出 PASS；workflow overall PASS。
- [x] Post-deploy Runtime Acceptance #84 PASS。
- [ ] 任何未來 timeout/failure 仍需依 `recovering-stuck-ci-deploys` 分類 queued / silent-but-bounded / true timeout-failure / chain break；不得因本次 hardening 已 PASS 就假設未來卡住都屬同一原因。

## Phase 1 Status

**PARTIAL**。Cloud target schema/API/runtime parity、SQLite→PostgreSQL migration tooling / synthetic runtime acceptance、Google provider synthetic failure / partial-success runtime acceptance，以及 Calendar destructive confirmation enforcement 已完成，但 Phase 1 仍不可標 DONE，主要缺口：

- Real historical SQLite user-data migration：尚未取得實際 source file，故 NOT VERIFIED。
- Calendar 真實帳號 read/list 尚未以新版 Acceptance Center 重跑；真實 Google provider failure / Drive partial-success 仍 NOT VERIFIED（synthetic failure-path runtime 已 PASS）。
- Backend authorization / minimum-permission、Cloud mutation idempotency，以及其他 destructive/sensitive action final policy gate；Calendar DELETE explicit confirmation 已 PASS。
- Bridge/MCP Release Gate。
- Task checklist / 完整 Web UX、Notes search、Attachment strategy 等剩餘 Phase 1 product acceptance。

## Phase 1 不阻塞項目

Android/iOS 正式上架、完整 offline-first、SQLite local-cache 雙向 sync、Today Cockpit、Attention/Focus、Routine Library、Global Capture、Plan/Review、Contextual AI、People context 延後至 Phase 1.5 / Phase 2。
# CI/CD V2 acceptance — 2026-10-08

**IMPLEMENTING / NOT CLOSED**. Required: real main Push → us-central1 2nd Gen
CI Trigger → affected backend/Alembic/Flutter tests → explicit full-SHA Manual
Release Trigger → immutable Docker digest → verified
migration → no-traffic candidate → Firebase Preview gates → live exact SHA →
runtime/real UI/Drive/Calendar/providers → unchanged schedules/job readback →
reference-aware cleanup dry-run → retire conflicting Actions entrypoints.
Runbook and baseline evidence: `deployment_runbook.md`. New intercepted UI
contract PASS must never stand in for true network/browser acceptance.
Single-user owner allowlist and shared Codex isolation require actual candidate
evidence; multi-owner collaboration is not added. Historical provider FAIL retained.
Trigger/build/revision/release identifiers will be recorded only after actual
execution. No mock/localhost or single Build PASS qualifies for CLOSED.

### CI/CD V2 runtime identity correction (2026-10-08)

- Commit `3a6941bddd7a2ba658240a1e74e255b5ee27da15` real push build `e95cee5e-2c91-44b3-ad81-baa2da1979ad` FAILED before tests: Cloud SDK image has no `python3` on PATH. No deployment executed.
- User approved and applied only deployer Service Account User on existing `omniagent-codex-life-client`, and that caller Secret Accessor on `life-assistant-bundle`. No default Compute impersonation grant.
- Candidate/API and the three existing Life Assistant jobs use this dedicated identity on the next release; shared provider checks metadata email and requests the audience-bound identity token directly. Existing live revision remains unchanged until acceptance.
- V2 remains OPEN; Push CI, release and all mandatory live gates still require real PASS evidence.

### Real Push CI evidence (2026-10-08)

- SHA `02a43ebf4de5209d720506f9da165ad93f8bfe8a`, regional build `cc710f32-0e32-48f6-9471-90399e771f63`: **SUCCESS**, 04:51:46.864–04:58:35.557 UTC (408.693 seconds).
- GCP Backend 403 tests PASS; Flutter 63 tests PASS; analyze completed with existing 109 info diagnostics and unchanged no-fatal-infos policy; Web build and branding checks PASS. Alembic verification reached `20261007_0010`.
- No Docker push, migration job, Cloud Run deployment or Firebase publication in Push CI. Full-SHA manual Release and live gates remain pending.
- Worker list-price estimate: 6.8116 minutes × $0.006 = **$0.04087**, before shared free allowance; not an invoice. Public standard GitHub runner remains $0 runner cost under its existing policy. V2 is not claimed cheaper. Failed build time and release/job/log costs must also be counted.
- Earlier build `29f9f507-64d5-4a92-a0fe-3bc9350c3eba` failed on official Flutter manifest URL 404; corrected root verified against official manifest and 3.47.3 checksum.

### Manual Release attempt evidence (2026-10-08)

- Latest SHA `09e89ccd59d71a2b5d561e0b079dd863e5b3e32c`: Push CI `c84b3516-20ec-4db3-ad7f-1b3fe8af1993` SUCCESS (125.993 seconds; worker list-price $0.01260).
- Manual candidate-only Release `b4ca14a1-c29a-44cb-9a02-ecd9fd83f5ac` FAILED at Scheduler baseline readback: deployer lacks `cloudscheduler.jobs.list`. Backend 403 / Flutter 63 tests and Web/Docker build passed; no migration, candidate deployment or Firebase Preview occurred.
- Immutable image: `us-central1-docker.pkg.dev/gen-lang-client-0593591102/cloud-run-source-deploy/life-assistant-backend@sha256:d882d80ad30f5dc898c3b306a7c0bdacb3a68872bf0cb1526c2ebaf80d9460ff`.
- Release worker runtime 556.119 seconds (9.26865 min), list-price $0.05561 before shared allowances; failed releases cost worker time too. Cloud Run Job costs not incurred by this attempt. This is an estimate, not billing-export evidence.
- Existing user credential readback: us-central1 Scheduler `janus-ingestion-daily`, `30 * * * *`, Asia/Taipei, ENABLED; untouched. Life Assistant jobs remain the same three existing names. This does not satisfy automated deployer readback.
- Auto-review rejected the additional Scheduler Viewer IAM grant because previous approvals did not include it. Exact read-only grant requested separately; no bypass or gate removal.
- Candidate/live revision, Preview/live publication, true UI/Provider/Integration acceptance and cleanup remain pending. **V2 OPEN / NOT CLOSED**.

### CI/CD V2 暫停 checkpoint — 2026-10-08

狀態：**PAUSED BY USER / OPEN / NOT CLOSED**。以下為真實 runtime evidence，不代表完整 Release PASS。

- Release source SHA：`09e89ccd59d71a2b5d561e0b079dd863e5b3e32c`；Push CI `c84b3516-20ec-4db3-ad7f-1b3fe8af1993` SUCCESS。
- 使用者核准後已套用 deployer 的 `roles/cloudscheduler.viewer`；本輪 deployer Scheduler/Jobs baseline readback PASS。排程未修改，未執行生活總排程或每小時監控。
- Manual candidate-only Build `af461348-13ee-4f43-833a-428f06f4e813` 已依使用者「先暫停」取消，讀回 **CANCELLED**。執行時間 2026-10-08 13:34:12–14:00:06 Asia/Taipei（1554.286 秒）；worker 牌價估算 US$0.15543，未扣共用免費額度、不含 Jobs/Logs/Registry，非帳單。
- Migration `life-assistant-db-migrate-m2jcx` PASS：pre/post `20261007_0010`，`verify-current`，沒有重複 schema migration。
- Candidate `life-assistant-api-00174-luw` 0% 流量；正式 `life-assistant-api-00173-gpf` 保持 100%。Candidate digest：`sha256:53d9a712e7a5262ce5c8a9f452d6e9cc531f38e78922fcd40f40712247b1a201`。
- Candidate health/readiness/database、未登入 401、OAuth redirect、single-user owner allowlist PASS；這不等於全部 Auth/owner/live gates 已完成。
- Cloud domain parity PASS：`life-assistant-core-acceptance-jgz2t`；Checklist PASS：`life-assistant-core-acceptance-d67jw`；idempotency PASS：`life-assistant-core-acceptance-mhbmk`。
- 取消時已啟動的 Google failure execution `life-assistant-core-acceptance-h65nm` 讓它完成清理；後續唯讀 readback succeededCount=1、runningCount=0（PASS）。Cloud Build 已取消，不把此結果寫成整輪 Release PASS。
- Firebase Preview/Live 均未發布；既有 live Hosting baseline version `7269b54b36337ed6`。尚缺 SQLite backfill success/failure、真實 HTTPS Google/DB/browser、POST/Drive/Calendar/Shared Codex/External Provider、Preview/Live UI/integration、post-deploy readback 與安全 image cleanup。
- Provider 既有 Gemini/OpenRouter FAIL 保持獨立 blocker；本輪尚未執行 Provider gate，沒有新增 Provider PASS 證據。Image 沒有實體刪除，沒有新 GCS evidence bucket。
- 舊 Actions 自動部署入口已改 manual；main 文件 push 只會觸發 CI，不恢复 Release。恢復前先讀回殘留 executions/traffic/Hosting、確認 main 完整 SHA、適用 CI/Ready gate；不得重跑正在執行的資料寫入型 Job或自動 downgrade DB。

### CI/CD V2 resumed implementation checkpoint — 2026-10-08

- User resumed CI/CD V2 after the cancelled candidate run. The previous
  `af461348-13ee-4f43-833a-428f06f4e813` remains CANCELLED, not PASS.
- Contract repair: backend-only release now builds a preview-only Flutter artifact
  and verifies Firebase Preview pinned to no-traffic Candidate instead of
  mislabeling live-frontend/live-API checks as candidate compatibility. This
  preview is never promoted to Hosting live unless frontend source changes.
- Added a backend-only prepare test and workflow/static coverage. No GCP
  migration, candidate, preview or promotion is claimed by this source commit.
- New Push CI / manual Release / runtime readback / production integration:
  **NOT VERIFIED** until fresh per-SHA GCP evidence is observed. Provider
  Gemini/OpenRouter FAIL remains an independent mandatory blocker.
