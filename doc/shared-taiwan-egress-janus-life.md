# Life／Janus 共用台灣出口通道

狀態：設計與來源盤點完成；尚未完成安全修復、部署與跨專案實測。

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
