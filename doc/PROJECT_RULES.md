# Project Rules

本文件是本專案的正式開發規則、架構決策與工作限制；若與其他專案文件衝突，以本文件為準。

## 開始工作前

- 每次工作開始前，先完整閱讀本文件。
- 再閱讀與目前工作直接相關的規格文件；不要因未使用的功能而載入全部文件。
- 若本文件與使用者的新指示衝突，先指出衝突，再依使用者最新明確指示執行。

## 實作邊界

- 產品是 Flutter / Dart 的 local-first 單人 App。
- SQLite 是 App 主資料來源；不使用自建 GCP backend、Firestore、Cloud SQL、Iceberg 或 OpenAI API。
- UI 不得直接操作 SQLite、DAO 或 Google API。
- 外部服務一律經 adapter；功能流程使用 repository / use case 分層。
- 新增 SQLite schema 必須有 migration；不得以清空或 drop database 取代 migration。
- Bridge JSON 匯入必須先做 validator；所有 proposed actions 在 v0.1 都要使用者確認。
- 重要、可追蹤的寫入操作在適用時必須記錄 Activity Log；log 不得包含 token、PIN、密碼或敏感郵件正文。
- 不新增 spec、decisions 或專項規格未定義的大功能。

## 資料安全

- 不為方便開發而清空使用者 DB。
- destructive operation、migration、backup/restore、sync conflict 與 Bridge action 必須遵守對應專項規格。
- Google OAuth token 只放安全儲存，不進一般 log、export 或 Bridge。
- 外部整合失敗不得破壞 SQLite 本機資料。

## 驗證與完成條件

完成工作前必須：

1. 檢查是否違反本文件與相關規格。
2. 執行適用的測試、lint、`flutter analyze` 或其他驗證。
3. 說明修改內容、驗證結果與尚待決定事項。
4. 未經明確授權，不得部署 production 或建立付費 GCP 資源。

尚未建立 Flutter source tree 時，至少驗證文件、路徑與可執行的本機檢查；不要為了通過驗證而虛構測試。

## GCP / WSL

- 可使用本機 WSL 執行 dev migration、Linux/shell 驗證（包含 `bash -n`）與 GCP dev 驗收。
- WSL 不得用於 production 部署，也不得因此建立或擴大付費 GCP 資源。
- 需要既有 GCP/gcloud credentials 或 GCP dev 驗收時，使用 Codex 升級權限執行；僅限既有 dev 資源。

## Git

- 執行任何 commit 或 push 前，必須先執行 `/ponytail-review`。
- 未經使用者要求，不建立 commit、push、production deployment 或付費雲端資源。

