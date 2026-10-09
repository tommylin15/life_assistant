# life_assistant — AI Provider Routing & Cost Policy

> **2026-10-10 現行權限分離：** 本文只管理 Life Backend 自身 Drive AI Provider 的 Gemini/Groq/OpenRouter/Shared Codex 路由。使用者自行建立的 **ChatGPT Chat 活動精選排程**是完全獨立的 AI 呼叫與計費途徑，不由 Life Provider fallback 控制。平台管理頁面見 [Issue #11](https://github.com/tommylin15/life_assistant/issues/11)，每位使用者的 Drive OAuth 與 AI 同意仍個別受保護。Provider live 測試與正式成本仍須實際驗證。


> **現行核准政策** · 2026-10-09 · 適用範圍：life_assistant 本身的 Drive AI enrichment；不包含 ChatGPT Chat 活動精選；不直接改變 omniAgent、Janus 等其他專案。
>
> **狀態分離：** GitHub `main` 已有 Provider 路由與測試，CI run [37874176801](https://github.com/tommylin15/life_assistant/actions/runs/37874176801) 為 PASS；**新路由的 production deployment／真實多模型連通性、成本及 owner E2E 均 NOT VERIFIED**。ChatGPT 活動精選由 ChatGPT 自有模型與排程執行，Life 不負責活動 AI Batch。

## 1. 單一正式順位

模型備援順位必須保持：

| 順位 | Provider 與策略 | 選擇方式 | 狀態／依賴 |
| --- | --- | --- | --- |
| 1 | Gemini `latest-3-flash` | 最多三個穩定、文字、支援 `generateContent` 的 Flash 候選 | 與 Lite 使用相同已授權 Gemini API key |
| 2 | Gemini `latest-3-flash-lite` | 最多三個穩定、文字、支援 `generateContent` 的 Flash-Lite 候選 | Flash 全部失敗才使用；獨立偏好 |
| 3 | Groq | 已配置的核准模型 | 不可私自更換授權、付費層級 |
| 4 | OpenRouter | 已配置的核准模型，保留 data-collection policy | 無合格路由則失敗/跳過 |
| 5 | **私有 Shared Codex** | 既有 omniAgent Cloud Run consumer | 需要 project-scoped owner、受允許的 GCP identity、明確啟用 |

`latest-3-flash`／`latest-3-flash-lite` 是 life_assistant 應用內的**選模策略別名**，**不是** Google API 可直接提交的原生模型名稱。應先讀官方模型清單，取得真實 model ID。只選合格的 stable text 型號，不為湊滿三個而納入 preview、Lite（Flash 組）、Flash（Lite 組）、TTS、圖片等變體；不到三個就使用現有合格數量。

**「最後成功模型優先」詳細規則：**

1. PostgreSQL 既有 `ai_provider_preferences` 以 `provider=gemini`、`provider=gemini_lite` **各自保存**上次成功模型；不共用記憶，Cloud Run 重啟可延續。
2. 每組從本次模型清單確認上次成功型號仍存在且合格；如存在，將它排第一，後接該系列其餘最新候選，**每組最多三個實際嘗試位置**。若上次成功模型比最新三個還舊，該型號仍可占一個位置（最多再加兩個最新模型）。
3. 成功時才更新該系列最後成功型號；錯誤或假輸出不得覆寫；不因別的系列成功而改寫本系列。避免每次呼叫都盲目輪詢三個。
4. 真實配額/429、逾時與服務異常依現行 bounded retry／backoff；禁止無限循環、跨三個模型重複消耗整個 batch；每一家 provider 的 direct-health 需獨立驗收，fallback 成功不掩蓋先前的 direct FAIL。
5. Provider 沒有合法模型、缺憑證、無 owner／權限時不得虛構成功。依當前 resolver 的可配置降級處理：未配置外部後備者不進鏈；**Gemini 主模型缺設定時仍 fail closed**。不得因 Codex 無 owner 擋住可以獨立處理的公用 Gemini 工作。

## 2. Shared Codex（使用者稱「Codex CLI」）

本專案裡「Codex CLI」**等同既有私有 Shared Codex 服務**，而非在 life_assistant 的 Cloud Run 安裝 CLI。使用 `SharedCodexEnrichmentProvider` 呼叫 omniAgent 所持有的私有 Cloud Run endpoint，以 server-side project-scoped owner ID、GCP audience-bound ID token、request ID 與固定輸出契約操作。

- **絕對不**在 consumer 複製、mount、讀取、輪換共用 Codex OAuth Secret，也不新增另一套 Codex CLI。
- `CODEX_PRIMARY_ENABLED` 是**歷史相容的設定鍵名稱**，現在語意是**是否允許最後一層 Shared Codex fallback**；名字不代表優先權第一。
- Private Codex 的佇列/回覆時間與 IAM 成本只應適用於 Life 內部有 owner 授權的 Drive AI 工作；不得讓外部 ChatGPT 活動排程繞過授權使用。
- **不**把 Codex 運作邏輯移進 life_assistant 的 Agent runtime；模型仍只提出受 schema 約束的文字候選，操作由 FastAPI/權限/審核負責。

## 3. Drive AI 呼叫原則（不包含活動分析）

1. **L0 零模型**：權限檢查、文件清單、指紋比對、快取、資料搬移及狀態查詢走普通程式，不因使用者打開頁面就呼叫 AI。
2. **只有經使用者明確同意的文件內容才可分析**；同一文件版本、context 與模型/抽取策略 fingerprint 可以重用快取；不得把別人的 Drive/Google 資料交給 Provider。
3. **依序備援，一次成功即停**：Gemini Flash → Flash-Lite → Groq → OpenRouter → private Shared Codex。各 Provider 真實健康個別驗收，後備成功不得掩蓋主用失敗。
4. **限額與可恢復錯誤**：有界時間、429/backoff、批次數上限、耗費可稽核；錯誤只記錄脫敏 metadata，不記錄 OAuth token、原始文件正文或金鑰。
5. **活動精選不使用本文 AI 路由**：ChatGPT Chat 自行分析，Life 只接收精選資料並存入 PostgreSQL；無 Life 活動 Queue、Batch AI、source crawler 或第二次語意判定。

## 4. 實作對應與驗收

| 現有位置 | 用途 | 備註 |
| --- | --- | --- |
| `backend/app/services/ai_enrichment_provider.py` | Gemini Flash/Lite dynamic selection、fallback、Codex consumer、模型 preference | 已有程式；生產實測另驗 |
| `backend/app/services/drive_enrichment.py` | consent、fingerprint/cache、partial outcome 的參考實作 | 文件專屬 schema 不應直接拿來塞活動 |
| `backend/app/models/ai_provider_preference.py` | 單表中兩個 provider key 的 last-success | 現有 schema 即可，無須另建 migration |
| `backend/scripts/run_drive_external_ai_acceptance.py` | 分 provider 真實 smoke/回傳失敗 mask | 必須兩組 Gemini 分開核對，不能用整體 PASS 代替 |

驗收至少包含兩組模型池完全隔離、最多三個、記住上次成功、型號已移除的回復策略、模型列表失敗、429 不暴衝、所有後備順序、provider 健康不遮蔽、consent OFF 零送出、內容未變零 AI 呼叫、Drive AI cache 併發去重、owner isolation、正式成本上限與真實 release SHA 的 deployment/runtime 證據。

**完成判定：** 文件整頓和 CI 可各自 PASS；新版五層路由 deployment、真實外部 Provider / Codex E2E 未取得新一輪證據前仍 **NOT VERIFIED**。歷史討論和 2026-10-07/08 的 Codex-first/Gemini-only 設定**不是目前政策**，但其當時的失敗與驗收紀錄仍保留於 `doc/integrations.md` 供稽核。
