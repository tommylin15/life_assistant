# Project Rules

本文件是本專案的正式開發規則、架構決策與工作限制；若與其他專案文件衝突，以本文件為準。

## 開始工作前

- 每次工作開始前，先完整閱讀本文件。
- 再閱讀與目前工作直接相關的規格文件；不要因未使用的功能而載入全部文件。
- 若本文件與使用者的新指示衝突，先指出衝突，再依使用者最新明確指示執行。

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

## 實作邊界

- UI 不得直接操作 PostgreSQL、SQLite、DAO 或 Google API。
- 前端透過 repository / use case / API client 與 Backend 溝通。
- Backend 負責 API、驗證、授權、資料存取與外部整合協調。
- 外部服務一律經 adapter / connector / tool 邊界；不得與 UI 強耦合。
- PostgreSQL schema 變更必須使用 migration；不得以 drop database 取代 migration。
- 現有 SQLite 使用者資料不得為了遷移方便而清空；SQLite → PostgreSQL 必須有可驗證、可重跑或可回退的 migration 設計。
- 重要、可追蹤的寫入操作在適用時必須記錄 Activity Log / execution log；log 不得包含 token、PIN、密碼或敏感郵件正文。
- 不新增 spec、decisions 或專項規格未定義的大功能。

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
4. 未經明確授權，不得部署 production 或建立／擴大付費 GCP 資源。

尚未完成 Backend / Web migration 時，必須明確區分「現有 SQLite / 原生 App 實作」與「新的雲端目標架構」，不得把規劃當成 runtime evidence。

## GCP / WSL

- 可使用本機 WSL 執行 dev migration、Linux/shell 驗證（包含 `bash -n`）與 GCP dev 驗收。
- WSL 不得用於 production 部署，也不得因此建立或擴大付費 GCP 資源。
- 需要既有 GCP/gcloud credentials 或 GCP dev 驗收時，使用既有已授權 dev 資源；不得自行建立 production 資源。

## Git

- 執行任何 commit 或 push 前，應先完成專案要求的 review 流程（目前文件稱 `/ponytail-review`）。
- 未經使用者要求，不建立 commit、push、production deployment 或付費雲端資源。
