# CI/CD V3 切換、舊資產清理與 runtime 驗收進度

最後更新：2026-10-09（Asia/Taipei）
狀態：**CI/CD 切換 PASS；已指定的舊 CI/CD GCS／AR 清理 PASS；全部 GCP AR 清空不是目標，janus-postgres 保留。整體產品 Phase 1 仍 PARTIAL。**

> Source of Truth：GitHub `main` implementation + 實際 GitHub Actions/GCP 唯讀 readback；本文件不取代 production 證據。本頁取代 2026-10-08 仍寫著「尚未部署、資產尚未刪除」的前一版狀態。原有核准規則及歷史風險繼續保留於 Git history；若規格與現況不符，以 runtime 為準，不能反推文件自動部署或自動刪除。

## 1. 目前 verified state（2026-10-09）

| 項目 | 狀態 | 現場 readback / evidence |
| --- | --- | --- |
| GitHub Actions → public GHCR → Cloud Run | **PASS（已部署）** | Promoted release run [37795789924](https://github.com/tommylin15/life_assistant/actions/runs/37795789924)，release SHA `25ff10c61abc15e557996b6070e02abf3b54a97b`，GHCR `sha256:b06254c2db22489295c2a82928ea19a6352193fd7b0c72f1041040f22bc0d7b1` |
| 正式 API / 目前 readiness | **PASS** | service `life-assistant-api`；ready revision `life-assistant-api-00183-hax`；spec/status digest 指向 GHCR 公開映像之 Cloud Run cache；Ready/Active/ContainerHealthy/ContainerReady/ResourcesAvailable 均 `True` |
| 舊 Cloud Build Trigger 5/5 停用 | **PASS** | `life-assistant-v2-main`, `life-assistant-v2-release`, `janus-dev-v2`, `omniagent-main-v2`, `omniagent-release-v2`：GCP `disabled=true` |
| GCS 舊 Cloud Build / Run source Bucket 清理 | **PASS（資產已不存在）** | 8 → 5 buckets；`gen-lang-client-0593591102-cloudbuild-regional`, `gen-lang-client-0593591102_cloudbuild`, `run-sources-gen-lang-client-0593591102-us-central1` 不再列於 Buckets list；三個候選 Bucket 的逐一讀取為 `404` |
| 舊 AR Docker repository 清理 | **PASS（指定舊資產已不存在）** | 4 → 1 repository；`cloud-run-source-deploy`, `janusai-poc`, `omniagent` 已不存在；`janus-postgres` 仍存在 |
| GitHub 唯讀資源盤點／讀回 | **PASS** | [GCP readback run 37867249614](https://github.com/tommylin15/life_assistant/actions/runs/37867249614)，在初次重跑因假設 Bucket 存在而 FAIL 後，修復 404 為已移除的正常結束狀態，並重跑 PASS |
| 一般產品 Phase 1 最終封板 | **PARTIAL** | 仍以 `doc/progress.md`、`doc/acceptance.md` 的功能驗收為準；不因 CI/CD 資產清理而宣告所有功能 DONE |

本次 readback 對應 `main` 基線 `86a22e2c46945f9ad8bf537131bce95f26bee151`（後續文件-only commits 不等於重新部署）。最新盤點列出 GCP 5 個 Cloud Run Services、8 個 Jobs；沒有證據表示 465 個歷史 Revision 已全部刪除，不得由 AR 清理結果推定 Revision retention 完成。既有 `life-assistant-api` 每服務保留 10 個 Revision 的 release-policy/保護機制仍需依實際 deployment/retention evidence 個別判讀。

## 2. GCS：目前保留清單（5 buckets；不屬於已清理舊 CI/CD 候選）

- `gen-lang-client-0593591102-dev-core`
- `gen-lang-client-0593591102-dev-mart`
- `gen-lang-client-0593591102-dev-private`
- `gen-lang-client-0593591102-dev-research-big-move-500`
- `gen-lang-client-0593591102-dev-stage`

這 5 個 `dev-*` Buckets 未授權作為 CI/CD 殘留刪除對象。資料庫備份、使用者／應用／研究資料一律不在本次清理範圍；Bucket list 不足以證明其他 project/VM 持有的備份存在或不存在。

2026-10-08 原先對兩個 Cloud Build Buckets 盤點到 208 objects，其中 `source/` 77 objects 為候選、131 objects 尚未分類。**目前兩個 Bucket 已整體不存在，對 77/131 個物件的逐項刪除日志並未分別取得**；可核實的是最終 Bucket 不存在，而不是逐項 object deletion event。第三個 `run-sources-*` Bucket 原盤點為 0 objects，現亦不存在。

## 3. Artifact Registry：目前僅 1 Docker Repository / 1 Digest

- Repository：`janus-postgres`（`us-central1`）
- Docker Image：`us-central1-docker.pkg.dev/gen-lang-client-0593591102/janus-postgres/postgres:16.15`
- Digest：`sha256:a9a39ade56dc5f417839ff378ba9265edf84518f40fc74d3a1366b8aae1cafc1`
- GCP 目前該區 Cloud Run Services/Revisions/Jobs 引用：**未發現**；VM/GCE/GKE／其他現役容器依賴：**NOT VERIFIED**。
- Decision：**保留，不能因 Cloud Run 無引用或最新版規則就當成可刪**；需驗證 Janus PostgreSQL 容器的現役來源及資料庫啟動／重建依賴後再決策。

舊版盤點的 66 Docker Digests、58 刪除候選、約 13.67 GB 為**清理前的候選估算**，不是逐個 Digest 已實際刪除的事件證據，也不是成本帳單；2026-10-09 readback 只證實 **目前 1 Digest**，且 3 個指定舊 Repository 已不存在。

## 4. 新核准保留/清理政策（不為舊版回滾保留 AR Digest）

1. AR Docker Tag/Digest **只因現役部署／排程 Job／VM／GKE 等實際 consumer 依賴而保留**；「這是最新版本」及「歷史 Revision 可能回滾」本身不構成保留理由。
2. 已切至 GHCR 且其他現役 consumer 不再引用的 AR Docker 舊映像，可列候選；**不准碰到 PostgreSQL database、資料磁碟、備份、應用資料**。
3. GCS 的歷史 Cloud Build source/log/staging 可清理；只有確認為舊 CI/CD 資產且無依賴時才動。保留 5 個 `dev-*` Buckets。
4. 目前 5 個 Cloud Build Triggers 為 **disabled=true**，不是刪除 definitions；舊版 `cloudbuild.yaml` / workflow 仍在 GitHub Git history 中，不等於目前的 release pipeline 使用它們。
5. 過往兩個 Cloud Build Bucket 及 Run source Bucket 已不存在，**後續工作流程不得依賴這些 Bucket**；盤點腳本需將真實 404 判作 `DELETED/PASS`，其他 HTTP 錯誤仍是 `NOT VERIFIED`。

## 5. 最新執行/驗收證據（可稽核）

- V3 promoted release：[`37795789924`](https://github.com/tommylin15/life_assistant/actions/runs/37795789924)。
- 全 Trigger 停用及候選盤點：[`37860865591`](https://github.com/tommylin15/life_assistant/actions/runs/37860865591)。
- 清理前 AR 4 repositories、66 Digests 盤點：[`37861562813`](https://github.com/tommylin15/life_assistant/actions/runs/37861562813)。
- 不保留歷史回滾的 AR/GCS cleanup candidates readback：[`37863496131`](https://github.com/tommylin15/life_assistant/actions/runs/37863496131) **原 attempt PASS，後來針對已刪 Bucket 的人工重跑先 FAIL，僅為 inventory 404 判斷舊假設不符**。
- 刪後 readback：[`37867249614`](https://github.com/tommylin15/life_assistant/actions/runs/37867249614) **PASS**，AR=1 / GCS=5 / 三舊 buckets 均 deleted / Trigger=5 disabled / API ready。
- 改進盤點：`v3_gcs_object_inventory.py` 與 `v3_no_rollback_retirement_inventory.py` 在 GCS HTTP 404 時回報 `DELETED` 而非將已刪資產當作故障；未知或權限錯誤不可冒充 404。

## 6. 尚未完成的驗證、風險

| 工作 | 狀態 | 下一步 |
| --- | --- | --- |
| 已指定 GCS / AR 舊 CI/CD 資源最終不存在 | PASS | 保存 readback；不需重建資源 |
| `janus-postgres` 現役 VM/DB/container dependency | NOT VERIFIED | 釐清是否還需 pull/start；未確認前保留 |
| 5 個 `dev-*` GCS 的應用/備份資料治理 | NOT VERIFIED（非本次清理範圍） | 不動資料 |
| 實際 Cloud Run revision 個數 / 每服務最新 10 的後續 retention | NOT VERIFIED（本次未盤查逐一剩餘） | 獨立 run/readback 驗證；不將 AR 清理推論為 Revision 清理 |
| GHCR V3 下一次正式部署及 end-to-end user integration | NOT VERIFIED（本次未重新部署） | 遵循正式 release policy；此次文件更新不觸發新 release |
| Phase 1 全產品完成 | PARTIAL | 繼續 `phase1_delivery_order.md` 與 `acceptance.md` 的剩餘封板工作 |

### Completion boundary

**CI/CD 舊 GCS/AR 指定範圍清理 = DONE / PASS（依最終 readback）。**
**所有 AR Docker 資源清空 = NOT DONE（`janus-postgres` 1 Digest 保留）。**
**全產品 Phase 1 = PARTIAL。**
