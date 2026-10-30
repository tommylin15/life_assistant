# Life／Janus 共用台灣出口通道

狀態：**Proxy 已完成安全發布與 Live 正向驗收**；Janus API 新版、Life VM 新 client 的端到端任務仍須個別驗收。Live 收據：[Actions #41010462296](https://github.com/tommylin15/life_assistant/actions/runs/41010462296)。

## 已有資產

- 共用既有 `tw-activity-proxy`，GCP `gen-lang-client-0593591102`，`asia-east1`。
- Janus API 位於 `us-central1`；Life 在既有 VM 透過 `TWRequestRouter` 使用代理。
- 現有 Cloud Run IAM 唯讀讀回：無公開 `allUsers` Invoker；僅授權 Life VM 服務帳號。這不代表程式層的公開原始碼／舊靜態密鑰已安全。

## 必要安全修復

1. 不再使用公開 repository 內的靜態代理密鑰；服務呼叫只接受 Cloud Run 已驗證的服務身分 ID Token 與限縮 Invoker IAM，Life／Janus 兩個已知呼叫者獨立授權。
2. 禁止代理任意網址：僅允許明確列出的來源 host、HTTPS、GET、合法路徑和參數。禁止 localhost、IP literals、內網／metadata、跨站 redirect、任意方法與任意自訂 Authorization header。
3. 保持 TLS 憑證驗證，限制大小、逾時、來源請求頻率與錯誤資訊；不記錄私密 payload 或 token。
4. 原服務保留低實例上限，不新增付費資源。部署先做私有 candidate、失敗不切換；保留既有 revision 與可驗證 rollback。
5. Janus 的 MIS 只作盤中、按需、限量備援；合法報價必須核對來源、日期、實際成交時刻與欄位，不得倒灌 canonical EOD。不能以台灣區域即宣稱台灣出口 IP 一定被來源接受。

## 驗收

依序記錄安全測試、Life 既有活動來源回歸、Janus MIS 讀取、CI、Cloud Run 100% revision、兩個服務身分的正向／未授權的負向請求、最終持股畫面及價格日期；任一缺證維持 PARTIAL／BLOCKED。

## 2026-10-30 跨專案交付索引

- 已變更 Life `services/tw_activity_proxy/main.py`：HTTPS host/path allowlist、僅 GET、DNS 公網檢查、禁轉址、TLS、回應 32MB / MIS 2MB 上限與逾時；原先驗證 shared secret 的程式已移除，**前提是 Cloud Run IAM 必須保持 private**。
- 已變更 Life `backend/app/services/tw_request_router.py`：採 VM 服務身分 ID Token，缺 token 拒絕，不再攜帶公開靜態 token。
- 舊的自動來源部署 workflow 已退役為 CI；新的 `.github/workflows/shared-tw-proxy-release.yml` 才是受控部署，要求 CI、舊 revision 回復基線、正式服務 IAM、無公開 Invoker、0% Candidate、未認證負向、SSRF 負向、MIS 正向及必要時 rollback。
- Janus `services/api/tw_proxy_client.py` / `services/api/intraday_quotes.py` 添加只有來源 403/5xx 才嘗試台灣代理的 read-only 備援（429 不備援）；Janus 權威規格見 `tommylin15/janus-omniforge/doc/spec/shared-taiwan-egress.md`。
- 既有 Live 核對曾見 `tw-activity-proxy-00005-c8k`／IAM public invoker 0；該版本由舊 workflow 發布，不視為新安全發布的整合 PASS。不能沿用已曝光的舊共享金鑰；新候選要求移除舊環境變數。
- **跨專案核准範圍**：本次僅對既有 proxy、Life caller、Janus API 與必要 service-specific Invoker 授權進行一次性工程，不新增第二個台灣代理、付費 API 或新 GCP 資源。

## 2026-10-30 正式發布結果（附真實 gate 範圍）

- 原 Live baseline：`tw-activity-proxy-00005-c8k`（之前的舊部署工作流）；新候選：`tw-activity-proxy-00006-dep`，採 0% 候選到 100% traffic promotion。
- 本次正式 Workflow [#41010462296](https://github.com/tommylin15/life_assistant/actions/runs/41010462296) 所有 steps PASS：測試、Cloud Run 私有 IAM baseline、Life/Janus Invoker、受控候選、無 token 未授權拒絕、metadata URL 負向 400、台灣 MIS `rtcode=0000`、切流後單一 100% readback、無公開 Invoker。部署指令移除舊共享 credential 環境變數；其值仍曾存在 Git 歷史，不能再使用。
- 由 Janus 現有 CI 在特定 Life 服務上建立一次性 `janus-user-api` 的 `roles/run.invoker`；已獨立 IAM readback PASS。Life 原部署者缺少 `run.services.setIamPolicy`，因此新流程僅作權限核對，避免引入不必要的 project-wide 擴權。
- 不包含：Life VM 現行 cron 是否已取得新版 client、台灣政府活動所有 host 的真實 end-to-end、Janus 最新 GHCR API deployment、Owner 持股日期與當日損益。這些不能因 Proxy 正向驗收當作 PASS。
