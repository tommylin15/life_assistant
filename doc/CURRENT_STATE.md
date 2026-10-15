# Life — Current state
Snapshot: **2026-10-15 Asia/Taipei**. This is a concise evidence index, not an automatically refreshed monitor. On any new code SHA, independently recheck the matching runs and runtime.

## 2026-10-15｜正式版真人驗收補正（使用者驗收回報）
- **正式 production Google OAuth 真人登入／授權／登入後可使用：PASS（使用者真人驗收）**。先前「真人 OAuth 尚未驗收」的風險判定已由本次使用者明確回報取代；此 PASS 是正式已發布版本的人工 E2E 驗收，不是 GitHub Actions 自動測試的結果。
- **正式 production 多使用者資料隔離：PASS（使用者真人驗收）**。不再將「尚無真人驗收」列為本版 P0 阻塞。程式層的 synthetic tenant rollback-only acceptance 另有 Release 證據，不可將兩者混成同一驗收來源。
- 本次回報未提供各真人帳號數目、逐 API 測試矩陣與逐次操作日誌，因此不附加未經證實的「精確三帳號／全路由覆蓋」聲明；但不因此否認已取得的**正式版真人驗收 PASS**。新 SHA 的變更仍須按受影響範圍執行回歸；人工 OAuth E2E 不恢復為每次 release 的強制門檻。

## Verified source/release baseline
At audit time the source baseline was `fc800b280be59f44f485dfc170fe45a14fc9c981` (2026-10-14 GitHub main). Evidence:
- **CI: PASS** — [#38567184081](https://github.com/tommylin15/life_assistant/actions/runs/38567184081), all four jobs `backend`, `flutter`, `deployment-scripts`, `free-events-postgres` succeeded.
- **Controlled one-time gate: PASS for its source/CI checks only** — [#38567521419](https://github.com/tommylin15/life_assistant/actions/runs/38567521419). Its successful workflow job alone is **not** a verified Sheet importer Execution/readback.
- **Life→Gateway→Gemini signed synthetic smoke: PASS** — [#38570644451](https://github.com/tommylin15/life_assistant/actions/runs/38570644451), including real Life runtime signed call and unchanged production traffic. Authenticated browser user's `POST /ai/text` full UX E2E remains **NOT VERIFIED** by this test.
- **Promoted production Cloud Run release: PASS for its defined release gates** — [#38572432707](https://github.com/tommylin15/life_assistant/actions/runs/38572432707): immutable GHCR digest, 0%-candidate, PostgreSQL additive migration 0018, core DB/auth smoke, Preview, fixed staging, 100% traffic promotion, postdeploy, controlled rollback and restoration, Job image alignment.
- **Production Firebase Hosting: PASS for its defined checks** — [#38576667267](https://github.com/tommylin15/life_assistant/actions/runs/38576667267): Hosting deploy/readback plus Task/Project automated browser acceptance.
- **Revision retention at that historical 2026-10-14 baseline: PARTIAL** — the original release had `PARTIAL_PROTECTED` and `remaining_count=62`. **Superseded by the 2026-10-15 V3 #38675052751 real deletion/readback PASS (68→10); see latest section below.**
- **Importer image pin: PASS; importer execution in that release: NOT_RUN** — the release's own summary says `curated_handoff_image=PASS … execution=NOT_RUN`.

## 2026-10-15｜P0/P1 Actions 版本整併（source；runtime evidence 待驗）
- 失敗的 staging-only [#38664515788](https://github.com/tommylin15/life_assistant/actions/runs/38664515788)：固定 staging 與 OAuth redirect 已 PASS，最後因舊 SHA 的獨立 Gemini smoke 派送步驟 FAIL；後續成功 staging [#38665056200](https://github.com/tommylin15/life_assistant/actions/runs/38665056200) 已證明部署路徑可用。獨立 [smoke #38667868716](https://github.com/tommylin15/life_assistant/actions/runs/38667868716) 的舊 Gateway pilot tag 不存在，不能據此推論正式 Gemini API 故障。
- 已精簡 main workflow 29→21，保留 CI 四項獨立 jobs，停用過時 one-time／bootstrap；文件專用 CI 不啟動 staging；Gemini Smoke 改手動／現行 live URL；修正 Revision 清理於 V3 成功後直接執行，保留正式流量與十版候選、精確偵測併發 ready/created 更新。這些 source 實作**不是** Cloud Run 最後十版的 runtime PASS。

## 2026-10-15｜P0/P1 發布後最新讀回
- [V3 staging-only #38670120522](https://github.com/tommylin15/life_assistant/actions/runs/38670120522) 的 fixed staging、Preview、OAuth redirect 全部 PASS，且正式流量維持不變；當次 maintenance step 被 newer main SHA 擋下，輸出 `retirement=SUPERSEDED`，**沒有執行任何 Revision 清理**。GitHub 顯示該 step success 僅代表 skip 成功，不是清到 10 版。
- 最新 main `c7ecb96` 的 [CI #38670191848](https://github.com/tommylin15/life_assistant/actions/runs/38670191848) 四項 PASS；[V3 staging #38670433974](https://github.com/tommylin15/life_assistant/actions/runs/38670433974) Preview PASS 但 preflight HTTP 404，固定 staging 發布前即 FAIL，沒有切正式流量，後置退版未執行。預檢的 Firebase Hosting API 或 CDN 資源沒有明確標示，因此針對 preflight 添加不放寬 gate 的 bounded retries 與精確資源類別診斷後重新驗證。
- 維持區分 CI PASS、Staging PASS、Revision retention PASS 與 production traffic；**當時（#38670433974）最新 10 版仍 NOT VERIFIED；後續 #38675052751 以真實 GCP 刪除／讀回完成 68→10，已取代該舊結論**。

## 2026-10-15｜P0/P1 CI/CD 實際結案（最後 verified main 23d898c）
- **CI 四項 PASS**：[CI #38674814026](https://github.com/tommylin15/life_assistant/actions/runs/38674814026)，SHA `23d898ccd6906d037bc3ee16d60af782c36def92`；Backend、Flutter、deployment-scripts、free-events-postgres 四項全部 successful。
- **V3 staging-only PASS**：[V3 staging-only #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751)，同 SHA；固定 staging 的 preflight、Preview、hosting pinned rewrites、OAuth redirect、API 401/readback 成功，`staging_live=PASS`、`traffic_unchanged=true`。Production **沒有** promotion，本輪不能據此推論新版正式產品驗收。
- **Revision Retention PASS（真實 GCP 讀回）**：Release 內 `life_cloud_run_retirement_apply.py` 實際讀得清理前 **68**，解除 **56** 個舊 0%-traffic tags、刪除 **58** 個歷史 Revisions，最後 `stage=DONE,status=PASS,remaining=10,live_unchanged=true,services_deleted=0,jobs_deleted=0`；`life-assistant-api-00281-men` 仍為本輪唯一 100% 正式流量的 baseline；正式 flow 沒有動到其他 Service／Job。本結果取代本文件更早 `remaining_count=62` 的歷史快照。
- **前一版 404 已修復**：上一版 [#38670433974](https://github.com/tommylin15/life_assistant/actions/runs/38670433974) 失敗於 staging preflight HTTP 404；最新版本新增明確資源分類及有上限的重試後，真實 preflight 與 staging 全部 PASS。舊 [#38670120522](https://github.com/tommylin15/life_assistant/actions/runs/38670120522) 雖 release PASS，但當時 `retirement=SUPERSEDED`，沒有清理；真正清理執行證據只以 #38675052751 為準。
- **範圍 DONE**：僅指 GitHub Actions P0/P1 精簡、staging 404 修復、Revision 10 版清理及完整匹配 SHA CI/staging/runtime gate；活動 GAS importer、Gemini 登入後 UX、各項功能 Live E2E 等仍依下列 backlog **NOT VERIFIED**，不能混同完成。

## 2026-10-15｜01–03 同批開發與驗收（最新）
- **01｜GAS/Life Sheet 匯入：** GitHub `main` 新增 Postgres `pg_try_advisory_xact_lock` 保護整批同時進入的 GAS/手動 importer，避免兩次匯入競爭回執；原 event_key/content_hash 長期去重、個別欄位錯誤與技術狀態分離規則保持不變。新增 mock lock 測試 CI PASS，但 staging-only 不會更新 production Job，故實際正式 importer 新映像及 GAS 07:30 尚 **NOT VERIFIED**，不得因 source 變更或先前 Job pin 而宣告結案。
- **01｜實際來源讀回：** 2026-10-15 對指定 Google Sheet「交接資料」唯讀 A1:AD1000，54 筆，ACKED 53、ERROR 1（`invalid_handoff_record`）；最近可見 ACK 時點 2026-10-14，ACKED 不代表 10/15 GAS 有/無執行（UNCHANGED 不重寫 ACK 時間）。[Cloud Run 唯讀調查 #38710051187](https://github.com/tommylin15/life_assistant/actions/runs/38710051187) 找到 16 個歷史 Job Executions，未找到可匹配的 importer 聚合日誌；Apps Script trigger 時間和同輪 PG row readback **NOT VERIFIED**。此調查未再次執行 Job，亦未寫 Sheet。
- **02｜Shopping＋Task：** Shopping batch sort_order 加 per-list advisory transaction lock，補全 Flutter widget 測試涵蓋多項新增、品項刪除、清單更名及刪除後重新載入；Task 已有 nested Navigation 刪除後保留頁面的 widget regression，均納入 Flutter CI。真實多使用者 runtime 仍獨立。
- **03｜活動／個人操作：** 後端列表回傳時間快照 `snapshot`，後續分頁以 `as_of` 鎖定來源建立時間，前端在篩選／重整／收藏後清掉舊頁碼並更新快照；有 Postgres 測試涵蓋新活動插入與跨日活動，原 Calendar/Task URL 相容單元測試保留。Calendar OAuth 真實寫入及其他特殊 E2E 未被這些 tests 證明。

## Open evidence gaps (do not infer PASS)
1. **GAS → importer → PostgreSQL → Sheet:** GAS 07:30 Asia/Taipei trigger's actual installation/success, the newest production importer Execution exit code, Sheet version-fenced ACK/ERROR and PostgreSQL row-level readback are **NOT VERIFIED** by the above release runs. Old 52 ACKED/2 ERROR is a historical snapshot only.
2. **Gemini UX:** signed text path is proven, but individual logged-in user API/frontend handling, timeout/failure UX and quotas are not proved by synthetic smoke.
3. **Activity UX:** current source has activities, personal actions and Calendar integration paths. Live multi-user collection, cross-day search, pagination stability, Google Calendar mutation/readback and consistent old-favorite linkage require independent acceptance.
4. **Drive AI provider governance:** source has admin controls/health counts, but token/cost-based budgets, per-user consent E2E and multi-provider runtime cost proof are **NOT VERIFIED**.
5. **Shopping/list edit/delete/batch and Task delete white-screen:** GitHub contains changes and matching main CI is PASS; user-reported hands-on verification was positive on 2026-10-14. Do not promote this to an independently automated full multi-account/regression proof.

## Rules
- `PASS / FAIL / NOT VERIFIED` apply **per** implementation, tests, CI, deployment, runtime, integration; aggregate DONE only with required evidence. Otherwise PARTIAL.
- The user's decision removed **manual Owner Google OAuth E2E as a blocking release step**, not automated OAuth/session/redirect/401 checks. 只有未執行的真人 OAuth E2E 才記 NOT VERIFIED；2026-10-15 已由使用者明確回報正式版真人驗收 PASS。
- This snapshot is superseded by later matching-SHA actions or GCP runtime evidence, not by documentation alone. Prior detailed history remains in Git history and [the archived pre-cleanup snapshot](archive/CURRENT_STATE_through_2026-10-14.md).
