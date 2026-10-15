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
- **Revision retention: PARTIAL** — the release log shows `PARTIAL_PROTECTED`, `remaining_count=62` (2026-10-14); tagged/traffic/rollback-protected revisions cannot be blindly pruned to 10. This is not a release-failure claim.
- **Importer image pin: PASS; importer execution in that release: NOT_RUN** — the release's own summary says `curated_handoff_image=PASS … execution=NOT_RUN`.

## 2026-10-15｜P0/P1 Actions 版本整併（source；runtime evidence 待驗）
- 失敗的 staging-only [#38664515788](https://github.com/tommylin15/life_assistant/actions/runs/38664515788)：固定 staging 與 OAuth redirect 已 PASS，最後因舊 SHA 的獨立 Gemini smoke 派送步驟 FAIL；後續成功 staging [#38665056200](https://github.com/tommylin15/life_assistant/actions/runs/38665056200) 已證明部署路徑可用。獨立 [smoke #38667868716](https://github.com/tommylin15/life_assistant/actions/runs/38667868716) 的舊 Gateway pilot tag 不存在，不能據此推論正式 Gemini API 故障。
- 已精簡 main workflow 29→21，保留 CI 四項獨立 jobs，停用過時 one-time／bootstrap；文件專用 CI 不啟動 staging；Gemini Smoke 改手動／現行 live URL；修正 Revision 清理於 V3 成功後直接執行，保留正式流量與十版候選、精確偵測併發 ready/created 更新。這些 source 實作**不是** Cloud Run 最後十版的 runtime PASS。

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
