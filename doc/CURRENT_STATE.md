# Life — Current state
Snapshot: **2026-10-15 Asia/Taipei**. This is a concise evidence index, not an automatically refreshed monitor. On any new code SHA, independently recheck the matching runs and runtime.

## Verified source/release baseline
At audit time the source baseline was `fc800b280be59f44f485dfc170fe45a14fc9c981` (2026-10-14 GitHub main). Evidence:
- **CI: PASS** — [#38567184081](https://github.com/tommylin15/life_assistant/actions/runs/38567184081), all four jobs `backend`, `flutter`, `deployment-scripts`, `free-events-postgres` succeeded.
- **Controlled one-time gate: PASS for its source/CI checks only** — [#38567521419](https://github.com/tommylin15/life_assistant/actions/runs/38567521419). Its successful workflow job alone is **not** a verified Sheet importer Execution/readback.
- **Life→Gateway→Gemini signed synthetic smoke: PASS** — [#38570644451](https://github.com/tommylin15/life_assistant/actions/runs/38570644451), including real Life runtime signed call and unchanged production traffic. Authenticated browser user's `POST /ai/text` full UX E2E remains **NOT VERIFIED** by this test.
- **Promoted production Cloud Run release: PASS for its defined release gates** — [#38572432707](https://github.com/tommylin15/life_assistant/actions/runs/38572432707): immutable GHCR digest, 0%-candidate, PostgreSQL additive migration 0018, core DB/auth smoke, Preview, fixed staging, 100% traffic promotion, postdeploy, controlled rollback and restoration, Job image alignment.
- **Production Firebase Hosting: PASS for its defined checks** — [#38576667267](https://github.com/tommylin15/life_assistant/actions/runs/38576667267): Hosting deploy/readback plus Task/Project automated browser acceptance.
- **Revision retention: PARTIAL** — the release log shows `PARTIAL_PROTECTED`, `remaining_count=62` (2026-10-14); tagged/traffic/rollback-protected revisions cannot be blindly pruned to 10. This is not a release-failure claim.
- **Importer image pin: PASS; importer execution in that release: NOT_RUN** — the release's own summary says `curated_handoff_image=PASS … execution=NOT_RUN`.

## Open evidence gaps (do not infer PASS)
1. **GAS → importer → PostgreSQL → Sheet:** GAS 07:30 Asia/Taipei trigger's actual installation/success, the newest production importer Execution exit code, Sheet version-fenced ACK/ERROR and PostgreSQL row-level readback are **NOT VERIFIED** by the above release runs. Old 52 ACKED/2 ERROR is a historical snapshot only.
2. **Account isolation:** migration and synthetic rollback-only multi-tenant DB acceptance ran in release. Full three-real-account cross-user read/write matrix remains **NOT VERIFIED**.
3. **Gemini UX:** signed text path is proven, but individual logged-in user API/frontend handling, timeout/failure UX and quotas are not proved by synthetic smoke.
4. **Activity UX:** current source has activities, personal actions and Calendar integration paths. Live multi-user collection, cross-day search, pagination stability, Google Calendar mutation/readback and consistent old-favorite linkage require independent acceptance.
5. **Drive AI provider governance:** source has admin controls/health counts, but token/cost-based budgets, per-user consent E2E and multi-provider runtime cost proof are **NOT VERIFIED**.
6. **Shopping/list edit/delete/batch and Task delete white-screen:** GitHub contains changes and matching main CI is PASS; user-reported hands-on verification was positive on 2026-10-14. Do not promote this to an independently automated full multi-account/regression proof.

## Rules
- `PASS / FAIL / NOT VERIFIED` apply **per** implementation, tests, CI, deployment, runtime, integration; aggregate DONE only with required evidence. Otherwise PARTIAL.
- The user's decision removed **manual Owner Google OAuth E2E as a blocking release step**, not automated OAuth/session/redirect/401 checks. Unrun human OAuth E2E = NOT VERIFIED, not PASS.
- This snapshot is superseded by later matching-SHA actions or GCP runtime evidence, not by documentation alone. Prior detailed history remains in Git history and [the archived pre-cleanup snapshot](archive/CURRENT_STATE_through_2026-10-14.md).
