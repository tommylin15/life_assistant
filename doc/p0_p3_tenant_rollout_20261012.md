# P0–P3 consolidated delivery evidence (2026-10-12)

Scope: authenticated general-account home/tasks/calendar/personalization, scoped
private notes/projects/habits/shopping, curated activity flow, UI/release.

## Delivered in source
- Existing P0 Flutter auth, tasks, calendar, personalized home/nav/logout
  and 11-card/UI implementation retained; second staging account OAuth E2E
  explicitly reported PASS by user for SHA a96f0798.
- Additive Alembic 0018 adds nullable indexed user_sub to legacy private tables,
  retaining every existing legacy NULL row. Only the configured Owner can read
  legacy NULL; all new private records carry the caller Google subject.
- Route guards cover listing, detail, mutations, note links/tags, habit history,
  shopping parent/child, project references from tasks/notes/shopping, Gmail
  project creation. Cross-tenant IDs must yield 404, not permit writes.
- Staging's approved tester can reach the four owner-scoped resources.
  Google Drive links, templates and admin remain blocked until separately
  audited. Private production access policy is unchanged.
- Audited curated listing/filters and account-owned personal actions now pass the
  staging tester route gate, but each remains subject to feature rollout and
  activity_access; ingestion, status and connector remain blocked.
- Existing curated UX V3, activity DB query and personal actions remain.
  Curated event release/visibility follows the separate admin rollout policy;
  exposing common curated data in staging is not equivalent to approval.
- Existing consistent feature header cards, notes category tabs and home cards
  remain unchanged. No user data deleted, no production traffic promoted.

## Mandatory gates and evidence
1. CI: all four jobs PASS on the single combined main SHA.
2. Additive migration Job: 0018 applied and verified before staged API readback.
3. Staging: exact SHA, pinned Hosting rewrites, 401 and Google redirect PASS.
4. Tenant runtime: Owner legacy visibility; second user cannot read Owner or
   third user notes/projects/habits/shopping; personal prefs/logout and tasks
   writable/readable without cross-account leakage.
5. Curated actions: real Sheet ACK/ERROR after DB commit, dedup and Google
   Calendar/Task source links separately verified; failure remains PARTIAL.
6. Production: only explicit V3 workflow_dispatch promotion and live gates.
   CI or source changes alone do not constitute DONE.

## 2026-10-13 Staging tester curated route correction
- Registered public signed-in endpoints are `/api/v1/free-events/curated`, `/api/v1/free-events/curated/filters` and `/api/v1/free-events/curated/actions`, **not** `/api/v1/curated`. The previous staging allowlist incorrectly accepted non-existent shortened paths; authenticated secondary testers were rejected before query execution.
- Stage tester route permissions now match FastAPI route registration and constrain per-item writes to existing V3 save/task/calendar_info actions. Owner-only status, connector, batch import, admin and historical follow/reminder actions remain denied.
- Admin feature-rollout policy is still enforced independently: ordinary users need enabled/all for opportunities/explore. No production account access or beta default is broadened.
- Flutter shows distinct signed-in 401, not-enabled 403, and other fetch failures. CI+Staging readback, and authenticated user E2E remain separately verified.

## 2026-10-13｜一般帳號活動載入與遺留資料安全檢查
- User reports real staging account activity list loads successfully for fixed staging release SHA `fc9c94d216a7985b88eb6ffe494457102afea59b`; classified **PASS for authenticated page load only**. Bookmark/task/calendar action E2E remains NOT VERIFIED.
- Security review: tenant visibility for NULL legacy rows now fails closed if `ALLOWED_GOOGLE_EMAIL` is empty/missing rather than interpreting every user as Owner. Explicitly owned records continue to be accessible only to matching Google sub. Added isolated unit coverage for empty, whitespace and missing owner config.
- This does not promote the production Hosting site or weaken rollout gates; current staging verification and production promotion are independent.

- Follow-up ownership audit: NULL legacy tasks use the same explicit Owner-only decision as notes/projects/habits/shopping. Being a non-staging account is **not** proof of legacy ownership; absent `ALLOWED_GOOGLE_EMAIL` denies legacy Task read/list for every account. Private Task rows with an explicit matching sub remain accessible.

## 2026-10-13｜活動三項核心操作 Staging 使用者實測回報

**Evidence type:** user-reported authenticated interactive E2E, **not** a GitHub
robot acting as a human. Staging fixed URL:
`https://life-assistant-v3-stage-tl15.web.app/`.

| 驗收項目 | 使用者回報 | 範圍／判定 |
| --- | --- | --- |
| 一般帳號活動列表載入 | 可正常載入 | **PASS** (staging user observation) |
| 收藏活動 → 已收藏速查／回讀 | 正確 | **PASS** (staging user observation) |
| 活動 → 建立待辦 → 待辦頁與活動網址 | 正確 | **PASS** (staging user observation) |
| 活動 → 日曆日期標記 → 日曆回讀 | 正確 | **PASS** (staging user observation) |
| Owner／第二使用者／第三使用者的實際私人資料隔離 | 沒有此三方實測回報 | **NOT VERIFIED** (已有自動測試，不等於真人多帳號隔離) |
| 正式站／正式 Backend 流量切換與 runtime 驗收 | 尚未進行本次 promotion | **NOT VERIFIED** |
| Sheet 接收排程 → Cloud Run Job → DB → Sheet ACK/ERROR 完整端到端 | 不屬於三項活動 UI 操作確認 | **NOT VERIFIED** |

**Latest source/runtime evidence before this user report:**
- `main` SHA `d58edf22a717f4578e9d9ac0c332574aa735897f`.
- [Four-job CI #38324692319](https://github.com/tommylin15/life_assistant/actions/runs/38324692319): **PASS**.
- [Automatic staging Release #38324917778](https://github.com/tommylin15/life_assistant/actions/runs/38324917778): **PASS**; logged `staging_live=PASS`, exact SHA above,
  Hosting version `sites/life-assistant-v3-stage-tl15/versions/df95e3d6166f15a7`,
  `staging_live_readback=PASS` for SHA and pinned API/auth rewrites,
  `staging_google_redirect=PASS`; `traffic_unchanged=true`;
  `owner_login_e2e=NOT_VERIFIED` is the separate manual Owner gate removed
  from release blocking by the 2026-10-12 policy. This record does not claim
  browser release-SHA readback was obtained from the user.
- This acceptance covers the three curated **user-facing operations**, not
  proof that every P0–P3 function, data feed, production multiuser policy or
  Google provider failure branch has passed.

**Overall for the requested P0–P3 release scope: PARTIAL** until all
applicable formal production gates and cross-account runtime evidence pass.

## 2026-10-13｜正式版一般 Google 帳號准入決策與安全門檻
- Owner 核准正式版加入一般帳號使用。Google `tokeninfo` 必須提供經驗證的 email、非空 `sub`、audience、issuer 與有效 exp。Login 不再把其他 Google email 一律拒絕；`Owner` 及管理員授權仍依 `ALLOWED_GOOGLE_EMAIL` 明確比對。
- **General-user API default deny:** `current_user` 在 staging 和 production 一律對非 Owner 套用已盤點路由白名單；僅准個人待辦/筆記/專案/習慣/購物/設定/Google Gmail、Calendar 整合，以及帶後台 rollout 開關的活動共用查詢和個人 action。舊 templates、Drive 文件與匯入、後台、curator 管理和未盤點路由仍 403；`ui/features` 對非 Owner 同步隱藏未審核模組。正式版登入不等於後台授權。
- 一般帳號不能讀 legacy NULL Owner 資料；私人資料存取仍用 `sub` 分流，Owner 的舊資料只允許明確 Owner 身分。此變更不授權清除資料或不經 V3 Gates 切換 production。
- 此項是**production access policy change**，必須先有新版單元測試／完整 CI／固定 Staging readback，再以現有 `v3-release-ghcr.yml` 的人工 `workflow_dispatch promote=true, publish_staging=true` 跑 production 真實驗收；不得改造自動 staging 入口去偷渡 production promotion。

## 2026-10-13 13:53 TPE｜production Hosting rollback after UI acceptance mismatch
- Latest general-account source SHA before fix: `77d03e142ef622228f065ae6b491f4c2f99163b4`.
- [V3 production backend promotion #38346524004](https://github.com/tommylin15/life_assistant/actions/runs/38346524004): **PASS**. Live candidate promotion, HTTP readiness, 401, OAuth redirect, post-deploy integrations and rollback rehearsal complete; backend at this SHA was promoted.
- [Production Hosting #38349502672](https://github.com/tommylin15/life_assistant/actions/runs/38349502672): **FAIL** despite successful Hosting publish, release SHA readback, root/401/auth/image checks. Both browser Task/Project user-journey acceptances reached the mobile navigation check after create/edit/filters/checklist and failed consistently expecting a visible `更多` destination. Production navigation source `lib/web/navigation_catalog.dart` explicitly removed "More" as a destination, and `lib/web/app_shell.dart` implements four-slot bottom nav (Home + 3 pinned), drawer for remaining features. This is an obsolete *test expectation*, not evidence of a failed Task/Project write.
- Workflow step **Restore previous production Hosting on failed readback: PASS**; previous Hosting version was restored. An independent unauthenticated public `release.txt` readback after rollback has not been obtained in this session: **NOT VERIFIED**. Current production backend is newer than restored Hosting; do not label overall product DONE.
- Corrected both UI acceptance scripts to assert that legacy `更多` is absent while requiring the four visible bottom destinations and the original end-to-end user operations. No changes to product navigation or live data.
- **Important SHA policy:** after this script change, original promoted backend SHA `77d03e1` is *not* sufficient to authorize new-SHA production Hosting. Require new four-job CI, new fixed Staging V3 PASS, then explicit V3 `promote=true,publish_staging=true` workflow_dispatch on latest main; only its same-SHA successful backend promotion may automatically dispatch Production Hosting. Never bypass release-SHA matching or live rollback gate.
