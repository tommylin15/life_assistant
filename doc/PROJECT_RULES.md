# Project Rules

本文件是本專案的正式開發規則、架構決策與工作限制；若與其他專案文件衝突，以本文件為準。

## 開始工作前

- 每次工作開始前，先完整閱讀本文件。
- 再閱讀與目前工作直接相關的規格文件；不要因未使用的功能而載入全部文件。
- 若本文件與使用者的新指示衝突，先指出衝突，再依使用者最新明確指示執行。

## Skill / Workflow 限制

- 本專案**不得使用、呼叫或套用任何 Superpowers skill / workflow**。
- 禁止範圍包含所有 `skills://plugins/superpowers/...` skills，以及其衍生的 brainstorming、planning、TDD、debugging、execution、review、verification 等 Superpowers 工作流程。
- 本專案的工程方法、測試策略、debugging、驗證、CI/CD 與交付流程，應以本文件、GitHub 目前實作、相關正式規格與專案治理 / delivery runbook 為準，不得以 Superpowers 規則覆蓋或補充。
- `docs/superpowers/` 已從當前工作樹清除（保留 Git history），不得把其草稿當作現行流程、Source of Truth 或必要輸入，也不得因舊文件存在而重新啟用 Superpowers skill。
- 除非使用者日後明確修改本條規則，所有代理人與開發工作都必須遵守本禁令。

## 目前架構基準

目前正式目標架構改為：

```text
Firebase Hosting
    ↓
Flutter Web / PWA
    ↓
Cloud Run — FastAPI Backend
    ↓
PostgreSQL
```

- Flutter 仍是主要前端技術，但 Phase 1 以 Flutter Web / PWA 為主，不以 Android / iOS 安裝包為主線。
- Firebase Hosting 負責前端靜態資源與 Web/PWA 發布。
- FastAPI 部署於 Cloud Run，作為前端唯一主要後端入口。
- PostgreSQL 是新的 operational source of truth。
- 現有 SQLite 實作屬於既有版本資料與遷移來源；未來原生 App 若需要，可保留為 local cache / offline cache，但不再作為全系統中央 source of truth。
- 原生 Android / iOS 封裝延後到 Web/PWA 與後端穩定後再處理。
- 不把尚未完成的 Firebase Hosting、Cloud Run、PostgreSQL migration、排程或 Agent 能力寫成已實作。

## 專案定位與責任邊界

`life_assistant` 的正式定位是：

> **Data + UI + API + Execution + Integration**

本專案負責：

- 生活資料與 operational source of truth。
- Flutter Web / PWA。
- FastAPI Backend。
- 實際 action execution。
- Google / Gmail / Calendar / Drive integrations。
- ChatGPT Bridge Backend。
- MCP Server / Integration API。
- life_assistant 自己的 Capability Catalog / MCP Tool Catalog。
- schema validation、idempotency、permission / confirmation policy。
- Activity / execution log。
- 不含 AI reasoning 的一般 background jobs。

本專案**不負責**以下能力；這些由獨立 `omniAgent` 專案負責：

- LangGraph Agent。
- Agent reasoning loop。
- Global Tool Registry。
- Workflow Registry。
- Agent Runtime。
- Agent Worker。
- 跨產品 multi-tool orchestration。
- 通用型 multi-agent platform。

不得把上述 omniAgent 責任重新加入 life_assistant roadmap / WBS，除非使用者明確改變專案邊界。

詳細邊界見 `doc/project_boundary.md`。

## ChatGPT Bridge / MCP 規則

- ChatGPT Bridge Backend 必須保留在 life_assistant。
- Bridge / MCP 僅提供安全、版本化、可治理的 life_assistant capability；不承擔跨系統 Agent orchestration。
- 外部 ChatGPT 或 omniAgent 對 life_assistant 的寫入必須經 Backend validation、auth、permission / policy 與 execution log。
- omniAgent 不得直接繞過 Backend 寫入 PostgreSQL。
- 舊 Google Drive Bridge 可保留作相容 / fallback；若舊 Bridge 文件與 PostgreSQL 新架構衝突，以本文件、`decisions.md`、`project_boundary.md` 為準。

## 實作邊界

- UI 不得直接操作 PostgreSQL、SQLite、DAO 或 Google API。
- 前端透過 repository / use case / API client 與 Backend 溝通。
- Backend 負責 API、驗證、授權、資料存取與外部整合協調。
- 外部服務一律經 adapter / connector / tool 邊界；不得與 UI 強耦合。
- PostgreSQL schema 變更必須使用 migration；不得以 drop database 取代 migration。
- 現有 SQLite 使用者資料不得為了遷移方便而清空；SQLite → PostgreSQL 必須有可驗證、可重跑或可回退的 migration 設計。
- 重要、可追蹤的寫入操作在適用時必須記錄 Activity Log / execution log；log 不得包含 token、PIN、密碼或敏感郵件正文。
- 不新增 spec、decisions 或專項規格未定義的大功能。

## Background Worker 規則

life_assistant 可有一般 background jobs，例如：

- Calendar / Gmail sync。
- notification dispatch。
- migration / export / backup。
- maintenance。

這些工作不得包含 Agent reasoning loop。

若工作包含 LangGraph state、reason → choose tool → execute → observe → continue / finish 等 Agent runtime 行為，則屬於 omniAgent。

## 資料安全

- 不為方便開發而清空現有使用者 DB。
- destructive operation、migration、backup/restore、sync conflict 與 Bridge action 必須遵守對應專項規格。
- Google OAuth token、API secret 與其他敏感 credential 必須放安全儲存或 Secret Manager 等適當機制，不進一般 log、export 或 Bridge。
- 外部整合失敗不得破壞 PostgreSQL 主資料或既有 SQLite 遷移來源。

## 驗證與完成條件

完成工作前必須：

1. 檢查是否違反本文件與相關規格。
2. 執行適用的測試、lint、`flutter analyze`、backend tests 或其他驗證。
3. 說明修改內容、驗證結果與尚待決定事項。
4. 正常 production deployment 依 `main → GitHub Actions → tests/build → GCP → runtime/integration validation` 執行，不需逐次確認；高風險例外仍依下節規則處理。

尚未完成 Backend / Web migration 時，必須明確區分「現有 SQLite / 原生 App 實作」與「新的雲端目標架構」，不得把規劃當成 runtime evidence。

life_assistant 的完成條件不得依賴 omniAgent 是否完成；兩個專案可獨立驗收。

## GCP / CI/CD / IAM

- 2026-10-08 **CI/CD V3** 決策已取代 Cloud Build-led V2 主線；新版文件見 `ci_cd_ghcr_release_policy.md`。V3 已有真實 release 完成證據；每次新 SHA、來源 Job、前後端 OAuth、資料庫及應用整合仍各自獨立驗收，不能由此推定 PASS。

- 正式派版優先走 `GitHub main → GitHub Actions → tests/build → GCP → runtime/integration validation`。
- GitHub Actions 對 `gen-lang-client-0593591102` 使用 OIDC / Workload Identity Federation；不得建立長效 Service Account JSON key 作為一般部署憑證。
- `tommylin15/life_assistant` 專案期間，為正常 CI/CD 與既有部署資源所需的最小權限 WIF、部署 Service Account、Cloud Run、Cloud Build、Artifact Registry、Secret Manager 與 Firebase 例行 IAM 調整，視為已持續授權，不需逐次再詢問。
- IAM 必須遵守 least privilege，不得為方便直接授予 Owner / Editor。
- 下列高風險操作仍需使用者明確確認：重大 IAM / Service Account 擴權、跨專案或跨組織權限、production credential / secret rotation、刪除 production GCP / database / Firebase 資源、destructive migration、可能造成重大 production outage 的權限或資源變更。
- 可使用本機 WSL 執行 dev migration、Linux/shell 驗證（包含 `bash -n`）與 GCP dev 驗收；production 部署仍以 GitHub Actions 為主線。

## CI/CD V3 — 正式目標（2026-10-08，優先於下方歷史 V2）

- **單一正式目標**：`ChatGPT → GitHub main → GitHub Actions 完整測試/發布公開 GHCR digest → GCP API → GitHub Actions Logs → ChatGPT`。Push 只做完整測試；Release 以 full SHA 手動啟動、GHCR 發布、Cloud Run 0%-traffic 候選驗收、Firebase Preview、經驗收後明確切流與可回滾。
- 新流程不得呼叫 Cloud Build、不得主動寫 GCS/Artifact Registry，也不得新增其 repo/bucket；過去 Cloud Build 僅允許獨立、WIF **唯讀** 診斷。部署採**分離的最小權限 deployer**；唯讀 WIF 無法部署。
- Cloud Run **僅允許直接讀取公開 GHCR package 的 immutable manifest digest**；package visibility/讀取、live/candidate digest、服務身份和 0% tagged URL 安全均需實測。私人 GHCR 所需的 Artifact Registry remote repo 與本決策衝突，因此失敗關閉，不自動替換架構。
- 禁止因寫好文件而標示 V3 DONE。切換前盤點現有 workflow/Cloud Build triggers，實作後先取得 Actions、GHCR、WIF、0% revision、真實候選/Preview/Live、rollback 及未觸發 Cloud Build/未主動寫 GCS/AR 證據；再停用舊入口，不刪歷史記錄。
- **Cloud Run Revision 保留最新 10 個**：V3 promotion + live gates 全數 PASS 後，於成功 release pipeline 最後安全清理舊版；含流量、回滾 baseline、候選 tag 的版本不可刪。保護條件使數量超過 10 時必須 PARTIAL，禁止強行刪除。無流量且無最小實例的版本通常不計運算費；GHCR image digest 與 Jobs 所需映像另行保留。
- 實作與驗收規範以 `ci_cd_ghcr_release_policy.md` 為準；V2 已歸檔至 [archive/ci_cd_v2_policy.md](archive/ci_cd_v2_policy.md)，只供稽核，不再作為新建/變更 pipeline 的目標。

## 歷史政策

V2 Cloud Build 全文已歸檔：[archive/ci_cd_v2_policy.md](archive/ci_cd_v2_policy.md)。**新建/更新/部署只使用 CI/CD V3**，當次驗收需實際 runtime evidence。

## 2026-10-10 現行文件與產品決策

- 現況：[CURRENT_STATE.md](CURRENT_STATE.md)；產品與權限：[CURRENT_PRODUCT_ARCHITECTURE.md](CURRENT_PRODUCT_ARCHITECTURE.md)；執行順序：[phase1_delivery_order.md](phase1_delivery_order.md)。現行程式與 runtime 永遠優先於文件的歷史快照。
- **最新 2026-10-10 活動決策（覆蓋所有舊 Queue 規劃）：** Life 只接受 ChatGPT 已選活動，經驗證與授權 API 直接 upsert 到 PostgreSQL 精選池，再交給使用者自行瀏覽。取消文化部/TDX 擷取、官網 Excel 掃描、來源清單、Queue/ACK/claim、Cloud Run source Job/14 天觀測與第二階段發布；舊 DB migration 和資料只供兼容，禁止破壞性清除。見 [活動現行資料管線](taiwan_free_events_discovery_plan.md) 與 [兩個使用者功能的唯一詳細規格](curated_activity_user_features.md)；兩個入口在單一精選池上運作，與個人待辦／日曆／提醒資料分離，僅為核准設計而非已部署。
- AI 管理：平台內部 Drive AI Provider 配置與 ChatGPT Chat 排程不同；每位使用者仍須自行 Google OAuth 授權和 Drive AI consent。後台只管共用資料、Provider 策略與功能開放，個人導覽/首頁設定按帳號隔離。追蹤 Issues #10–#12。
- 曾經核准的 Drive 正式文件若與 GitHub 的現行規格不同，應明示差異，不默默覆蓋。

## Git

- `main` 是目前唯一正式 branch。
- ChatGPT 可直接修改 application source、tests、schema/migration、CI/CD、deployment config、IaC 與專案文件，並可直接 commit / push 到 `main`；一般開發不需逐步再次確認。
- 正常部署可由 GitHub Actions 自動觸發。
- force push、rewrite `main` history 或其他高風險 Git 操作仍需使用者明確確認。
- 修改前應先檢查目前 GitHub implementation；實作狀態以 GitHub/runtime evidence 為準。
