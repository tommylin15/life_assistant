# life_assistant — Current State (2026-10-10)

## 本批開發與驗收安排（2026-10-10 最新）

- 新交接表、穩定去重、活動卡片、兩個入口及個人動作已在工作樹實作；開發驗證與 deployed／runtime 驗收分開記錄。細節見 [活動規格](curated_activity_user_features.md)。
- 活動能否開放一般使用者由 admin 在後台設定。AI 管理補強暫緩，僅 AI 管理相關能力限 admin；不把這項限制套用到全部新功能。
- 下一輪合併新活動功能、後台及個人首頁做正式上線驗收。真實 Sheet write scope／版本回執、GCP Job、Google Calendar 與新 SHA 的 CI／staging 尚待驗證；舊版測試站登入已完成。


## 測試站驗收更新（2026-10-10；優先於下方歷史快照）

- **固定測試站發布與真實 owner Google 登入驗收：PASS / 已完成。** [V3 run 38030697455](https://github.com/tommylin15/life_assistant/actions/runs/38030697455) 的 real database/auth、Preview、fixed staging preflight，以及「Promote exact Preview to independent fixed staging live and verify owner OAuth」均 success。使用者於本次對話確認 https://life-assistant-v3-stage-tl15.web.app 已能正常登入使用。
- 測試站 `release.txt` 實際讀回 `3fb06169ad01a065fef60eecc2010c459970746e`，與上述成功發布 SHA 一致。先前 wrong_callback、Missing session 與未驗收敘述是修復前歷史，不再列為目前登入 blocker。
- **後續版本發布是獨立狀態：** main `4219510cf2764c7b7bce9286ec2374d9ca36a1df` 的 CI success，但 [run 38037092043](https://github.com/tommylin15/life_assistant/actions/runs/38037092043) 在 real database/auth acceptance failure，尚未執行 Preview 或固定 staging 發布。不可據此把既有可用測試站改標 FAIL；也不可把測試站已驗收推定為最新 main 或 production 已發布。
- 下一步仍是新交接 Sheet → Life Job → PostgreSQL → ACK/ERROR 的實作與真實驗收，以及活動產品待辦；不要求重做已完成版本的測試站登入驗收。

**Overall PARTIAL**; release proof and runtime evidence are required beyond GitHub implementation.

Architecture: Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL. CI/CD V3: GitHub Actions → immutable public GHCR digest → Cloud Run candidate → gated Firebase Hosting.

## Active curated-activity data path

**Latest approved design:** ChatGPT explores and verifies in Drive → [dedicated 30-column handoff Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) → Life daily GCP Job → validated PostgreSQL upsert / version-checked Sheet ACKED/ERROR → signed-in Flutter. Life does not crawl sources, run old Queue/claim/lease or apply second-stage AI. 本批 source 已加入固定交接表、版本回執與永久 event_key；舊 direct API／URL identity 保留相容。真實 Sheet／GCP runtime 尚待驗收。

**Implemented in current main at source level**: additive Alembic 0015, authenticated bounded batch upsert with stable identity, curated listing/status, Flutter curated UI and site navigation. New `events` feature defaults **owner-only beta** until actual acceptance; old verified-only API preserved. **New Drive handoff Job / Sheet ACK / stable event_key dedup / real DB readback and production deploy: NOT VERIFIED**. Scheduled direct-writer token is no longer the approved default path. Do not reactivate old Sheets/Queue ChatGPT task. Read-only GCP inventory [#38012860019](https://github.com/tommylin15/life_assistant/actions/runs/38012860019) confirms the obsolete `life-assistant-free-events` Cloud Run Job still **EXISTS** (job existence alone does not prove it is scheduled). The regional Cloud Scheduler readback [#38013575831](https://github.com/tommylin15/life_assistant/actions/runs/38013575831) is **PASS** for `us-central1`: no Scheduler Job names/targets matched the retired `life-assistant-free-events` job. This is scoped negative evidence only; other regions and external invocations remain NOT VERIFIED. No deletion/pause performed.

## New activity user UX — source implemented, runtime pending

[限時機會／活動探索規格](curated_activity_user_features.md) splits **user-facing entry points only**, not the curated database. 本批已實作父子卡片、兩個入口、個人收藏／追蹤／Task、資訊／報名／確定參與 Calendar 與提前 popup；真實 Google、Sheet 及新 SHA runtime 尚 NOT VERIFIED。旅遊行程與 App 推播尚未實作；admin 決定活動入口開放對象。AI 管理補強暫緩。

## P1 modules

**Source implemented**: feature rollout API + owner UI, versioned account-owned personal navigation & Home cards, responsive bottom/rail/drawer, partial Home task/calendar/habits/events/projects cards, internal Drive AI admin allowlist/pause, aggregate-only usage and direct rate-limited probe. Personal Google OAuth/Drive AI content consent never delegated to administrator. **Actual per-device UI / provider smoke / runtime verification: NOT VERIFIED**. Usage tokens/cost, advanced budgets/alerts and owner E2E remain partial.

## Historical fixed staging OAuth incident (2026-10-10; superseded by PASS above)

**2026-10-10 follow-up — V3 [#38023532632 attempt 2](https://github.com/tommylin15/life_assistant/actions/runs/38023532632/attempts/2):** candidate, database acceptance, Preview, and fixed-staging preflight **PASS**. A new staging Hosting version `36b7a8ddcf919c04` was temporarily published, but the subsequent post-publish check exited 1 **before** `staging_oauth_canary=ACTIVE`. Its precise failing subcheck is **NOT VERIFIED** because the old script logged no failure layer. The staging-only rollback reported **PASS**, restoring version `e3a6dd23aec06848`. Real owner Google OAuth remains **NOT VERIFIED**; do not retry the old release SHA as if fixed.

Following this evidence, `scripts/v3_fixed_staging_release.sh` on `main` adds bounded 24-attempt post-publish live readback (5-second spacing), explicit failed-gate phase markers, strict failure on REST version/rewrites/API 401, and visible canary-activation logging. These are **source fixes only** until current-SHA CI and a new staging-only release prove runtime PASS. Production Hosting and traffic remain outside this staging task.

Live read-only OAuth redirect probe [#38022456431](https://github.com/tommylin15/life_assistant/actions/runs/38022456431): **fixed staging `/auth/login` FAIL** — `redirect_uri` still points to production `/auth/callback` while the `__session=oauth:` state cookie is set on the staging hostname; this explains user-observed post-Google-login `401 Missing session` at the cross-origin callback. SHA Preview also points to the production callback and is **not a valid Google login host**. Production `/auth/login` targets production and remains PASS for redirect origin only. Anonymous Flutter homepage checks [#38022194645](https://github.com/tommylin15/life_assistant/actions/runs/38022194645) PASS for all three sites, but **do not prove login**.

The current `main` backend has `oauth_redirect_for_request` support for the fixed staging hostname; **the existing fixed staging live backend pin is not yet promoted to a version that returns this callback**, so this is a **deployment/runtime gap, not a confirmed new source-code defect**. Next gate is **staging-only** V3 pinned version release + real owner OAuth callback/session readback with production traffic and Hosting unchanged. Do not claim staging OAuth PASS, production cutover, or successful user login before those runtime results. The one-time read-only probe job was removed after the result.

## Historical fixed staging OAuth callback repair (2026-10-10; subsequently accepted above)

New staging release [#38027300562](https://github.com/tommylin15/life_assistant/actions/runs/38027300562) failed with `staging_google_redirect=FAIL wrong_callback` after exact live Hosting version, release SHA, pinned `/api/**` + `/auth/**`, and unauthenticated API 401 all **PASS**. Rollback to `e3a6dd23aec06848` **PASS**. This proves the old OAuth host-header heuristics are insufficient for actual Firebase Hosting → Cloud Run requests. Production release/traffic were not promoted.

Repair in `backend/app/api/auth.py`, `lib/web/login_page.dart` and `scripts/v3_fixed_staging_release.sh`: fixed staging Flutter calls the explicit `/auth/staging/login` backend entrypoint, which always uses the **constant allowlisted** staging Google callback, stores staging provenance in the existing HttpOnly/Secure `__session` OAuth state and authenticated session, and reads that provenance on callback, `/auth/me`, and Google incremental authorization. Production keeps normal `/auth/login` and production callback. No dynamic user-supplied callback URL. In `v3-release-ghcr.yml`, the Preview must now prove `/auth/staging/login` sets state cookie and emits the fixed staging redirect **through the real Hosting rewrite**, before any fixed staging mutation. Tests cover missing forwarded headers, OAuth callback, wrong state, verified session and owner E2E evidence. The failure stage remains fail-closed with staging rollback.

**Status: source implementation complete; full exact-SHA CI, preview smoke, fixed staging live, true owner Google login and session readback: NOT VERIFIED until independent runtime evidence is observed.** Do not ask the owner to rerun the old release, and do not present the restored staging as repaired.

## Evidence
Prior V3 historical release [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) PASS for its own previous SHA only. P0/P1 candidate CI [38009774496](https://github.com/tommylin15/life_assistant/actions/runs/38009774496) had backend, ephemeral PostgreSQL, Flutter and deployment checks PASS for SHA `19f693263bc9c546a2d81239b9fc236cc53833e3`. Subsequent implementation changes must pass CI for their **own** SHA; historical PASS is not inherited.

Current post-CI follow-up: repaired Drive AI provider selection overwriting note candidates; added fixture regression tests and a rollback-only curated 0015 live DB smoke to V3 release, with migration before Drive AI runtime check and mandatory fourth PostgreSQL CI gate. Added the optional, separately controlled fixed staging live source flow requiring valid prior version, actual pinned Hosting/API/auth version, owner OAuth E2E and rollback; this code does not mean staging has been changed. These changes require new exact-SHA CI and still do not prove any live production integration.

Full consolidated matrix: [P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md); [active TODO](todo.md). No unsupported claim of DONE.

## Dedicated Drive handoff update (2026-10-10)

[新「交接資料」Google Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) 已建成、30 欄與規格分頁 readback PASS；初始 0 筆，尚未把原精選池部分待核 53 筆直接移入。Life Job 實際消費新表、回 ACKED/ERROR、持久化 event_key/content_hash、最小 Sheets 編輯授權、30天成功清理、Scheduler 與 PostgreSQL/Flutter E2E 均 NOT VERIFIED。本輪僅更新 GitHub 文件，不更動 production runtime 或程式。
