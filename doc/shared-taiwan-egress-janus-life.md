# Life／Janus 共用台灣出口通道

**最新狀態（2026-10-30）：Life 觀光署來源經既有台灣 Proxy 的可信 TLS 連線已恢復，Cloud Run 正式流量與雙來源 Live readback PASS。** 現役 `tw-activity-proxy-00011-zip`；安全發布 [#41014398927](https://github.com/tommylin15/life_assistant/actions/runs/41014398927)，獨立正式讀回 [#41014672520](https://github.com/tommylin15/life_assistant/actions/runs/41014672520)。Life VM 排程是否已使用新版 caller 與端到端匯入仍 NOT VERIFIED；下文舊 502／BLOCKED 內容是歷史診斷，均由本節新證據取代。


## 2026-10-30｜觀光署可信 TLS 連線修復：CLOSED／LIVE PASS

### 根因與最小修正
- [TLS 證據 #41014131479](https://github.com/tommylin15/life_assistant/actions/runs/41014131479)：同一官方網站使用 Python 系統 CA 與 Certifi，嚴格 X.509 驗證皆報 `verify_code=86 / Missing Subject Key Identifier`；較寬鬆的一般 OpenSSL verify 可以通過，並非服務端必然沒有可信 CA。
- [精確相容性驗證 #41014255690](https://github.com/tommylin15/life_assistant/actions/runs/41014255690)：只移除 `ssl.VERIFY_X509_STRICT` 旗標後，Python 握手 PASS；憑證 Subject 為 `media.taiwan.net.tw`、Issuer `TWCA Secure SSL Certification Authority`；`ssl.CERT_REQUIRED` 與 `check_hostname=True` 保持開啟。
- `services/tw_activity_proxy/main.py` 新增 `_origin_tls_context(host)`：**僅**對精確主機 `media.taiwan.net.tw` 略過這項舊憑證延伸欄位的 RFC 5280 嚴格格式檢查；其餘所有 Life host 和 `mis.twse.com.tw` 不動。CA 鏈、簽章、有效期限、Hostname 與 HTTPS 仍由 OpenSSL 驗證，沒有 `verify=False`、加載未知根憑證或取消 IAM。
- 測試 `test_only_official_tourism_host_uses_legacy_ski_interoperability` 覆蓋 scope、TLS >= 1.2、CERT_REQUIRED、Hostname。專用 CI [#41014344340](https://github.com/tommylin15/life_assistant/actions/runs/41014344340) PASS。

### 真實驗收
- [受控發布 #41014398927](https://github.com/tommylin15/life_assistant/actions/runs/41014398927)：0% Candidate 當輪 Life 官方 ZIP `HTTP 200` 且 `zipfile.is_zipfile=true`、MIS `rtcode=0000`、未授權拒絕與 SSRF 負向 PASS，然後才切 100% `tw-activity-proxy-00011-zip`，有既有回復基線。
- [Live 唯讀驗收 #41014672520](https://github.com/tommylin15/life_assistant/actions/runs/41014672520)：正式服務現役 revision `tw-activity-proxy-00011-zip`、100% traffic、IAM 無公開 Invoker、`TW_PROXY_SECRET` 環境變數不存在、未登入拒絕；官方觀光署 ZIP `HTTP 200`／**503922 bytes**／ZIP 格式 PASS；MIS HTTP 200／rtcode=0000 PASS。
- **完成範圍**：本項「Life 官方觀光署資料來源經共用 Cloud Run 代理的可信 TLS 連線」可結案。**未包含**：Life VM 現行定時任務的實際部署版本、全來源覆蓋、下載後的 PostgreSQL/Drive 匯入與活動 UI，這些仍各自 NOT VERIFIED。
- **持續安全條件**：此 compatibility exception 是精確主機的可追蹤例外；官方更新符合 RFC 5280 的憑證鏈時應回到 `VERIFY_X509_STRICT`，不能擴散到其他網域。

## 已有資產

- 共用既有 `tw-activity-proxy`，GCP `gen-lang-client-0593591102`，`asia-east1`。
- Janus API 位於 `us-central1`；Life 在既有 VM 透過 `TWRequestRouter` 使用代理。
- 現有 Cloud Run IAM 唯讀讀回：無公開 `allUsers`／`allAuthenticatedUsers` Invoker；已授權 Life VM 與 Janus API 兩個既有服務身分。舊靜態密鑰曾存在公開 Git 歷史，已於本次服務部署移除且不再使用。

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

## 2026-10-30 新一輪查核與未完成事項

- [#41011056509](https://github.com/tommylin15/life_assistant/actions/runs/41011056509) 正式代理讀回 Life 觀光署 ZIP 得到 HTTP 502 `upstream_unavailable`。
- 針對早期 Life 網站 IPv6 問題，已將代理 outbound 限縮到 IPv4（HTTPX 官方 `HTTPTransport(local_address="0.0.0.0")`）、維持 CA 驗證與 SSL TLS、避免環境任意 proxy、Life timeout 有界延長；仍不允許使用 `verify=False` 退回不安全 TLS。
- 新候選執行 [#41011718029](https://github.com/tommylin15/life_assistant/actions/runs/41011718029) 中，MIS 與私有 IAM／SSRF 閘門 PASS，但觀光署 ZIP **HTTP 502 / `ConnectError`**，因此發布 FAIL，**沒有提升新候選到 100% 流量**；現役安全版 `tw-activity-proxy-00006-dep` 保留。
- 對 Life 既有 VM 與所有官方網站來源的整合仍 **PARTIAL**。缺值需保留，不得因 MIS 正向成功冒充所有 Life 活動來源成功。
- IPv4/TLS 設定及分類測試在 [Taiwan proxy safe CI #41012113664](https://github.com/tommylin15/life_assistant/actions/runs/41012113664) PASS；此結果是離線測試，不代表 Live 活動下載可用。
- 後續排查 TLS 鏈、網站封鎖或 TCP 連線重置原因，尋找具官方授權與 TLS 正常的替代來源，維持少量有界探測，不新增付費資源；只在活動來源 Live 正向驗證 PASS 後切換。

## 2026-10-30 TLS 根因進一步定位與安全停損

- [候選診斷 #41012831462](https://github.com/tommylin15/life_assistant/actions/runs/41012831462) 從 0% 私有候選讀回：觀光署 ZIP `502 upstream_unavailable`、`ConnectError`、`reason=tls_certificate`；MIS 正向與私有 IAM 未受影響。
- [外部憑證驗證 #41012955722](https://github.com/tommylin15/life_assistant/actions/runs/41012955722)：GitHub runner 上的 OpenSSL `-verify_return_error` 為 PASS；證明從該 runner 的連線可驗證，不等於 Cloud Run 取得相同 TLS 鏈。
- 進一步把 HTTPX transport 改成 `ssl.create_default_context()`，依 OS 可信 CA 驗證，`CERT_REQUIRED` 與 hostname check 維持開啟；[Taiwan proxy safe CI #41013076822](https://github.com/tommylin15/life_assistant/actions/runs/41013076822) PASS。
- [嚴格雙來源候選 #41013128130](https://github.com/tommylin15/life_assistant/actions/runs/41013128130) MIS PASS、觀光署 ZIP 仍 HTTP 502／`ConnectError`，**發布 FAIL 且沒有切換 100%**。Life 來源未恢復，現役私有代理維持 `tw-activity-proxy-00006-dep`。
- 後續應有界比較 **Cloud Run 連到官方來源時所見 TLS 憑證鏈／目的 IP** 與 GitHub runner 可信驗證結果；僅在確認合法官方可驗證 CA 或合規替代入口時才調整。不可開 `verify=False`、跳過 hostname check 或把未知憑證加入 trust root；若無可信修復，該來源維持來源端 BLOCKED，Life 既有已核准快照／直接連線策略另行評估。
