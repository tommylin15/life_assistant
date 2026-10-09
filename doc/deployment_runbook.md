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

## 2026-10-09 修正：固定 staging 真實 OAuth 的有界 canary 驗收

**關鍵現況與前後順序：** SHA Preview 是隨版本變更且有期限的不同網域，無法在固定 staging hostname 完成真實 Google OAuth callback。因此舊 `v3-staging-live.yml` 要求「尚未發布 staging live 就先有同 SHA 的 staging true-OAuth 成功 run」會永遠卡死；已改為受控、**僅 staging** 的短時 canary 例外，不放寬任何 production release gate：

1. 先有本次 full-SHA 完整 CI、V3 GHCR immutable digest、Cloud Run **0% 有 tag 候選**、SHA Preview、REST version→`/api/**`/`/auth/**` pinned revision、及既存 staging live 技術恢復基線的全部 PASS；任一失敗則不發布。
2. 鎖住 V3 共用發布互斥鎖，在 staging live 記錄原 version / SHA / backend pinned tag 與正式 Hosting version／正式 Cloud Run 流量，clone **已驗證的同一 Preview Hosting version** 至 staging live。此步 **不會**寫 production Hosting、變更正式流量、變更 Secret／IAM 或建立額外 Job。
3. **開始六分鐘真實 owner 登入 canary**。使用者在固定 `https://life-assistant-v3-stage-tl15.web.app/auth/login` 經 Google OAuth Web Client 完成 code callback，再在**相同瀏覽器 session** 開啟 `https://life-assistant-v3-stage-tl15.web.app/auth/me?staging_e2e=true`。新 backend 在驗證過 Google ID token、固定 staging origin、owner allowlist、Cloud Run `K_REVISION` 後，於既有 `execution_logs` 記錄 `staging_google_callback` 與 `staging_google_session` 的成功狀態，不記 token、auth code、cookie 或 email。
4. 同一 release workflow 使用**現有** `life-assistant-db-migrate` Job 的短期**唯讀 `python -c` arguments override** 查詢 `execution_logs`：必須在本次 canary 起算後、**同一 user_sub、同一 expected revision** 有兩筆成功事件才算 PASS。此驗收不做 migration 或資料異動，也不需要 Cloud Logging reader IAM。若 timeout、登入失敗、DB 唯讀查詢失敗或其他後續 Gate 失敗，當次工作流在同一 shell trap **clone 回原 staging Hosting version**，再核對 version、原 SHA、API/Auth 401；若回復不完整則明報 **ROLLBACK FAIL**。此技術恢復不自稱舊版 Google 登入也曾 PASS。
5. 成功後仍 readback 固定網址 SHA、Hosting version 的兩條 exact pinned routes、正式 Hosting version 和 Cloud Run 正式流量不變。**本 canary 只封板 true Google code exchange + owner session；桌面/手機 UI、其他 provider、資料庫實際 P0 aggregate 與正式發布 gate 仍獨立保留。**
6. **不可跳過的外部前提**：必須在既有 Google OAuth **Web Client** 合法追加 `https://life-assistant-v3-stage-tl15.web.app/auth/callback`（保留 production callback），並確認實際 Hosting/Cloud Run 代理 Origin/Header 選擇正確。Google Console 變更與真實使用者登入不可以 mock、不可由假的 workflow run ID 冒充；未完成則 staging 新版最多為 **NOT VERIFIED**，不得宣稱 P1 DONE。

程式證據：`backend/scripts/verify_staging_google_e2e.py`、`backend/tests/test_staging_oauth_e2e_gate.py`、`backend/app/api/auth.py` 與 `.github/workflows/v3-staging-live.yml`；`apply=false` 依然只做 preflight，不改 staging live。**目前僅實作與 CI 階段，尚未執行這個 live canary，實際 Google Client redirect URI 設定也 NOT VERIFIED。**

## 2026-10-09 staging live 現場 readback／OAuth 隔離修正（本輪最新）

- GitHub Actions 唯讀現場盤點 [37944737101](https://github.com/tommylin15/life_assistant/actions/runs/37944737101) **PASS**：staging site **live** 已存在，Hosting version `sites/life-assistant-v3-stage-tl15/versions/e3a6dd23aec06848`；固定 URL `/release.txt` 讀出 `eb9f60c3413a8e5216318888a6456a1c464d8cab`；Hosting REST `/api/**`、`/auth/**` 各有單一 pinned tag `v3-eb9f60c341` 並精確對應 Cloud Run revision `life-assistant-api-00197-fug`。此版本只確定靜態 SHA、pins 及未登入存取控制，**尚不是「真實 Google OAuth 已驗證」的 fallback 認證**。
- 後續唯讀 OAuth probe [37945021056](https://github.com/tommylin15/life_assistant/actions/runs/37945021056) **PASS（盤點）**：目前 staging `/auth/login` 實際產生 **PRODUCTION_CALLBACK**，不是固定 staging callback；`/api/v1/free-events/status` 在 staging 和 production 目前皆是 **404**，所以最新 P0 owner-only API **尚未正式部署**，不能宣稱已取得 DB aggregate。
- 已補 `backend/app/api/auth.py` 固定 staging host／可辨識的 Cloud Run 代理來源白名單及 callback / frontend return URL；`backend/app/api/google_integrations.py` 和 `backend/app/services/google_oauth.py` 的增量授權／token exchange 也以同一 whitelist-derived callback 處理。正式站原本 callback 不變；Preview 的暫時網域不冒充固定 staging。安全回歸測試已加入 `backend/tests/test_auth.py`。
- staging 發布 workflow `.github/workflows/v3-staging-live.yml`：改為候選 0% tagged revision 檢查、真正的 Hosting REST pinned 後端 readback；必要時使用現有可回復版本 clone 並核對回復 SHA + API/Auth。CLI 已安裝，`apply` 預設關閉，**沒有觸發實際 staging live promotion**。目前仍以獨立成功的真實 Google login E2E 證據作為 `apply=true` 必要門檻（此證據尚無）；不得填造 run ID 或移除門檻。
- 新增 `.github/workflows/v3-p0-p1-joint-acceptance.yml` 手動唯讀聯合驗收：同版 SHA、Hosting pins、固定 staging OAuth redirect、P0 owner-only API 401、正式 Hosting 與 Cloud Run 交通不變。**其本身不能證明真實 Google 授權碼完成或 owner 已讀到 DB 統計數字**；兩者需另外真實帳號與應用驗收。
- **尚未封板：** 新後端需通過本次 exact-SHA V3 candidate / GHCR / Cloud Run、Firebase Preview 與 stage live 正式部署；Google Cloud Console OAuth 2.0 Client 必須**保留正式 redirect** 並確認追加 `https://life-assistant-v3-stage-tl15.web.app/auth/callback` 白名單，按實際使用確認 Firebase Auth domain（若使用）；再真實 Google login → callback → cookie session、desktop/mobile UI、roll back/production isolation 與 P0 owner-only PostgreSQL live readback。這些 **NOT VERIFIED**，不能只因 CI 綠燈或 workflow 已寫好就標 DONE。

## 2026-10-09 staging 工程續作紀錄（與原規則同步）

- 已在 GitHub `main` 新增 `.github/scripts/v3_staging_gate.py`、`tests/test_v3_staging_gate.py`，加入必要 `deployment-scripts` CI。其 readback 驗證 **本次完整 SHA、Preview／前版 staging live 的 Hosting version ID、`/api/**` 與 `/auth/**` 的 pin tag→Cloud Run revision 以及前版 SHA**，任一證據缺失即拒絕發布。
- 新增 `.github/workflows/v3-staging-live.yml` 作為 **manual only / 同 V3 release concurrency lock** 的 staging-only 前置驗證及受控同版 clone、post-readback、失敗回復路徑；預設 `apply=false`。它不能部署正式 Hosting，不能改正式 backend 流量，且以 Google 真實 staging OAuth E2E 之獨立成功執行紀錄為 `apply=true` 必要條件。沒有經核實的該紀錄，或 callback 仍回 production，fail closed；不能填個布林值就繞過。
- **未封板：** staging 真實 OAuth 前後端配置／登入 E2E 目前不存在；新 workflow 的 **live clone 與 rollback 尚無 GCP runtime PASS**，固定 staging 版本也尚未證實能使用。因此這是 implementation / CI 層新增安全閘，不是固定備選正式可用的證據。首版 staging 若沒有可核實的「上一已驗證版本」，需要另設安全 bootstrap 設計，不能刪掉基線保護偷渡首次發布。
- **相容性風險：** 短期 SHA Preview 的 hostname 每次不同，Google OAuth callback 無法直接假設和固定 staging live 互通；要讓真實 staging 授權成立，須分別設計並驗證固定 hostname callback、cookies、後端來源判定及實際 Google OAuth Client 白名單。**不能在未取得這些真實證據前執行 live promotion。**

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

> V2 Cloud Build 執行步驟已歸檔至 [archive/deployment_runbook_v2.md](archive/deployment_runbook_v2.md)；不要當作目前的部署指令。以上 staging 日誌是 2026-10-09 的時間快照，不代表最新 runtime 驗收。

---
