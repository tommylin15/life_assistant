## 2026-10-26｜Gmail V2 P0/P1：Production 已於 2026-10-23 正式發布，Staging 真人快掃已驗收

- **P1 正式上線已於 2026-10-23 發布完成（DONE，同 main SHA `2e2bbb50d7166fe49b9130594af3fe952dbf6334`）：**
  - **CI 四項 PASS**：[CI #39887105661](https://github.com/tommylin15/life_assistant/actions/runs/39887105661)，同 SHA。
  - **V3 100% 正式切流 PASS**：[Release #39888978522](https://github.com/tommylin15/life_assistant/actions/runs/39888978522)（`promote=true`、`enable_gmail_onnx=true`、`publish_staging=true`）：
    - 0% 候選驗證（`life-assistant-api-00439-dil`）、Alembic 0022 資料庫遷移。
    - 100% 切換正式流量，正式 API 啟動 ONNX 本地語意推論（`gmail-onnx` 映像標記）。
    - 上線後健康檢查 `live_ready=PASS`、`live_readback=PASS`。
    - Rollback 演練恢復正常 `rollback_drill=PASS`。
    - Revision 清理保持最新 10 個、定時 Job digest 對齊 PASS。
  - **正式 Hosting 發布 PASS**：[Deploy Firebase Hosting #39889756103](https://github.com/tommylin15/life_assistant/actions/runs/39889756103)，同 SHA `2e2bbb5`，ONNX 映像 digest 對齊，正式站 live readback PASS，Task/Project 自動 UI 驗收通過。
  - **正式站現況實測**：`https://gen-lang-client-0593591102.web.app/release.txt` 讀回 `2e2bbb50d7166fe49b9130594af3fe952dbf6334`，未授權 API 探測返回 HTTP 401。
- **P0 真實 Gmail Staging 驗收（使用者結案，2026-10-26）：**
  - 使用者於 2026-10-25 21:08 手機截圖確認：Owner 重新授權 Google 後，「立即快掃」正常執行，近三天 19 封「重新判讀」`失敗 0 封、未檢查 0 封`，掃描狀態更新為 2026/10/25 21:08。此前失敗屬 Google OAuth 憑證過期（409），重新授權後排除。
  - 使用者於 2026-10-26 明確確認目前操作與結果符合預期，P0 正式結案。
- **未被證明事項（NOT VERIFIED）：**
  - 正式 Production 環境真人 Gmail 登入與掃描操作（目前真人回報僅限於 Staging 站）。
  - 實際帳單抽取與促銷排除、7 天 40 封補檢、Gmail → Inbox 本地轉存寫入 PG、一般帳號跨帳號隔離、完整 FastAPI ONNX p95/RSS。

## 2026-10-20｜Gmail V2 完整 Life FastAPI ONNX Staging：PASS（產品 PARTIAL）

- **同 SHA CI／啟動：** [四 CI #39353419852](https://github.com/tommylin15/life_assistant/actions/runs/39353419852) PASS；[ONNX 指定 Staging 接續 #39353419856](https://github.com/tommylin15/life_assistant/actions/runs/39353419856) PASS，SHA faa8f5b80e8c5724d8b9759cc71d794d73e75082。
- **Cloud Run + Firebase 固定 Staging：** [V3 Release #39353638014](https://github.com/tommylin15/life_assistant/actions/runs/39353638014) PASS。2GiB／2vCPU／並行 1 ONNX 全功能 FastAPI candidate（0% Production）、Gmail 模型 ready 狀態 local_semantic_ready、正式 DB ready、Gmail 未授權 401、OAuth callback、PostgreSQL migration / 0022 Job、Preview 同 SHA、固定 Staging Hosting pin 及路由 PASS。Staging version sites/life-assistant-v3-stage-tl15/versions/938c9cfec8496d3c，https://life-assistant-v3-stage-tl15.web.app/。
- **明確未完成：** 真人 Owner／一般帳號 Gmail 掃描、漏判帳單、40 封七天補檢、收件匣不外送 Gemini／跨帳號、完整 FastAPI RAM/p95/冷啟動及真實錯誤率、rollback rehearsal、正式 production 同 SHA 切流/Hosting 和手動讀回：**NOT VERIFIED**。本次 promote=false；正式使用者流量未切換。實際固定 Staging 已具備 ONNX，但不能因此將 Gmail V2 整體標 DONE。
- **治理：** 保留舊公開 Git 提交敏感測試文字歷史修復待核准，未執行 history rewrite。完整證據與下一步詳見 [Gmail V2](gmail_local_v2_delivery.md)、[TODO](todo.md)。

## 2026-10-20｜ONNX Cloud Run 2Gi／2vCPU 獨立候選：DONE（Gmail V2 整體仍 PARTIAL）

- **同 SHA CI PASS：** [#39349455453](https://github.com/tommylin15/life_assistant/actions/runs/39349455453)，候選 source SHA b3ea92b6e11865d82887d4aa6a16b00285a63553。
- **Cloud Run 私有候選與實測 PASS：** [#39349455587](https://github.com/tommylin15/life_assistant/actions/runs/39349455587)：life-assistant-gmail-onnx-candidate 修訂 life-assistant-gmail-onnx-candidate-00002-l9b，2GiB／2vCPU、並行 1、實例 0–1、內部入口，digest sha256:f69b3f84cf10f829de8fe4e6522c388ebcd8f7b5e5944b9150e490b9e4543c31；獨立 Cloud Run Job life-assistant-gmail-onnx-smoke-57qqm 真實執行合成 ONNX 模型 PASS。正式 life-assistant-api 的非零流量 revision+百分比前後一致；**候選自己有 100% 私有流量，並非 Life 正式流量**。
- **安全／IAM PASS：** gcloud deploy 曾輸出 IAM-policy 設定失敗警告，但 [只讀 IAM/Ingress/未授權探測 #39350332042](https://github.com/tommylin15/life_assistant/actions/runs/39350332042) 全 PASS：internal ingress、Invoker IAM check enabled，未發現 allUsers／allAuthenticatedUsers Invoker 綁定，外部未授權 HTTP 非 200；不更動 IAM，無 Gmail、DB、OAuth、外部模型內容處理。
- **實測範圍限制：** 這是合成輸入、專用無私人郵件的 ONNX Cloud Run 候選服務；**沒有**將模型啟用到 Life 的登入版 Staging FastAPI，也沒有真實使用者 Gmail E2E／人為安全回退／正式 Hosting 切流。GitHub runner 1Gi 無網路容器測得程序 RSS 約 710MiB，但 Cloud Run Job p95 和 RSS 尚無精確指標讀回。對外不得宣稱 Gmail V2 產品 DONE。
- **待辦順序：** P0 將 ONNX 以 0%-production-traffic 真正接入 Life Staging（完整 API/OAuth/DB + 對照原規則）、P0 Owner 與一般帳號 Gmail 真信及 Inbox 本地轉存讀回、P1 正式同 SHA production/Hosting 安全發布、回滾與真人驗收。詳見 [唯一 Gmail V2 規格](gmail_local_v2_delivery.md)／[TODO](todo.md)。
- **歷史風險：** 公開 repo 的歷史提交疑含曾用於測試的實際帳單內容；程式最新工作樹已替換虛構樣本，歷史改寫需本人明確確認。

## 2026-10-20｜Gmail V2 CI + PostgreSQL 0022 + 固定 Staging 讀回

- **工程 CI：PASS。** [#39278270473](https://github.com/tommylin15/life_assistant/actions/runs/39278270473)，Flutter／Backend／PostgreSQL／Deployment Scripts 四項 PASS，同 SHA `3ad6b7768642fb8580027aa5460c5d2b4430d62f`。
- **自動接力：PASS（重試）。** [#39282095085](https://github.com/tommylin15/life_assistant/actions/runs/39282095085) 第 2 次執行成功觸發同 SHA staging-only。前次失敗屬接力 gate／GitHub API，未代表程式 CI FAIL。
- **固定 Staging：PASS。** [Release #39343836610](https://github.com/tommylin15/life_assistant/actions/runs/39343836610)：0% digest-pinned candidate、migration Job、獨立 Gmail V2 PostgreSQL schema readback Job、Hosting SHA、Pinned Preview、Staging live/API 401、OAuth redirect 均成功。固定 Hosting version `sites/life-assistant-v3-stage-tl15/versions/433b1bc1b2014576`，`traffic_unchanged=true`；正式 promote 與 rollback steps 未執行。
- **仍 PARTIAL：** FastEmbed ONNX 已通過離線合成樣本＋1 GiB 無網路容器工程驗收，但正式 API/Staging 尚未載入 optional ONNX 映像；使用者本人 Gmail 真信分類、一般帳號隔離、效能與模型誤判 E2E、正式版切流與 rollback：NOT VERIFIED。不能宣稱 Gmail V2 完整 DONE。規格：[Gmail V2](gmail_local_v2_delivery.md)。
- **隱私治理：** 本輪最新測試已改合成帳單，但公開 Git 歷史過去提交可能保留原始銀行帳單信息；未經使用者核准不可改寫 `main` 歷史。

## 2026-10-19｜Gmail V2 local-only scan / seven-day backfill

- User decision: no Gemini/omniAgent or other external generative AI on Gmail scanner. Rules + offline-only optional multilingual semantic model + local due-date extraction; manual only. Source: [V2 specification](gmail_local_v2_delivery.md).
- **Source/CI PASS:** SHA c4560ce77d3faaefbe31896849181f60ed6da27c, [four CI gates #39271061902](https://github.com/tommylin15/life_assistant/actions/runs/39271061902). Non-destructive Alembic 20261019_0022, versioned recheck, seven-day 2,000-ID bounded list/40-ID batch, user UI due evidence/coverage, no message body persisted.
- **Staging PASS:** [V3 staging-only Release #39271510026](https://github.com/tommylin15/life_assistant/actions/runs/39271510026) success, migration step success, staging Hosting static SHA and API 401 readback PASS, OAuth redirect PASS, fixed Staging version sites/life-assistant-v3-stage-tl15/versions/d97953b44182cde6; traffic_unchanged=true. **Production promotion, production Hosting and rollback steps were skipped**, NOT VERIFIED.
- **Not yet complete:** offline semantic checkpoint/dependencies not shipped (rules-only production Docker), Traditional-Chinese semantic quality/perf/RAM, actual Gmail human readback and per-user database receipts, cross-account E2E, direct database 0022 revision readback. Mark overall **PARTIAL**.
- **Evidence correction:** V3 workflow migration step/summary still labels 0018; release runner code targets 0022. Do not interpret the outdated summary wording as actual DB revision proof.

## 2026-10-18｜15:54 後最新接續驗收：BeClass 三筆新活動 → Life PostgreSQL

- **探索端有據的部分成功：** 正式 [10/18 唯一探索 Log](https://drive.google.com/file/d/1dOdbXe9zN-c5sT32RPA3bMk7ijNRk07-/view) 與執行紀錄記 `tw-discovery-manual-20261018-1507-rule-fallback`：A7 已實查 7，B 檢查 11 個 distinct 官方/主辦來源、可用 9；官方雙快照讀回 PASS（文化部 84 UID／觀光署 1,159 EventID），原池 78→81 個互異 `event_key`，新入池 BeClass 三筆皆 `pending_review`，四衍生視圖及交接新增寫後讀回 PASS。來源月曆新鮮度、主辦額外核證及本輪跨日全 ID delta 仍 PARTIAL／NOT VERIFIED，不以此宣稱完整探索 DONE。
- **Life Sheet 新真實狀態：PASS。** 10/18 15:54:43 +08:00 Google Sheets 交接表已有 **65 ACKED、0 READY、0 ERROR、65 個互異鍵**。三筆新 BeClass 的 `life_import_result=CREATED`；四筆 BeClass 的驗證狀態仍 `pending_review`，無證據的歷史狀態仍為 `unknown`。原 Wild Wild 最新同鍵業務版仍為 UPDATED/ACKED；不需要為測試再次觸發 importer。
- **PostgreSQL 獨立只讀版本核對：PASS。** [Life Importer Evidence #39110194986](https://github.com/tommylin15/life_assistant/actions/runs/39110194986) 執行 `python -c` 覆寫既有 Job execution 參數、`SET TRANSACTION READ ONLY`，直接讀 Sheet ACK 列並查 PG `curated_activities` 的 `handoff_event_key`／`content_hash`／`handoff_details.verification_status`；逐鍵版本一致且 `pending_review` 至少四筆的 assert 完整通過。Workflow 的 Job digest/live 100% image preflight 也成功。**這不是執行 `scripts.import_curated_from_sheet`，不變更 Job 定義或正式流量。** 對應 [CI #39110194915](https://github.com/tommylin15/life_assistant/actions/runs/39110194915) 已 PASS。
- **仍須分開驗收：** 新版 Flutter 一般登入者看得到活動、核證狀態篩選、來源與報名雙連結；同 SHA 新 UI 部署／Hosting 讀回；明日 GAS 約 07:30 自然觸發的 Trigger ID／Execution／PG 回執；A/B 資料品質改善與跨日差異。這些為 **NOT VERIFIED**，不得用匯入器 PG PASS 代替。
- **治理：** 活動探索正式 README/01～05 和當日 run_id／唯一 Log 仍由 Drive `life_assistantGPT` 管理；本文件只記 Life 端結案證據。GitHub 另有活動前台並行提交，需由其同 SHA CI／staging 後再走核准正式發布；不覆蓋正在修改的 UI。

## 2026-10-18｜台灣活動探索 Life 匯入器收尾（當日最後讀回）
- **正式技術 Job：PASS。** [#39100289293](https://github.com/tommylin15/life_assistant/actions/runs/39100289293) 為第一輪真實 importer 成功；修正上游不合規的 SHA256 後，[#39101120210](https://github.com/tommylin15/life_assistant/actions/runs/39101120210) 在 CI 四 gate、live revision `life-assistant-api-00365-haf`、Job digest/contract preflight 均 PASS 後，真實執行一次，`Completed=True, failed_tasks=0`。另一條舊 exact-SHA [#39101120348](https://github.com/tommylin15/life_assistant/actions/runs/39101120348) 只因祖先 SHA 不吻合而在 preflight FAIL，**沒有**執行 Job，不能當作 production importer 新故障。
- **2026-10-18 14:00 後人工讀回固定 `交接資料` Sheet：PASS（Sheet 層）。** 實際表頭 31 欄，62 個不同 `event_key`、64 字元小寫 SHA256 hash 全部有值、62 ACKED／0 READY／0 ERROR；其中 `beclass:305283a6ab273a8df4a8:20261019:wangchuan` 保留 `verification_status=pending_review`，13:23:02 +08:00 得到 ACK。原 `Wild Wild` 為同鍵 UPDATED/ACKED，沒有殘留重複列。61 個歷史 AE 空白是 **unknown**，不是 verified。探索精選原表 78 個不同 event_key（不是宣稱新發現 78 筆）。
- **尚不能結案整條使用者流程。** 目前這輪未單獨取得 PostgreSQL 中 BeClass 同鍵、新 hash、`handoff_details.verification_status` 的具體 readback，也未由正式 Flutter 一般登入者確認「可報名資訊待核」篩選/標籤、資訊來源連結和報名連結；A7+B10 自然/手動最新 01→05 同輪完整來源讀取、四視圖逐筆對帳、GAS 07:30 trigger ID 仍 **NOT VERIFIED**。來源有界備援遵守 Drive 正式 01～05；不得讓 Life importer 重新實作探索，亦不得將 ACKED 自動解讀成核實。
- **一次性 workflow 治理：** 當日用過的特殊 `life-curated-{promotion,import,hash-retry}-once-20261018.yml` 在成功/失敗證據留存 GitHub Actions 後從 main 移除，避免未來所有 CI 繼續生成過期 exact-SHA check、錯誤紅燈或再次匯入；日常 `curated-handoff-daily.yml` 手動備援與正常 V3 release gate 保留。

# Life — Current state

## 2026-10-17｜Gmail／Drive／Life Inbox／Session／月曆合併交付：全功能一次驗收
- 使用者要求上述已核准能力合併開發完成後執行**單次整合驗收**，不逐項要求人工確認。驗收 gate 與範圍集中在 [todo.md](todo.md) 首節，保持唯一 active backlog。
- `main` 已有可撤銷 30 天 PostgreSQL Session（`life_login_sessions`）、Gmail 重新判讀與 OAuth callback 修正、Drive Picker、日期萬年曆及月曆；歷史 TODO 的「Session 尚未實作」不再適用。本次新增：Life Inbox 對確定 FAILED 允許修正後重送，對 UNKNOWN 仍阻止盲目重送，補 Flutter 回歸測試；Gmail 重新判讀期間不誤顯快掃 spinner。
- 先前 [CI #39025948853](https://github.com/tommylin15/life_assistant/actions/runs/39025948853) 及 [Staging #39026104477](https://github.com/tommylin15/life_assistant/actions/runs/39026104477) 成功，SHA `9fda2f7`，但這是**本批整合 commit 之前**的證據；不能繼承為更新後同 SHA PASS。該 V3 有 `promote=false`，正式流量切換、live/rollback 與正式 Hosting 未執行。
- 新整合版的 CI、Staging、真實 Gmail/Drive/Calendar E2E、正式部署及實際讀回仍須依新 SHA 各別核實：**PARTIAL**；不可先行宣稱 DONE。

## 2026-10-16｜正式 Hosting 自動派送修復：source submitted; runtime gate open
- 原先正式 V3 由 GITHUB_TOKEN 發起 workflow_dispatch，後續 workflow_run 不會建立，因此自動 Hosting 沒有 Run。修正為 V3 同一 workflow 的最終步驟直接使用 workflow_dispatch。
- 僅在 promotion、fixed staging、postdeploy live、rollback drill、revision retention 與 curated importer 對齊皆 PASS 時允許派送。實際派送前重新核對 main SHA、四項 CI、100% live revision 和 immutable GHCR digest；同 SHA 已存在 Hosting Run 時跳過。
- 舊 production Hosting workflow_run dispatcher 移除。Firebase Hosting 原有 SHA／digest／401／OAuth 讀回及失敗回復前一版本均保留。新來源 CI、Staging 尚待同 SHA 驗收；正式自動派送的 runtime 成功仍 NOT VERIFIED。
- 上版正式來源 7e6f6cd 已有 V3 #38892900365 及手動 Hosting #38898216624 成功，不重新切流。


## 2026-10-16｜CI/CD 效能重構修復暨新版 Staging 真人驗收：PASS
- **程式／流程證據**：已發布應用 SHA `2cfe1c9f1e4946bc2849a863f9891419f0db1c45`；經 `9d9fa33` 保留快取、共用 Action／Reusable Workflow 並恢復必要驗收，`eadc310` 修復精選池 Job live digest 與契約讀回，`2cfe1c9` 補共用 Workflow 觸發邊界測試，未刪減原本的安全驗收矩陣。[同 SHA CI #38886583192](https://github.com/tommylin15/life_assistant/actions/runs/38886583192) 四項成功。
- **固定 Staging 與 runtime 自動證據：PASS**：[V3 Release #38886894486](https://github.com/tommylin15/life_assistant/actions/runs/38886894486) completed/success；`staging_live_readback=PASS`（Hosting SHA／pins/API 401）、`staging_live_ready=PASS`、`staging_google_redirect=PASS`；固定 Staging version `sites/life-assistant-v3-stage-tl15/versions/a1c3bd3ce0d7c6fc`，`staging_live=PASS sha=2cfe1c9... traffic_unchanged=true`。入口：https://life-assistant-v3-stage-tl15.web.app。
- **真人操作：PASS（使用者回報）**：使用者明確回報「新版測試網址通過人工驗收」，驗收歸屬於上述最新成功發布的 Staging 版本。這是使用者實際操作的驗收證據，非 GitHub Runner 自動執行真人登入；GitHub release 原始記錄的 `owner_login_e2e=NOT_VERIFIED` 仍表示自動化沒有這段操作證據，不與使用者回報矛盾。
- **本輪 CI/CD 修復／Staging 發布／使用者確認操作：DONE（各自 PASS）**。尚無逐項清單可證明 Life Inbox 的 Shopping／Calendar 寫入、重送、每種一般帳號權限流程全部 PASS；不可將「Staging 整體人工驗收」延伸為逐個業務 API 或 Production 正式版全功能驗收。此前使用者另已回報 Life Inbox Gemini 文章摘要成功，該特定能力可保留「真人回報 PASS」；尚未提供逐次模型呼叫日誌。
- **Production 未切換**：本次為 staging-only，正式環境流量保持原狀；是否發行正式版屬下一個獨立發布及驗收 gate。此段為最新版本證據，覆蓋下方較早的 10/16 Staging 舊版快照，不抹除歷史。


## 2026-10-16｜生活收件匣 Gemini 啟用修復：最新 Staging #38877006034 PASS
- **實作與同 SHA CI：PASS** — code SHA `2aa917663c037c57887defb6fa6c1d4c0ab82344`，Life Inbox 專用 Gemini `gemini_life_inbox_enabled=True`，經內部 `purpose=life_inbox` 呼叫 Gateway，保留通用 `/ai/text` 的獨立既有開關；網址摘要新增 Google share.google／公開 URL 安全轉址、失敗原因分類與中文提示、SSRF 保護，無任何用戶資料自動寫入。對應 [CI #38876663435](https://github.com/tommylin15/life_assistant/actions/runs/38876663435)：backend / flutter / free-events-postgres / deployment-scripts 四項 success。
- **最新固定 Staging：PASS／該發布範圍 DONE** — [Release #38877006034](https://github.com/tommylin15/life_assistant/actions/runs/38877006034) `completed/success`，相同 `2aa9176` SHA，`staging_live_readback=PASS layer=hosting_version_and_static_sha`、`staging_live_readback=PASS layer=pins_and_api_401`、`staging_live_ready=PASS attempt=1`、`staging_google_redirect=PASS fixed_staging_callback`、`staging_live=PASS sha=2aa9176... version=sites/life-assistant-v3-stage-tl15/versions/1b45d60d34fbed2b oauth_redirect=PASS owner_login_e2e=NOT_VERIFIED traffic_unchanged=true`。固定入口：https://life-assistant-v3-stage-tl15.web.app。
- **未被本次 release 證明的事項：NOT VERIFIED** — Owner 真實登入後測試多語意分類 Gemini 模型回覆、實際 share.google 轉址與文章擷取／摘要、Gateway 原因碼、單筆與多筆持久化讀回／重送；Cloud Run runtime 是否有覆蓋 `GEMINI_LIFE_INBOX_ENABLED=false` 的顯式環境設定亦未做獨立 config readback。生產正式流量未切換，Admin `life_inbox` 開放 all 未啟動。整體產品仍 PARTIAL。
- **證據限制**：`staging_live=PASS` 代表 matching-SHA 部署、403/401 及固定版讀回，不應把它敘述成 Gemini 真實推論的 PASS。文件變更只記錄證據，不更改上述已發布應用 SHA。


## 2026-10-16｜生活收件匣 V1：同 SHA 四項 CI + Staging 完成（優先於下方歷史快照）
- **實作來源：PASS**：`03295a0b8067d3046da2877c70a7874b06976a78`，新增 `life_inbox` owner-only 預設 rollout、分類候選、用戶明確確認的寫入、收據、文章預覽、Flutter 入口及筆記摘要提示；單元與 Flutter widget 測試在 CI 執行。詳細設計見 [V1 SPEC](life_inbox_quick_capture_spec.md) 及 [AI 工程指示](life_inbox_ai_developer_instructions.md)。
- **CI：PASS**：[CI #38866256031](https://github.com/tommylin15/life_assistant/actions/runs/38866256031) 同 SHA backend、flutter、deployment-scripts、free-events-postgres 四項成功。
- **Staging：PASS／該版發布 DONE**：[V3 Release #38866539155](https://github.com/tommylin15/life_assistant/actions/runs/38866539155) 2026-10-16 已 `completed/success`，`staging_live=PASS sha=03295a0...`、`staging_live_readback=PASS`（Hosting 靜態 SHA／pins／401）、`staging_google_redirect=PASS`；候選 revision `life-assistant-api-00324-ruf`；固定站 https://life-assistant-v3-stage-tl15.web.app。
- **Production：NOT DEPLOYED FOR THIS SHA**：run inputs `promote=false`，`traffic_unchanged=true`；本輪並未將 Life Inbox 部署至正式 100% 流量。Release 中 Revision 維護獨立 `stage=DONE,status=PASS`，12→10、刪兩版、`live_unchanged=true`、未刪 Service/Job。
- **功能 E2E 仍 PARTIAL**：該 workflow 明確 `owner_login_e2e=NOT_VERIFIED`；這次 staging infrastructure／auth redirect PASS 不等於已通過真正登入帳號使用新收件匣、Gemini 意圖拆解、URL 摘要、Shopping/Calendar 真實寫入與收據重送結果的所有測試。Admin `life_inbox` 預設 beta/owner，未確認設定 `enabled/all`，不得宣稱一般 user 已開放。下一步是同 SHA 的 owner／一般 user 權限與寫入讀回驗收，後續再受控正式部署。
- **歷史狀態註記**：本文件下方 2026-10-16 月曆／登入的「尚未實作」屬該日期早期快照，須按該功能各自的後續 Actions/evidence 補正，不能拿來否定上述 Life Inbox 本版的實際 Staging PASS。


## 2026-10-16｜新 UI 改版來源提交，驗收待補（不改既有 01–03 正式結案）
- **日曆／月曆 source 已提交 main**：`lib/web/calendar_page.dart` 改為七欄整月日期格、今日與點選標記、由既有事件文字分類的小圖示（會議／生日／帳單／旅行／交通／活動／提醒）與首筆短標題，底下只呈現選定日期的精簡行程；點入詳情才看描述、可信活動網址、編輯／刪除。保留原有 Google Calendar API 與 OAuth。
- **活動統一 source 已提交 main**：`curated_events_page.dart` 以「全部活動／限時機會／已收藏」三模式查詢既有同一 PostgreSQL 活動池；`navigation_catalog.dart`／`personalize_page.dart`／`today_page.dart` 合併導覽與首頁偏好，保留 legacy 活動鍵與舊網址 API，新增 `test/web_activity_unification_test.dart` 檢查主活動分組及偏好映射。最後 UI 變動 commit [`dac1e17`](https://github.com/tommylin15/life_assistant/commit/dac1e17c085ba0e021b7cc9e6ab1090bf3004735)。
- **新 UI 驗收狀態：PARTIAL**。源碼已 GitHub commit；新 SHA 的 Flutter analyze／widget tests／四項 GitHub CI／固定 Staging／正式 Hosting／真人 Google Calendar E2E 均 **NOT VERIFIED**，不能繼承 2026-10-15 已驗收的舊 UI 結果。尚未執行本次變更的 production promotion。
- **記住登入：設計待實作（NOT VERIFIED）**。目前 `backend/app/api/auth.py` 的 `__session` 直接持有最長約 3600 秒有效的 Google ID Token；不能只延長 Cookie。須用 PostgreSQL 存可撤銷的 Life opaque session hash、短效 OAuth 登入換長效的 30 日 HttpOnly／Secure／SameSite cookie、logout server-side revoke，保留 staging provenance 及各帳號資料隔離；schema migration／測試／CI／runtime 尚未做。
- 本新功能工作追蹤 `doc/todo.md` P1-5／P1-6。先前 01–03 的成功技術鏈及使用者正式驗收仍成立，但**不延伸為新版日曆／合併介面的驗收**。

## 2026-10-16｜01 GAS／Life 匯入技術驗收 PASS／DONE（本批 01～03 完整結案）
- **01 正式匯入流程：PASS／DONE（實際資料鏈）**。正式 [V3 #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151) 已更新 `life-assistant-free-events` 至正式 promoted immutable GHCR digest，`job_digest_and_contract=PASS`；2026-10-16 上午 **07:34:20 台北時間** [Execution `life-assistant-free-events-ds4bq`](https://console.cloud.google.com/run/jobs/executions/details/us-central1/life-assistant-free-events-ds4bq?project=gen-lang-client-0593591102) Completed=True。當天 07:00 後至稽核時僅見這一筆完成的 importer Execution（舊歷史累計 17）。
- **Sheet／PostgreSQL 真實版本一致：PASS**。固定交接 Sheet `交接資料` 讀得 **59 列：58 ACKED、1 ERROR**；2026-10-16 **07:34:15.797234+08:00** 有 **5 筆新 ACKED／CREATED**。不重跑 importer，而透過 [唯讀驗收 #38825509671](https://github.com/tommylin15/life_assistant/actions/runs/38825509671) 執行既有 `life-assistant-core-acceptance` Job（Execution `life-assistant-core-acceptance-xr6sq`，成功退出），在 PostgreSQL 精確比對這 5 筆 `handoff_event_key`、`content_hash`、`handoff_updated_at_tpe`，並驗證 `created_at` 落在本次來源版本與 ACK 時間範圍；GitHub check `life_oct16_handoff_pg_readback=PASS exact_new_ack_versions=5`。
- **排程證據邊界**：Cloud Run 07:34 成功執行與同輪 Sheet／DB 讀回，足以結束產品的「每日交接匯入」功能驗收；**Apps Script 原始 Trigger ID／單次觸發 ledger 未直接讀到，維持 NOT VERIFIED（可觀測性補強，不反推為已證實的觸發來源）**。這是功能運作驗證，不是所有後續日期必定成功的保證。
- **來源品質與技術成功分離**：唯一 `ERROR=invalid_handoff_record` 仍為 `ntpclib:9af3c52d:20261024:parent-halloween`，屬探索端來源修補事項；來源品質 **PARTIAL**，但不構成本次 Cloud Run 技術驗收 FAIL，不重寫錯誤列或假填核證時刻。
- **本批完成判定**：01（定時匯入技術資料鏈）、02（購物／待辦）、03（活動／個人操作及 Calendar）皆 **PASS／DONE**。01 由真實 execution、5 筆 Sheet→PG 精確比對證明；02／03 為先前已確認的正式版使用者人工驗收。其它獨立產品待辦與剩餘風險照常保留。


## 2026-10-15｜02／03 正式版使用者人工驗收結案（最新）
- **02｜Shopping／Task：PASS，功能範圍 DONE（使用者正式版人工驗收）**。使用者在正式部署 [V3 #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151) 與 [Hosting #38738435372](https://github.com/tommylin15/life_assistant/actions/runs/38738435372) 成功後明確回報「02,03驗收完畢」，按本輪預先列明的驗收範圍結案：購物清單／品項獨立編輯及刪除、一次新增多品項、重新載入、待辦刪除不白畫面與相關權限操作。
- **03｜活動個人操作／Calendar：PASS，功能範圍 DONE（使用者正式版人工驗收）**。同一使用者驗收回報涵蓋此批預先列明的跨日活動搜尋／分頁、收藏及個人待辦／追蹤、Google Calendar 操作與讀回。這是**使用者回報的整批功能驗收**，不是 Actions 自動產生的每個 OAuth 寫入事件或逐條 API log；未提供各帳號／事件數與逐項追蹤紀錄，不捏造。
- **證據分層**：implementation/CI/PG rollback-only/production deployment 為 GitHub workflow PASS；正式 UI 操作為**使用者回報 PASS**。兩項功能不應在待辦重列為「尚無正式人工驗收」。未來相關程式變動仍應依受影響範圍回歸測試，不把這次人工驗收推論為任何未跑過的壓力／併發／全部帳號路由自動驗收。
- **01（2026-10-15 當時尚未結案）**：後續 2026-10-16 已取得正常 Execution + Sheet ACK + PostgreSQL 精確版本讀回，**技術資料鏈 PASS／DONE**；來源單筆 ERROR 的品質改善仍屬獨立事項。


## 2026-10-15｜01–03 正式 Release / Hosting 驗收（發布時快照；02／03 狀態由上方人工驗收更新）
- **Production CI/CD 發布：PASS**，source SHA `6fdb4cf7e12f6c76d0b6955bc3f6e9325a5cbcce`。[四項 CI #38730407125](https://github.com/tommylin15/life_assistant/actions/runs/38730407125)、[正式 V3 #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151)、[正式 Firebase Hosting #38738435372](https://github.com/tommylin15/life_assistant/actions/runs/38738435372) 全部 success；保留固定 staging、登入 redirect/401、核心/購物/活動 PostgreSQL rollback-only、Drive AI/Google 自動化、正式 health/ready、回滾演練與恢復。Hosting `release_check=PASS` 確認 production 靜態版 SHA 與 promoted backend 相同；Task/Project 自動 UI 驗收 PASS（非所有私人帳號的真人 E2E）。
- **01 正式匯入器新版映像：PASS**：V3 的 `Pin curated handoff Job after verified production promotion` success，Job `life-assistant-free-events` 更新，`{"check":"job_digest_and_contract","status":"PASS"}` 讀回；包含本輪已 CI PASS 的 `pg_try_advisory_xact_lock` 版本。未手動執行 GAS/importer。**下一輪定時 GAS 07:30 的來源 ledger、該新映像 Job Execution、PG 與 Sheet 同輪版本 ACK 尚 NOT VERIFIED**，不能以發版即當作執行成功。
- **正式 Revision 維護 PASS**：當輪讀回 13→10，刪 3 個舊 Revision，`jobs_deleted=0`，`services_deleted=0`，`live_unchanged=true`。
- **來源 Google Sheet 再次唯讀**：54 rows，53 ACKED／1 ERROR（`invalid_handoff_record`），最後可見 ACK 為 2026-10-14 13:41 台北時間；來源錯誤未修復，且原 ACK 不等於最新發版後同輪版本確認。
- **02/03（發布當時狀態，已由上方 2026-10-15 最新人工驗收取代）**：Shopping/Tasks、跨日活動／分頁／收藏／Calendar 自動 CI、Staging 與 PostgreSQL smoke 均 PASS；發布時真人驗收尚未回報，後續使用者已明確確認 02／03 驗收完畢。


## 2026-10-15｜01–03 新驗收 Release 修復完成（取代以下 #38715747623 FAIL 事件）
- **正式 importer 唯讀配置驗收：PASS（限對齊既有 production）** — [Cloud Run Audit #38725678405](https://github.com/tommylin15/life_assistant/actions/runs/38725678405) 經 WIF 讀取既有 production 100% API Revision 與 `life-assistant-free-events` Job：`importer_image_alignment=PASS contract=PASS`，且固定 Sheet ID、`python -m scripts.import_curated_from_sheet` 及 `LIFE_CURATED_IMPORT_APPLY=1` 契約吻合。舊 16 筆 execution 最新 `life-assistant-free-events-krcmj` 於 2026-10-15 07:34 台北時間 Completed=True；Cloud Logging 聚合日誌依權限無法讀取（`summaries=0` 不是 0 次匯入）。**這僅驗證既有正式版 digest，沒有讓目前 staging-only 的 importer 排他鎖新版進入正式 Job。GAS 實際觸發來源及同輪 Sheet/PG receipt 仍 NOT VERIFIED。**
- **最新可驗證的 staging-only Release：PASS** — [V3 #38720078074](https://github.com/tommylin15/life_assistant/actions/runs/38720078074)，SHA `8d2720758d3d2bacf92f023ea64b96ef58646595`。相同 SHA 的 [四項 CI #38719801492](https://github.com/tommylin15/life_assistant/actions/runs/38719801492) Backend／Flutter／deployment-scripts／free-events-postgres 全 PASS。
- **原阻塞已實際回歸：PASS** — V3 `Read existing handoff DB versions and rollback-only Shopping CRUD` job step `success`、Cloud Run `life-assistant-core-acceptance` execution exit=0；rollback-only curated/ownership、additive migration 0018 及固定 staging 均 successful。新版 `staging_live=PASS`、`oauth_redirect=PASS`、`traffic_unchanged=true`，未將新 candidate 切至 production。
- **事件診斷** — 前次 [#38715747623](https://github.com/tommylin15/life_assistant/actions/runs/38715747623) 在新加的購物/活動驗收 Job Exit 1。修正 shopping fixture parent-first `flush` 後，同一真實 gate PASS，符合 ORM FK 插入順序的根因判斷；原部署帳號不能讀 Cloud Logging，所以不聲稱曾取得原失敗 Execution 的 Python traceback。
- **範圍界線** — PostgreSQL handoff 欄位一致性與 rollback-only Shopping 實測已 PASS；**不等於** GAS 07:30 trigger source、同輪 Sheet/PG 逐筆版本 ACK、正式 importer 最新映像、Calendar OAuth 真實寫入，以及使用者登入後的購物/活動前端完整 E2E 均 PASS。後者仍是活躍 TODO 的 PARTIAL／NOT VERIFIED。文件專用後續 commit 不繼承新的 production 流量證據。


## 2026-10-15｜V3 #38715747623 失敗診斷與修正中
- [V3 #38715747623](https://github.com/tommylin15/life_assistant/actions/runs/38715747623) SHA `296e50f` **FAIL**，失敗只在新加入的 `Read existing handoff DB versions and rollback-only Shopping CRUD`；Execution `life-assistant-core-acceptance-kdl4r` exit=1，先前既有 curated/ownership tests 正常。
- WIF deployer 讀 Cloud Logging 回傳 `PERMISSION_DENIED`，沒有 Python traceback；不能判定實際 PostgreSQL 資料損壞。
- 新驗收程式的 ORM 操作順序存在可重現的外鍵問題：`ShoppingList`／`ShoppingItem` 沒有 mapper relationship，同一輪 flush 可能先 insert 子品項；已修改為先 flush parent，再 flush items，新增順序測試。下輪以四項 CI 和 Release 真實執行讀回判定修復，**不能先記 DONE**。
- 新增有限的 Cloud Run task exit code 分類（41 交接 DB 存取、42 交接一致性、43 購物交易、44 rollback 讀回），後續日誌權限不足時仍可定位錯誤階段，不需調整 GCP IAM。

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
1. **GAS → importer → PostgreSQL → Sheet:** 2026-10-16 同輪實測已 **PASS／DONE**（見最上方）。只有 Apps Script Trigger ID／觸發 ledger 未取得（NOT VERIFIED；可觀測性補強），及 1 筆來源品質 ERROR（非技術故障）仍需分別處理；舊 52 ACKED/2 ERROR 僅為歷史快照。
2. **Gemini UX:** signed text path is proven, but individual logged-in user API/frontend handling, timeout/failure UX and quotas are not proved by synthetic smoke.
3. **Activity UX:** 02／03 的正式版功能人工驗收已由使用者回報 PASS；未另取得逐事件 Calendar API 紀錄、全帳號組合或壓力／併發極端情境獨立儀表化證據，這些不當作此次產品人工驗收的未完成項。
4. **Drive AI provider governance:** source has admin controls/health counts, but token/cost-based budgets, per-user consent E2E and multi-provider runtime cost proof are **NOT VERIFIED**.
5. **Shopping/list edit/delete/batch and Task delete white-screen:** 正式部署後，使用者再次回報 02 人工驗收完畢；該功能範圍 PASS／DONE。已完成的 widget/CI、PG 及正式 UI 佐證各自歸類，不聲稱已跑過全部帳號／API 自動回歸矩陣。

## Rules
- `PASS / FAIL / NOT VERIFIED` apply **per** implementation, tests, CI, deployment, runtime, integration; aggregate DONE only with required evidence. Otherwise PARTIAL.
- The user's decision removed **manual Owner Google OAuth E2E as a blocking release step**, not automated OAuth/session/redirect/401 checks. 只有未執行的真人 OAuth E2E 才記 NOT VERIFIED；2026-10-15 已由使用者明確回報正式版真人驗收 PASS。
- This snapshot is superseded by later matching-SHA actions or GCP runtime evidence, not by documentation alone. Prior detailed history remains in Git history and [the archived pre-cleanup snapshot](archive/CURRENT_STATE_through_2026-10-14.md).


## 2026-10-17｜Gmail 分類修復版的 Firebase Preview 404 連續失敗（保留失敗證據）

- SHA `b4894f056a79199b5d39e9b11639727a282fad4b`：CI [#39034846342](https://github.com/tommylin15/life_assistant/actions/runs/39034846342) 四項 PASS；V3 [#39035036060](https://github.com/tommylin15/life_assistant/actions/runs/39035036060) 第一次及第二次均 **FAIL** 在 `Verify pinned Preview API and static release`。Firebase Hosting API channel/version 顯示 PUBLISHED，但 `web.app` 與 `firebaseapp.com` 公開 Preview `release.txt` 均持續 HTTP 404、24 次有界驗證後失敗；不能把 API PUBLISHED 視作網站可用。
- 候選 0%／DB/auth 完成，不代表固定 staging 更新；先前固定 Staging `2e91c017` 仍為最後已證實版本，production 沒有變動。
- 對策：每個 Release `GITHUB_RUN_ID` + `GITHUB_RUN_ATTEMPT` 使用隔離且可追溯的 Preview channel，避免同 SHA 重跑一直復用一個失效的公開 Host；所有網址、版本、SHA 與被動 API 401 gate 都維持 fail-closed。這是針對持續 404 的受控修復假設，尚非 root cause 已證實，也不能先標 PASS。


## 2026-10-18｜Preview isolated-channel hostname truncation 實際失敗

- [V3 #39040660665](https://github.com/tommylin15/life_assistant/actions/runs/39040660665) 同 SHA `802e106` 四 CI **PASS**；Preview channel `v3-802e10649f-r39040660665a1` 已由官方 metadata 宣稱 PUBLISHED，但 Firebase 公開 URL 實際只包含截短的 `v3-802e10649f-r390406606`，`scripts/v3_verify_preview.py` 的精確 channel gate 因此 **FAIL**，尚未執行網站 SHA/API 讀回。
- 根因已由 Actions 的 `PREVIEW_CHANNEL` 和 `PREVIEW_URL` 直接對照確認：Preview channel 不能超過 Firebase 公開 hostname 可完整表示的長度。改用 GitHub run ID **完整 base36**（此輪 7 字元）加 attempt，並在 CLI/API 驗證及固定 Staging promotion 前限制 channel ≤ 24 字元；跨版 SHA、候選 revision pin、OAuth/API 401、正式流量不變等門檻保留。新 SHA 的 CI／Staging／實機驗收不可沿用失敗版的證據。


### 2026-10-18｜YAML 格式回歸與修復

- [CI #39048784160](https://github.com/tommylin15/life_assistant/actions/runs/39048784160) 與 [workflow 載入失敗 #39048783013](https://github.com/tommylin15/life_assistant/actions/runs/39048783013) 暴露：Preview channel Base36 計算的內嵌 Python heredoc 沒有保持 YAML `run: |` 縮排，導致 GitHub Actions workflow 直接無法解析（0 jobs）；程式碼 CI 不能取代 workflow YAML 格式檢查。
- 修正 heredoc YAML 縮排，並在 deployment-scripts CI 新增 PyYAML 的 **所有 .github/workflows/*.yml** 結構載入驗證；正式 staging/production 仍以新的同 SHA workflow/runtime readback 判定，不沿用之前的綠燈。
