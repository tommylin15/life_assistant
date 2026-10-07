# 生活助理 App v0.1 — Integrations

## 1. Google Sign-In

用途：

- 身分識別
- Gmail 授權
- Calendar 授權
- Drive Bridge 授權

要求：

- 採最小權限原則
- scope 分項請求
- 清楚顯示使用目的
- 支援重新授權
- 支援斷線 / revoke 後的降級模式

---

## 2. Gmail

### v0.1

- 取得郵件必要 metadata
- 顯示摘要
- 一鍵轉待辦
- 一鍵轉行程
- 掛到專案

### 不做

- App 內寄信
- App 內回信
- 自建 Mail Client
- Gmail 全文長期鏡像

---

## 3. Google Calendar

### v0.1

- 讀取
- 建立
- 修改
- 刪除
- 本機 / Backend 快取策略依目前架構實作
- Gmail / Item 轉行程

### 衝突策略

- 遠端修改與本機／Backend 修改同時存在時，應提示或依明確 policy 處理
- 不應靜默覆蓋
- 刪除動作需確認或符合明確 policy

---

## 4. ChatGPT Bridge Backend

ChatGPT Bridge Backend 屬於 life_assistant，目的在於讓 ChatGPT 或其他授權 client 安全地讀取 life_assistant context、提出 proposed actions，並由 life_assistant Backend 執行。

核心責任：

- context read / export
- proposed action contract
- schema validation
- request / action idempotency
- permission / confirmation policy
- action execution
- action result
- Activity / execution log

ChatGPT Bridge Backend 不等於 LangGraph Agent，也不負責跨系統 reasoning orchestration。

---

## 5. MCP / Integration API

life_assistant 可提供 MCP Server 或等價 Integration API，對外暴露自己的能力，例如：

- task.list / create / update / complete
- calendar.list / create / update
- note.search / create
- project.get
- activity.list

life_assistant 只維護自己的 Capability Catalog / MCP Tool Catalog，包括：

- tool name
- version
- input / output schema
- required permission
- risk / confirmation requirement
- idempotency contract
- error contract

跨產品的 Global Tool Registry、Workflow Registry、Agent Runtime 與 Agent Worker 不在本專案，由 `omniAgent` 負責。

---

## 6. Google Drive Bridge（Legacy / Fallback）

### 6.1 目的

既有 Google Drive Bridge 保留作為相容 / fallback integration，讓 App 與 ChatGPT 在沒有直接 MCP / Backend integration 時交換結構化資料。

Drive Bridge 不再是新架構的中央資料來源，也不是唯一 ChatGPT integration 方法。

### 6.2 預設路徑

```text
生活助理/
└── ChatGPT_Bridge/
    ├── README.md
    ├── bridge_manifest.json
    ├── current_state.json
    ├── inbox.json
    ├── projects.json
    ├── pending_actions.json
    └── history/
```

### 6.3 bridge_manifest.json

至少包含：

- bridge_id
- schema_version
- app_version
- exported_at

### 6.4 life_assistant → Drive

輸出可包含：

- 今日狀態
- 近期待辦
- 近期行程
- 等待中事項
- 進行中專案
- 使用者指定上下文

### 6.5 ChatGPT → Drive

可寫入：

- proposed_actions
- summaries
- recommendations

### 6.6 匯入規則

所有 proposed actions 必須：

1. schema 驗證
2. permission / policy 驗證
3. 顯示預覽或依 policy 決定是否需要確認
4. 由 life_assistant 執行
5. 寫入 Activity / execution log
6. 產生 execution result

不得讓 ChatGPT 或 omniAgent 直接繞過 life_assistant Backend / policy 寫入 PostgreSQL。

---

## 7. ChatGPT Onboarding

App 可提供「ChatGPT Bridge / MCP 設定」入口。

可能狀態：

- Backend / MCP：Available / Unavailable
- Google Drive fallback：Connected / Not connected
- Bridge Folder：Ready / Missing
- ChatGPT integration：Not verified / Verified

舊 Google Drive Bridge 的測試流程可以保留，但應明確標示為 fallback / compatibility path。

---

## 8. Share Bridge

提供：

- 複製文字
- 複製 JSON
- 系統分享

用途：

- MCP / Backend integration 尚未設定時
- Google Drive Bridge 未設定時
- 緊急 fallback
- 使用者只想分享單一事項時

---

## 9. Local Folder ↔ Google Drive Folder Sync

既有同步能力可保留；其是否繼續作為 Phase 1 主功能，需依 Web / Backend 架構與實際需求驗證。

核心規則仍應遵守：

- 不靜默覆蓋衝突
- destructive sync 需可追蹤
- PostgreSQL 主資料與 Bridge / sync 檔案角色不得混淆

完整舊規格見 `sync_spec.md`。

---

## 10. ChatGPT Bridge JSON Contract

既有 Drive Bridge JSON schema、action registry、版本相容與驗證規則見：

`bridge_schema.md`

該文件保留作既有 Drive Bridge contract；若其中出現「SQLite 是主資料來源」等舊架構描述，屬 legacy context。

目前正式 source of truth 與 integration 邊界以：

- `PROJECT_RULES.md`
- `decisions.md`
- `architecture.md`
- `project_boundary.md`

為準。

實作時不得以 README prose 取代 schema 驗證。
# Drive AI provider configuration — 2026-10-07

使用者已選擇 Gemini 主用、Groq 第二順位、OpenRouter 免費第三順位。Backend 保留既有 OpenAI adapter，三個服務共用 Chat Completions 傳輸與既有 Tag / related Note 驗證；Gemini / Groq 使用嚴格 JSON Schema，OpenRouter 使用 JSON mode + schema prompt，因符合隱私限制的免費 endpoint 不一定支援 JSON Schema；不新增 SDK。

- `AI_ENRICHMENT_PROVIDER=gemini`、`AI_ENRICHMENT_MODEL=latest-3-flash`：每次新分析讀取 Google models 清單，按數字版本選最新三個支援 `generateContent` 的正式文字 Flash 模型，依新到舊嘗試。排除 Lite、preview、image、TTS 等變體；每個 stage 最多三次模型呼叫。
- `AI_ENRICHMENT_FALLBACK_PROVIDER=groq`、`AI_ENRICHMENT_FALLBACK_MODEL=openai/gpt-oss-120b`：Gemini stage 失敗後呼叫 Groq。各 stage 分別保留 failure / partial 語意；不讀使用者資料來驗收。
- `AI_ENRICHMENT_TERTIARY_PROVIDER=openrouter`、`AI_ENRICHMENT_TERTIARY_MODEL=openrouter/free`：前兩個服務失敗後只呼叫一次免費路由；指定 `require_parameters=true`、`data_collection=deny`，沒有符合條件的免費 endpoint 時保留 failure / partial 語意，不改用付費模型。
- `GEMINI_API_KEY` / `OPENROUTER_API_KEY` 的授權來源是 `omniagent-bundle`；只複製所需兩個欄位，Groq key 由使用者指定的本機檔案讀取。三把 key 與 routing config 已依明確授權寫入 `life-assistant-bundle` version `7`，原有 DB / OAuth / Picker 欄位驗證一致；不讓 runtime 取得 omniAgent 的 DB / signing secrets。
- Consent 預設 OFF；相同 bounded context 與 related Note snapshot 才可送出，OAuth / user identity / DB credentials 不送給模型。
- Cache fingerprint 包含 provider / model routing policy。移動模型策略按 UTC 日期失效，最多沿用一天；force re-analysis 可立即略過 cache。execution run metadata 的 provider / model 表示設定的 routing policy；Gemini selected-model log 與 live acceptance `served_models` 記錄實際成功模型。
- Live acceptance 分別驗證主用與備援，不讓備援成功掩蓋 Gemini 失敗；只使用 synthetic context，不讀使用者資料。

Local live evidence：Gemini `3.8` / `3.7` 回覆 `503 UNAVAILABLE` 後，`3.6 Flash` 的 tags / related Notes 均 `200` 且 acceptance PASS；`openrouter/free` 與 Groq `openai/gpt-oss-120b` 的兩個 stage 亦 PASS。這是本機 API evidence，不等同 deployed runtime acceptance。多順位的最壞等待時間可能超過 5 分鐘，因此 Cloud Run request 與 live acceptance task timeout 均設為 10 分鐘。

API references：[Gemini compatibility](https://ai.google.dev/gemini-api/docs/openai)、[OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)、[Free router](https://openrouter.ai/openrouter/free/)。

## Secret 與真實 Drive 驗收設定 — 2026-10-07

- Life Assistant Cloud Run revision `life-assistant-api-00154-xrt` 只引用 `LIFE_ASSISTANT_BUNDLE=life-assistant-bundle:latest`；沒有 omniAgent / Janus bundle 的 runtime dependency。
- `life-assistant-bundle` 現在只有 version `7` enabled；被取代的 versions `1–6` 均 destroyed。新版 DB / OAuth / Picker 設定已載入且真實 Drive PASS。
- Groq key 另依使用者授權加入 `omniagent-bundle:2` 與 `janus-runtime-bundle:5`。omniAgent gateway / chat 更新 pinned reference 至 `2`；Janus API 重部署載入 `5`，三個服務 health 均 `200`。這次只追加 key，不宣稱其他專案已實作 Groq provider adapter。
- 新版本健康驗收後，`omniagent-bundle:1`、`janus-runtime-bundle:3–4` 已 destroyed；Janus runtime 只保留 `5` enabled。`janus-mart-codex-auth:1` 沒有 Gemini / OpenRouter 欄位，未修改或刪除。
- 真實 Drive fixture 使用 `tommylin15@gmail.com`；user sub `114499021556773459186`。使用者授權建立非敏感 Google 文件 `Life Assistant Drive Acceptance 2026-10-07`，file ID `1mLEdBCDyFdDO7dXDO5djgudKSjPhz2400ihV6YODpcs`，已透過 production Picker 選取並在 Drive UI 登記成功。
- GitHub `dev-test` 的 `DRIVE_ACCEPTANCE_USER_SUB` / `DRIVE_ACCEPTANCE_GOOGLE_FILE_ID` 已設定；保留 fixture 供後續重跑。驗收只讀來源並清理自己建立的本地測試 Note / Tag，不修改 Google 文件，不擴大 `drive.file` scope。
- 真實 Drive execution `life-assistant-postdeploy-acceptance-tqwr4` PASS、exit `0`。AI 診斷 execution `life-assistant-postdeploy-acceptance-9djrt` 中 Gemini 成功模型為 `gemini-3.7-flash` / `gemini-3.8-flash`，Groq `openai/gpt-oss-120b` 亦 PASS；但 OpenRouter 嚴格 JSON Schema 回覆 `404`。改用 JSON mode 後本機兩個 stage 均 `200`、acceptance PASS；完整新版 deployed gate 必須另行重跑，不以本機結果替代。

Final deployed evidence：release `2d08118a13c71c6fec97e8bfba0857b861eefd1e` 的 Drive Knowledge #47 / run `37568734572` final gate PASS。真實 Drive execution `life-assistant-postdeploy-acceptance-hlpg2` PASS；AI execution `life-assistant-postdeploy-acceptance-sqlx5` 三個 provider 各自 PASS、exit `0`，Gemini 成功模型為 `3.6 Flash` / `3.8 Flash`。OpenRouter JSON mode 已在正式 image 中通過兩個 stage，不再是只通過本機驗收。

Latest regression closure evidence：Habits release `02eda112...` 的 Drive Knowledge #54 曾在 live external AI gate 以 Cloud Run task exit `85` 失敗；因 deployment identity 缺 Cloud Logging read，當次無法可靠還原單一 provider 根因，因此不做未證實歸因。後續 `89d54011` 加入 408/429/5xx/transport bounded retry，`a44617bc` 改為逐一驗證全部 configured providers 並以 provider failure mask 回傳失敗組合，`668aa0db` / `3b75e9e2` 補齊測試。release `3b75e9e288be0d2179cd381281b55210a14ad875` 的 Drive Knowledge #59 / run `37595859159` final gate PASS；live external AI execution `life-assistant-postdeploy-acceptance-n8zk9` successful，real Drive / Picker / exact Firebase / OAuth / production UI 同輪亦全 PASS。


## Latest provider health after Shopping release — 2026-10-07

- Shopping final release `1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d` 的 Drive Knowledge Runtime Acceptance #63 / run `37625447402` 已執行兩次 attempt，兩次 final mandatory gate 均 FAIL。
- 失敗只來自 live external AI execution；兩次 Cloud Run task exit code 均為 `91`。依 `backend/scripts/run_drive_external_ai_acceptance.py`：`EXIT_PROVIDER_FAILURE_MASK_BASE=90`，Gemini bit=`1`，因此 `91` 可明確分類為 **Gemini-only direct provider health failure**。
- 同一輪 production config、synthetic Drive Knowledge runtime、real Google Drive fixture、exact Firebase release、OAuth redirect、Drive Knowledge production UI 均 PASS。
- 現行 live acceptance 的設計刻意逐一驗證 configured providers，不允許 fallback 成功遮蔽 primary provider failure；本次不修改此標準，也不把 fallback 可用性寫成 Gemini PASS。
- 狀態：**OPEN / FAIL**。這是獨立 cross-feature/provider-health regression，需後續另行修復或待 upstream provider 恢復後重驗；Shopping Package #7 的 direct product evidence 已完整，因此 #7 仍可封板 DONE。
