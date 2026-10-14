# life_assistant — Current State（2026-10-14）

> **本段優先於下方 10/12 以前的歷史快照。** 本次 01～07 工程批次尚待其新 SHA 的 CI、staging 和 runtime 實際結果，不以文件或 commit 判 DONE。

## 2026-10-14｜新回報：購物 CRUD／批次輸入、待辦刪除白屏

GitHub main 原實作只有購物清單建立、單項新增及勾選更新；未提供清單／品項的獨立編輯與刪除，也不能多行同批新增。待辦刪除確認在巢狀 Navigator 中使用頁面 `context` pop，有誤關頁面的風險；本次以對話框自己的 `dialogContext` 關閉。

本次變更需在新 SHA 上取得 CI、Flutter、staging／runtime 與真實帳號 readback，未查證前均為 **NOT VERIFIED／PARTIAL**，不能推論正式站已更新。

## 2026-10-14 已取得的 Release 證據
- 正式 main `7c42a01d58f4bc7df16fa44a63845d8baa58c794`：完整 CI 四 job [#38497669129](https://github.com/tommylin15/life_assistant/actions/runs/38497669129) PASS；正式後端 Release [#38502483297](https://github.com/tommylin15/life_assistant/actions/runs/38502483297) PASS（包含 PostgreSQL migration 0018、合成 tenant rollback-only readback、postdeploy、正式流量與 Job pin）；正式 Hosting [#38505066967](https://github.com/tommylin15/life_assistant/actions/runs/38505066967) PASS（release.txt、API 401、OAuth redirect、Task/Project browser acceptance）。
- **不能混淆：** 活動 Job digest/contract readback **PASS 但 execution=NOT_RUN**；GAS 07:30 觸發器及定期實際終態 **NOT VERIFIED**。前一次交接快照為 52 ACKED／2 ERROR，這是來源行級狀態，不能證明後續新一輪 Job PASS。
- Life→Gateway→Gemini：10/13 Signed Smoke [#38376914628](https://github.com/tommylin15/life_assistant/actions/runs/38376914628) PASS（合成文字，非使用者 API）；10/14 [#38500240196](https://github.com/tommylin15/life_assistant/actions/runs/38500240196) FAIL，Cloud Run execution `life-assistant-core-acceptance-jfb25`，根因尚未被讀回，不能猜測為 Gateway 或 Gemini。
- Revision 保護清理：正式 Release `PARTIAL_PROTECTED`，剩餘 60 個 Cloud Run revisions。依現行政策保護 tag／流量／回滾 revision，不強行刪到 10 個。
- 一般帳號：之前 Staging 真人活動收藏／Task／日曆基本操作 PASS；本次 formal release rollback-only 多租戶合成資料庫測試 PASS；未取得三個真人帳號跨讀寫的完整矩陣。
- Drive AI：現有控制與執行筆數有效；Token、費用及預算**未埋點，不得提供猜測值**。

## 2026-10-14 同批 01～07 修正／驗收
本次單一 main commit 的變更需由 GitHub 最新 Actions 獨立核對。活動匯入以一次性受控工作流驗證當前**已正式發布的 live digest**，僅會使用既有 Life Job 並執行冪等 Sheet/DB 匯入，不設定額外定期 cron；新版 Gemini Signed Smoke 失敗增加限縮資訊的診斷；活動快速查詢補有據跨日重疊；後台用量顯示只提供實際已儲存執行次數；Revision 僅報保護原因，不卸 tag。詳見 [todo](todo.md)。新 SHA 的 CI／staging／formal production／runtime 未跑完以前 **NOT VERIFIED**。

---

# life_assistant — Current State (2026-10-12)

## 2026-10-12｜`verified_at_tpe` 選填、GAS 07:30 排程與接收真實驗收（最新）

- **契約**：Drive 原生交接 Sheet「交接規格」已明定 `verified_at_tpe` 選填；來源未知時保持空白，Life 模型應轉成 `None`／JSON `null`，不得取代為批次／發現時間。提供核證時間時仍需 +08:00、不得冒填。此修正維持 event_key/content_hash、post-commit Sheet ACK 與其他資料驗證。
- **2026-10-12 GAS 實測與 root cause**：`previewLifeHandoffPrerequisites()` 回 `READY`；Job/live image canonical digest 一致（`sha256:19ed58af30bfd752c133a09bfb489cfeda4e75f3026fc06d94a1fe9a384884a8`），`runLifeHandoffDaily()` 回 `ACCEPTED_NOT_COMPLETED`，Operation `6c041ac8-847e-4885-9fd9-e745156622be`。Cloud Run Execution `life-assistant-free-events-zc4xr` Exit 1。使用者提供實際 stderr：先有 HandoffItem Pydantic 單欄驗證錯誤（截圖/片段未含失敗欄名，不能只推定 `verified_at_tpe`），舊 importer 在逐筆 `receipt()` 重新讀整表時又遭遇 `sheets_http_429`，未處理例外造成 Job 崩潰；GAS jobs.run 已接受不是容器失敗原因。
- **Sheet 快照**：本次檢視共有 54 筆，其中 28 ACKED、20 ERROR、6 READY；20 ERROR 均為 `invalid_handoff_record`，且 `verified_at_tpe` 為空。此關聯不保證其餘所有欄位有效，也不證明新部署後已全部入庫。
- **GitHub 修復（2026-10-12）**：`backend/scripts/import_curated_from_sheet.py` 已把 post-commit Sheet 回執改為固定 key/完整業務版本 fencing 的批次回寫（整批預讀＋bounded `values:batchUpdate`＋整批讀回），替代每列兩次整表讀取，429／暫時 5xx 採有界 Retry-After／exponential backoff；無法核對或仍限速則 FAIL/PARTIAL，不假稱 ACK。Pydantic 非敏感欄位路徑／錯誤類型會記於 Job logs，`verified_at_tpe` 未知繼續保持 null。回歸測試包含 bulk receipts、重試限速、重跑補 ACK、不同版本不誤 ACK；本輪 `7d00ef0` GitHub CI Backend 與 free-events-postgres jobs PASS，其他 CI job／完整 workflow 結論及正式映像／runtime/DB/Sheet 仍待各自驗證。
- **交付關卡**：GitHub source/schema/test 修正不等於已部署。須確認此修正 commit 的 CI、正式 V3 release 與 Job digest 更新，取得新 Execution 與真實 PostgreSQL/Sheet ACK readback。已有同日 GAS ledger，不要盲目再次呼叫 Job；**GAS 每日 07:30（Asia/Taipei）是使用者最新確認的排程設定**，但 Apps Script 時間觸發器的存在／排程時刻／定時觸發紀錄仍 NOT VERIFIED，不可標 DONE。


## 2026-10-11｜交接批次 CI/CD 映像責任移轉（待實際部署驗證）

GitHub 舊每日 09:30（歷史設定）的 `curated-handoff-daily.yml` 已從 source 移除 `schedule`，保留 `workflow_dispatch` 手動備援；備援只驗正式 live 與 Job digest／固定匯入設定，不再自行更新 Job 映像。正式 `v3-release-ghcr.yml` 在 `promote=true` 且 live、回滾、Revision 保留關卡通過後更新現有 `life-assistant-free-events` Job 的 GHCR immutable digest／Python importer／交接 Sheet 固定 ID 與 apply，驗證 Job readback，不執行匯入。GAS 接收排程**現在以每日 07:30（Asia/Taipei）為最新設定**；實際 GAS Trigger 是否已啟用、07:30 自動觸發與完成情況，未能由 GitHub 內容直接驗證（NOT VERIFIED），不得推定已成功或已停用。舊 GitHub cron 已取消，部署／runtime／PostgreSQL／Sheet ACK 仍待驗收，不能標 DONE。詳見 [交接契約](curated_sheet_job_ingestion.md) 及 [V3 policy](ci_cd_ghcr_release_policy.md)。


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
