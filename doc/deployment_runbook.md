# Life Assistant V3 — 固定備選 staging Hosting 發布與恢復 Runbook

> **規則建立：2026-10-09｜文件規則已核准；固定 staging live 自動發布與端到端驗收：NOT VERIFIED / 待實作。** 本節是現行 **V3 staging** 操作規則；下方 V2 Cloud Build 內容僅是歷史紀錄。程式碼與實際部署狀態仍以 GitHub `main`、Firebase Hosting／Cloud Run readback 和每次 Actions 證據為準。**此文件更新不代表已建立、發布或驗證 staging live，也不授權直接執行 staging/production 部署。**

## 網址、site 與 channel（禁止混稱）

| 用途 | 固定網址或範圍 | 性質與使用規則 |
| --- | --- | --- |
| 正式服務（production） | https://gen-lang-client-0593591102.web.app/ | 正式 Firebase Hosting site 的 **live**；遵守既有 V3 獨立正式發布門檻 |
| 固定備選（staging） | https://life-assistant-v3-stage-tl15.web.app/ | **獨立 staging Hosting site** `life-assistant-v3-stage-tl15` 的 **live** channel；發布成功並完成 readback 後，才可把它當成可用固定入口 |
| 本次 SHA 驗證用 Preview | staging site 上的 `v3-<SHA 前 10 碼>` 等短期 channel URL | 只用於本次候選版本驗收；現行 `--expires 1d`，會到期，**不能當固定備選網址** |

固定入口始終指向 **staging site 的 live channel**，不是 production site 的 live、也不是 staging site 的限期 Preview。維持 staging 與 production **不同 Hosting site**，不可把 runner-local staging `hosting.site` / `pinTag` 寫回 production `firebase.json` 的預設發布組態。

## 每次 staging 發布順序（目標流程／未宣稱已全部實作）

1. **鎖定版本與前置 Gate**：選定本次完整 **40 字元 Git SHA**，核對 GitHub `main`、對應 CI 與所有適用 V3 Gate；後端候選必須是已驗證的 public GHCR immutable digest、Cloud Run **0% traffic** revision 與唯一 candidate tag。不得因 staging 發布而跳過既有候選 HTTP/auth、真實資料庫、provider、UI、回滾及正式 Release Gate。若要使用 `promote=true` 之正式流程，仍按既有獨立正式批准及門檻處理；**staging 流程不得自行發起正式 promotion**。
2. **先保護上一個 staging live**：在任何 staging live mutation 前 readback 並記錄上一個**已驗證** Hosting version／release ID、release SHA、其 `/api/**` 與 `/auth/**` 的既存 backend pinned revision/tag，及固定 URL 的可用狀態。保留可執行的原版本恢復路徑；若無可信 readback／恢復來源，fail closed，不覆寫 staging live。
3. **只建立本次 SHA Preview**：在 staging site 的獨立短期 channel 建置 Flutter Web，寫入 `build/web/release.txt` **完整 SHA**，使用 runner-local Hosting rewrite `pinTag`，令 `/api/**`、`/auth/**` 指向**本次對應**的 Cloud Run candidate revision/tag。Preview 有效期可以是 1 天，但僅作驗收；不可宣稱永久入口。Preview 的 Hosting version 必須可識別並保留到本次部署。
4. **先驗證 Preview，失敗即停**：至少檢查 `release.txt` 與完整 SHA 完全一致；檢查實際 Hosting version 的兩條 rewrites、服務 `life-assistant-api` / `us-central1` 及 **實際 pinned backend revision/tag** 與本次候選一致，不能僅靠 `pinTag: true` 字樣、`/api/v1/tasks` 回 401 或 redirect 就假定已指向正確 revision。對 **`/api/**` 與 `/auth/**`** 分別執行適用的 HTTPS、401/session/OAuth redirect/proxy 與候選整合驗收；UI 桌機／手機、真實 provider/登入、資料與 V3 其他 gate 仍須依原政策取證。無法證明路由綁定、Google OAuth 或本次後端相容性時標 **NOT VERIFIED**，不得更新 staging live。
5. **只發布已驗證 Hosting version 到 staging live**：上述 Gate 全 PASS 後，以 Firebase Hosting 版本／release clone 或等價受控方式，將**同一個已驗證的 Preview Hosting version** 發布至 `life-assistant-v3-stage-tl15:live`，不得在此步重新建置、改指後端或改發到 production。發布後再次 readback staging live **Hosting version ID / release SHA / rewrites 的 exact candidate revision/tag**，並在固定網址 `https://life-assistant-v3-stage-tl15.web.app/` 驗證前端完整 SHA、`/api/**`、`/auth/**` 和適用真實端到端門檻。固定 staging 使用者流量必須維持 pinned revision 的可用性；revision/tag 清理策略不得破壞仍被 staging live 引用的後端。
6. **失敗處置**：任何 Preview／候選／路由／驗證失敗都**保留上一個已驗證 staging live 版本**，不能拿未驗證 Preview 覆蓋。若**更新 staging live 後**驗證失敗，必須恢復第 2 步紀錄的上一個 Hosting version（連同對應 rewrites/pinned backend）、重新確認固定網址與 API/auth 功能。若恢復失敗、版本無法定位或原 revision 已不可用，須明確回報 **ROLLBACK FAIL / staging 狀態 NOT VERIFIED**、受影響版本及實際 URL，不得宣稱已恢復或以更新 production 替代。
7. **嚴格隔離 production**：本 staging 作業**不得執行** `deploy-firebase-hosting.yml` 的正式 `firebase deploy --only hosting`、不得更新 `gen-lang-client-0593591102` Hosting site、不得改動正式 Cloud Run backend traffic percentages、不得移除／放寬／改寫任何原有 V3 production Gate。只允許對 Life 的獨立 staging Hosting site 進行版本發布與安全 readback；若目前 workflow 無法滿足，列為待辦，不用未受驗證的替代捷徑。

### OAuth 固定設定（一次性前置；不隨 SHA 重設）

- 必須先完成固定 staging 網域與**實際使用的 callback URI** 在 Google OAuth Client、適用的 Firebase Auth authorized domain／相關回呼白名單、後端 OAuth redirect／session/cookie 設定上的對應檢查，並以 staging 網域完成真實登入與 callback 驗收（若適用）。保持 production `https://gen-lang-client-0593591102.web.app/auth/callback` 原設定不受影響；**不能擅自把既有 production callback 視為 staging 登入已驗證**。
- 一旦 `https://life-assistant-v3-stage-tl15.web.app/` 所用的 staging 網域及實際 callback 經設定且驗證通過，**後續更換候選 SHA／Preview／Hosting version 不需要重設 OAuth 網域或 callback**；只需檢查它仍有效。只有 OAuth Client、實際 callback 路徑／網域或授權設定確實變更，才重新設定並重新驗收，不應每次發版重複增刪 redirect URI 或 authorized domain。
- **目前證據：NOT VERIFIED**。現行 V3 workflow 的 `GOOGLE_REDIRECT_URI` 與 redirect assertion 指向 production `/auth/callback`；沒有固定 staging 網域真實 OAuth 往返及穩定 callback 的已通過證據。短期 Preview 的 `--no-authorized-domains` 不等於完成固定 staging OAuth。

### 每次發布都要保留的稽核紀錄（不可只寫 PASS）

記錄在該次 GitHub Actions run summary／可追溯的 release evidence；不要因每次候選版本更新就修改本段 runbook，**僅在流程、規則或門檻實際改變時修改規則**。

| 必填欄位 | 紀錄要求 |
| --- | --- |
| GitHub / CI | 完整 40 字元 SHA、workflow run URL/ID、CI 與必要 V3 Gate PASS/FAIL/NOT VERIFIED |
| Preview | Preview channel／URL、Preview **Hosting version ID**、到期時間、本次 SHA、驗證結果 |
| Backend | public GHCR digest、候選 Cloud Run **revision 名稱與 tag／tag URL**、0% traffic 證據、兩條 rewrite 實際綁定的 revision/tag |
| Staging | 固定 URL `https://life-assistant-v3-stage-tl15.web.app/`、staging live 發布前／後 **Hosting version 或 release ID**、release SHA、前後 API/auth/實際 OAuth 測試結果 |
| 故障／恢復 | 未發布／已更新、恢復目標舊版 ID、恢復操作與 readback、恢復後固定網址及 API/auth 測試、恢復失敗的明確 FAIL 和原因 |
| Production 隔離 | production Hosting 未更新、production Cloud Run traffic 不變的 readback 結果；若讀不到標 NOT VERIFIED 而非推定 PASS |

不在 evidence 中輸出 OAuth secret、cookie、session、credential 或使用者敏感資料。**發布成功、路由核實、正式網址不可受影響及 staging live E2E 是分開驗收項目。**

## 2026-10-09 GitHub 實作差距與後續工項

| 檢查來源／工項 | 核對到的實作與缺口 | 判定 |
| --- | --- | --- |
| `.github/workflows/v3-release-ghcr.yml` | 已使用 `STAGING_HOSTING_SITE=life-assistant-v3-stage-tl15`、確認獨立 site、runner-local `pinTag` 兩條 rewrite，建立 `--expires 1d` 的 SHA Preview 並驗證 `release.txt` 完整 SHA + unauthenticated API 401；**未**將已驗證版本發布到 staging **live**，未 readback 固定 staging live Hosting version。 | Preview 程式路徑 **PASS（已實作）**；固定 staging live **NOT VERIFIED／待實作** |
| `.github/workflows/v3-firebase-preview-probe.yml` | 建立／檢查同一 staging Hosting site；使用 `v3-candidate-diagnostics` 及 `--expires 1d` 短期診斷 Preview，非最新正式 SHA staging live 的發布證據。 | 診斷 Preview **≠** 固定 live |
| `firebase.json` | repository 預設 `/api/**`、`/auth/**` rewrite 指向 `life-assistant-api`／`us-central1`；只在 V3 Preview runner local 設定 `hosting.site` 與 `pinTag`。尚未看到對已發布 Hosting version 的 **exact** backend revision/tag 讀回驗證。 | rewrite 存在 **PASS**；版本級 pinned 對應 **NOT VERIFIED** |
| `.github/workflows/deploy-firebase-hosting.yml` | `workflow_dispatch` 執行 `firebase deploy --only hosting`，檢查正式 `https://gen-lang-client-0593591102.web.app/`；**這是 production workflow**，不是 staging live 更新器，staging 作業不得觸發它。 | production 專用，禁止 staging 重用 |
| staging clone / 驗證 / restore | 未發現完整 SHA Preview PASS → **同版** staging live clone → 固定 URL 的 SHA+API/auth+revision/tag 核對 → 失敗時上一版 restore 及恢復 readback 的受控自動流程。 | **待實作／NOT VERIFIED** |
| 固定網域 OAuth | V3 redirect expectation 是 production callback；未見 staging 固定 callback 的設定及真實登入驗收證據。 | **待一次性設定／NOT VERIFIED** |
| Production 保護與 V3 Gate | 現有 V3 的獨立正式 candidate/promotion/rollback/live checks 必須原樣保留；此文件**沒有**改變 workflow、Hosting live、Cloud Run traffic 或 OAuth 資源。 | 文件修改範圍 **PASS**；未執行新的 runtime 驗收 |

**下一步待辦（不是本次實作）：** 在現有 V3 流程旁新增受控的 **staging-only** version clone/live 驗證與恢復路徑；補 exact Hosting version→candidate revision/tag 的兩條 rewrite readback、production 隔離驗證與稽核欄位；完成固定 staging OAuth 一次性配置及真實 E2E。不得把「site 已建立」「Preview 可瀏覽」「workflow 綠燈」當作上述 staging live 完成。

---

> **歷史／已被取代（2026-10-08）**：以下保留 CI/CD V2 Cloud Build 執行與失敗證據，**不再作為正式新部署操作手冊**。現行 V3 政策請見 [CI/CD V3 — GitHub Actions + public GHCR + Cloud Run digest](ci_cd_ghcr_release_policy.md)；既有 V3 發布已實作，但上方固定 staging live 路徑仍待實作及實測。不得照此 V2 runbook 再新增 Cloud Build 主線，舊 runtime evidence 不因設計變更而消失。

---

# Life Assistant CI/CD V2 Deployment Runbook

Status: **RESUMED / OPEN / NOT CLOSED** (2026-10-08). This replaces the deployment
runtime release only after all V2 live gates pass. Existing product completion evidence
and existing provider FAIL records remain authoritative.

Policy is exclusively `PROJECT_RULES.md` → CI/CD V2 集中發布政策. main Push
runs CI only. Ready packages use the manual Release operations below.

## Trigger operations

- Push CI: `life-assistant-v2-main`, ID `70ca60f2-8519-40c4-9422-5ac78f1b355f`.
- Manual Release: `life-assistant-v2-release`, ID `892a893e-173f-49b2-9055-d5a9adc21496`.
- Both use the same 2nd Gen repository and `cloudbuild.yaml`; `_PIPELINE=ci`
  cannot enter Docker/deployment steps. Release requires exact-SHA Push CI PASS.

After Ready review/tests/contracts and successful Push CI, invoke:

```sh
gcloud builds triggers run life-assistant-v2-release \
  --project gen-lang-client-0593591102 --region us-central1 \
  --sha FULL_40_CHARACTER_SHA --substitutions _PIPELINE=release,_PROMOTE=false
```

Read candidate/Preview evidence and measured cost first. For the final
centralized release invoke the same exact SHA with `_PROMOTE=true`; it must
still match current main. Keep all provider gates. Do not use `[skip ci]` for
intermediate commits by default.

## Scope and identities

- Repository `tommylin15/life_assistant`, push branch regex `^main$` only.
- Existing second-generation connection `tommy-github`, repository
  `tommylin15-life_assistant`, region `us-central1`.
- `cloudbuild.yaml`, full `COMMIT_SHA`, `CLOUD_LOGGING_ONLY`; no nested source
  builds and no new legacy/multiregion bucket.
- Reuse `life-assistant-github-deployer`; no service account key.
- FastAPI remains Cloud Run; Flutter remains Firebase Hosting. Shared Codex
  remains the existing OmniAgent service. No OmniAgent/Janus code changes.
- Runtime identity: existing `omniagent-codex-life-client`; deployer has
  Service Account User only on it, caller has Secret Accessor only on
  `life-assistant-bundle`. Shared Codex uses metadata email/identity directly;
  no default Compute token-minting grant.
- Never mutate Scheduler configuration or execute scheduled business jobs.
  Only the three existing Life Assistant migration/acceptance jobs are updated.

## Release sequence

1. Check full SHA and current main; compare paths against deployed `release.txt`,
   covering every batched commit. Missing baseline fails toward complete testing.
2. Python import, backend tests, Alembic offline SQL, branding source checks;
   Flutter 3.47.3 analyze/tests/web build and branding equality.
3. Single Docker build/push, full SHA tag, resolve immutable digest.
4. Serialize mutable deployment operations by Cloud Build creation order;
   refuse a superseded main SHA and skip successful duplicate SHA/phase builds.
5. Existing migration job executes the release module, then no-traffic tagged
   candidate. Set the approved dedicated caller identity on API and the three
   existing jobs; preserve VPC, secrets and other existing settings.
6. Candidate health/readiness/401/OAuth; six existing core gates; actual HTTPS
   authenticated Google session, PostgreSQL persistence and owner-bound audit.
7. All existing post-deploy/Drive/Calendar/provider gates run against the release
   image. Gemini/OpenRouter diagnostics preserve aggregate failure.
8. Every backend-changing release gets an isolated Firebase Preview with Cloud
   Run `pinTag`, even when Flutter source is unchanged; this preview-only
   Flutter build is a deliberate safety cost and must never clone to Hosting
   live for a backend-only release. This avoids misrepresenting a browser test
   against the old live API as candidate compatibility. Stamp full candidate
   SHA and verify branding,
   cache, manifest, auth, API and all eight existing UI scripts. Their intercepted
   API tests are explicitly UI contracts, not proof of live integration.
9. Additional live browser reads use a real Google session and observe actual
   API responses without route interception, desktop and mobile.
10. `_PROMOTE=false` stops after candidate/preview. Only `_PROMOTE=true` may
    promote traffic and clone the exact verified preview to live.
11. Live exact SHA, true HTTPS/DB/browser gates, all UI and provider gates;
    Scheduler readback unchanged, job image readback, image cleanup dry-run.
12. Read back legacy Actions entrypoints: deployment and acceptance workflows
    expose `workflow_dispatch` only, preserving manual diagnosis/recovery.
    They retire automatically triggered deployment per the latest user policy.
    V2 is still not CLOSED until all live evidence passes.

## Recovery

- Before promotion failure: existing live traffic and live Hosting stay serving.
  Candidate and migration failure are failures, never CLOSED. Additive migration
  may have already run; no automatic downgrade or data deletion.
- After promotion failure: restore saved exact Cloud Run revision percentages.
  Use Firebase Console Hosting release history to roll back to the recorded
  previous version, then verify `release.txt`, `/auth/login`, `/api/v1/tasks`
  401, authenticated runtime and UI. Never restore DB by dropping tables.
- If Cloud Build is interrupted during promotion, inspect actual traffic and
  Hosting release before another deployment; use recorded previous revisions.
- A superseded build must not promote. Push latest work through CI and explicitly
  invoke the Ready manual Release SHA again.
- Evidence: Cloud Logging structured `gate/status/release_sha` lines; copy
  non-sensitive closure evidence and exact Build/revision/digest IDs into this
  repository. No GCS evidence write or staging/log bucket is required by V2.

## Artifact safety

Existing latest-only asynchronous policy can delete runtime/rollback images.
Keep it in **dry-run** during V2 validation. `cleanup_plan()` inventories all
Cloud Run revisions/jobs, protects their image references, checks SHA256 digest
syntax and only considers the three exact Life Assistant package names. Mutable
runtime references protect their entire package. A cleanup plan is evidence,
not deletion authorization or proof of physical deletion. Before any deletion,
refresh references and check the plan again; never delete another package.

## Cost comparison before cutover

The repository is public. Standard GitHub-hosted runners are free for public
repositories ([GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)).
The old pipeline also incurs GCP Docker build, Cloud Run acceptance and storage
cost; migration to Cloud Build does not remove these.

Default Cloud Build e2-standard-2 in us-central1 is $0.006/build-minute, with
2,500 promotional free minutes per billing account/month; allowance is shared
and cannot be assumed available ([Cloud Build pricing](https://cloud.google.com/build/pricing)).
The 120-minute bound caps build-worker list-price exposure at $0.72/build,
excluding existing runtime executions, egress and storage. No paid pool/new
database/bucket is requested. Successful duplicate SHA builds skip release work.

Observed old Firebase job `37714548567`: 2026-10-08 01:48:27–01:50:49 UTC,
142 seconds, standard public GitHub runner = $0 runner charge under that policy.
Existing Cloud Build `3d803831-b558-47a7-bfa6-eabba6ad23fd`: 111.20 seconds;
estimated e2-standard-2 worker list price $0.01112 before account free credits.
This is measured duration, **not a billing invoice**.

Existing Artifact Registry readback: 382.428 MB; free first 0.5 GB/account and
$0.10/GB-month above it ([Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)).
Other projects/packages share account allowance. V2 creates no GCS objects or
bucket dependency; existing legacy bucket costs remain separate from V2.
Exact billed AR/GCS amounts require billing export/readback.

Record V2 actual build duration, machine, account free-tier usage and billing
evidence before formal cutover. No automatic claim that V2 is cheaper.

## Current blockers / baseline failures

- IAM auto-review initially rejected proposed repo writer / project log-writer /
  build viewer grants; user subsequently approved these exact minimal roles.
  Proposed GCS evidence writes have been removed; no storage grant is needed.
- Existing deployment `37714548574` failed at shared caller IAM policy access;
  do not grant broad IAM policy administration to CI as a workaround.
- Existing Notes/Habits/Shopping/Calendar UI runs at `a9a570c` failed exact
  release SHA checks; not demonstrated product bugs and not PASS.
- Drive #63 exit 91 and #70 exit 93 remain historical external-provider FAIL.
- Shared Codex consumer completion remains PARTIAL pending actual runtime proof.
- Core Tasks/Notes/Habits/Shopping models have no owner columns. The existing
  product is single-user: candidate must set existing `ALLOWED_GOOGLE_EMAIL`
  protection to the explicitly verified fixture owner; CI checks non-owner
  rejection, live gates check real owner session and invalid identity rejection.
  Shared Codex additionally retains stable owner/project isolation gates.
  This does not establish multi-owner core data isolation or add collaboration.

## Resume after user pause

1. Wait for explicit user resume. Read the final checkpoint in `acceptance.md`.
2. Confirm cancelled Build status, remaining Job executions, production traffic and Hosting version. Do not launch duplicate writing executions.
3. Confirm current main full SHA and applicable successful Push CI; a documentation push changes main SHA. Previous candidate is evidence for its original SHA, not the new SHA.
4. Review Ready/migration/API/auth contracts and invoke candidate-only manual Release for the chosen current SHA. Preserve all unfinished gates and existing Provider blockers.
5. Promote only after every required candidate/preview gate passes; then execute live/post-deploy gates. Do not downgrade DB or delete images merely because a Build was cancelled.
