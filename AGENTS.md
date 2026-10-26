# AGENTS.md — Life Assistant

這是 `life_assistant` 的代理人工作指引與執行規範。正式專案規則以 [`doc/PROJECT_RULES.md`](doc/PROJECT_RULES.md) 為最高準則；開始任何工作前必須先完整閱讀它。

> **專案級禁令：本專案嚴格禁止使用、呼叫或套用任何 Superpowers skill / workflow。** 所有 `skills://plugins/superpowers/...` skills 均禁止；已移離工作樹的 `docs/superpowers/` 僅視為 Git 歷史資料，不得作為目前工作流程、Source of Truth 或必要輸入。

---

## 1. 專案定位與研究系統屬性

- **專案定位**：本專案負責 `life_assistant` 的產品、資料工程、軟體工程、治理、模型研究、測試、CI/CD、部署與驗收。
- **系統屬性**：這是**研究系統開發專案**。
- **責任邊界**：
  - `life_assistant` 負責：Data + UI + API + Execution + Integration（含 PostgreSQL 營運資料庫、Flutter 前端、FastAPI 後端、本地 ONNX 語意推論、Google 服務整合、ChatGPT Bridge/MCP、Activity/Execution log、無 AI reasoning 的一般背景排程）。
  - 通用型 Agent reasoning loop、LangGraph runtime、全域 Tool Registry 屬於獨立專案 `omniAgent`，不在本專案重複建構。

---

## 2. 核心行為原則

- **官方來源優先**：以官方規格、真實 API 回應與一手資料為準，不採用二手未查證臆測。
- **可追溯、可重跑、可稽核**：所有資料變更、資料庫遷移與重要操作均需具備回溯與審計依據。
- **缺值不造假**：資料缺失或未知時保持 null/空白，嚴禁為了欄位完整性偽造數值、日期、資格或成功標記。
- **資料不足寧可不下結論**：資訊不齊全時停下來指出未知或標示 `NOT VERIFIED`，不可主觀推定。
- **LLM 不擁有最終數值與發布決策權**：數值驗證以確定性邏輯/資料庫為準；正式 Production 發布需經規範門檻。
- **Partial success 不得包裝為 full success**：子項目部分通過時誠實標示 `PARTIAL`，不得美化為全部通過。
- **文件完成不等於功能完成**：僅撰寫完規格或文件不代表已實作或已上線，禁止以文件代表 runtime evidence。
- **🔥 有不妥要主動提出，嚴禁盲目說可以**：若發現使用者指示或現有設計存在架構衝突、安全漏洞、資料破壞風險或技術不妥，**必須主動明確提出質疑、衝突點與改善建議**，嚴禁未經思考逕行同意或逢迎「可以」。

---

## 3. Source of Truth 判定準則

涉及目前程式碼、API、schema、migration、tests、CI/CD、deployment、infra、bug 或實際完成狀態時，**必須優先讀取 `life_assistant` GitHub Repository**。

若 GitHub 與 Google Drive 規格不同：
1. **目前實作與部署狀態**：一律以 **GitHub main／runtime evidence** 為準。
2. **原始設計與核准規格**：參考 **Google Drive**。
3. **衝突處理**：必須主動指出差異與衝突，**不得自行覆蓋任一方**。

---

## 4. GitHub 開發權限與自主開發範圍

`life_assistant` 目前使用 **`main` 單一 branch**。AI 在未涉及高風險操作的前提下，**一般開發工作不需要每一步再次取得確認**，可直接讀寫並 commit 至 `main`，包含：
- Application source（Python / Dart / TypeScript / JavaScript）
- API / schema / SQL migration（Alembic 等非破壞性遷移）
- Tests（單元、整合、契約測試）
- Docker / scripts / IaC
- GitHub Actions（CI/CD V3 主線）與既有 Cloud Build 診斷相容設定
- Firebase / Cloud Run / deployment config
- Markdown 與專案文件

**修改前要求**：修改前必須先檢查目前 GitHub implementation、既有 caller 與現有測試，修改最少必要檔案。

---

## 5. 目標架構基準

現行正式目標架構：
```text
Firebase Hosting
    ↓
Flutter Web / PWA
    ↓
Cloud Run — FastAPI Backend
    ↓
PostgreSQL (Operational Source of Truth)
```
- **PostgreSQL** 是唯一的中央 Source of Truth，前端絕對不得直接碰資料庫。
- **SQLite** 僅屬既有版本資料與未來原生 App 本機快取，非系統核心資料來源。
- AI 可修改及執行 GitHub Actions 能力範圍內的 CI/CD；若由 GitHub Actions 負責部署 GCP，應在 commit 後追蹤 workflow、deployment 與 runtime 結果。

---

## 6. 完成判定標準（Definition of Done）

**不能只因程式已寫完或 CI 綠燈就宣稱完成。**

必須依任務需要多維度驗證：
1. `implementation`（程式碼實作與型別檢查）
2. `tests`（單元測試與回歸測試）
3. `CI`（四項核心 CI Job 通過）
4. `deployment`（Staging / 候選版本部署完成）
5. `runtime`（服務健康度、HTTP 狀態碼、API 回應）
6. `integration`（真實外部依賴整合與資料庫讀回）

**狀態標示規範**：
- 僅使用：**`PASS` / `FAIL` / `NOT VERIFIED`**
- 證據完整才可標示 **`DONE`**；部分完成一律標示 **`PARTIAL`**。

---

## 7. 高風險操作（必須使用者明確確認）

以下操作**嚴格禁止**擅自執行，必須取得使用者明確確認：
- Production 大量或不可逆資料刪除
- Destructive migration（包含 drop table/column、清空使用者資料）
- 刪除 production GCP / database / Firebase 資源
- 重大 IAM / Service Account 權限變更或提權
- Production secret / credential rotation
- Force push / rewrite `main` history
- 可能造成重大 production outage 的架構或組態變更

*(一般程式修改、tests、commit、CI/CD 與既有授權的正常部署不需額外確認)*

---

## 8. Google Drive 存取邊界

**唯一允許主動搜尋與讀寫的 Drive 根資料夾**：
> **`life_assistantGPT`**

- **用途**：
  - 正式規格與長期文件
  - 模型推演暫存
  - 模型與研究產物
- **限制**：暫存資料不得直接視為 production source of truth。
- **長期回寫**：具有長期價值的架構、治理、SPEC、runbook、研究與驗收內容，可主動回寫此資料夾。

---

## 9. 工程細節與實作風格（Ponytail）

- **規範依據**：測試策略、migration、secrets、observability、runtime validation、CI/CD 細節與完整交付規範，依 Drive 內 **`life_assistant Engineering Governance & Delivery Runbook`** 執行。
- **Ponytail 風格**：
  - 優先重用現有 helper、型別與模式；不建立只有一個實作的抽象、factory 或過度鷹架（no speculative scaffolding）。
  - 修 bug 先追查所有 caller，在共用根因處修一次。
  - 任何刻意接受的效能或正確性上限，用 `ponytail:` 註解寫明上限與升級條件。
- **發版公告治理**：主動依 `doc/product_release_notes_policy.md` 判斷產品可見性，候選時同步版本號與「最新消息」。

---

## 10. 回報格式要求

每次任務完成回覆必須至少包含：
1. **修改內容**（具體異動檔案與邏輯）
2. **驗證結果**（明確列出各維度 PASS / FAIL / NOT VERIFIED 與對應 Actions/Runtime 證據）
3. **尚待決定事項或未完成原因**（誠實指出未驗證項目，不把未實作的未來擴充寫成現況）
