# Life — Current Approved Product Architecture (2026-10-10)

**產品方向 APPROVED；部署及使用者功能以 current GitHub source / runtime 為準。** 具體最新證據請看 [CURRENT_STATE](CURRENT_STATE.md) 和 [P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md)。

## 系統與責任邊界

Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL。Life 負責 Data + UI + API + Execution + Integration，不是通用 Agent reasoning 系統。

最新核准入口：**ChatGPT 探索／核證 → Drive 精選池 → [獨立交接 Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) → Life 每日 GCP Job → 單一 PostgreSQL curated pool**；Life 不做來源爬蟲、舊 Queue 或第二次 AI。既有 direct batch API 尚是相容 source 實作，不能冒充新 Job 已部署。唯一輸入規格：[Sheet Job 交接契約](curated_sheet_job_ingestion.md)；[現有 API](free_events_candidate_ingestion_contract.md) 作相容對照。

## 使用者產品（規劃）

同一精選池提供兩個可重疊的使用者功能：**限時機會**（追蹤報名／限量／提醒／待辦）與 **活動探索**（收藏、日期標記、旅遊規劃候選）。使用者自主勾選個人待辦、行事曆、通知或未來行程；日曆資訊標記、行動提醒、確定行程必須分開。星等、報名屬性、時效性、旅遊用途不能混為單一等級。**唯一詳細功能規格：[curated_activity_user_features.md](curated_activity_user_features.md)**。

## 管理端與個人化

- Life admin：精選資料與錯誤、系統健康、內部 Life Drive AI Provider 策略、feature rollout。不可閱讀他人 Google Drive 文件、OAuth secret 或替他人建立私人物件。
- 個人：Google OAuth / Drive AI consent、手機底部／桌面左側導覽及排序、首頁卡片與提醒偏好；個人記錄依帳號隔離。保持 Material 3 responsive UI。
- ChatGPT 的活動探索和獨立 Google Drive 優惠研究不屬 Life 內部 Drive AI Provider；互不改動。

## Implementation ≠ release

截至此份規格整理時，source 有 curated API / Alembic 0015 / 單一 Flutter 精選池以及泛用的 rollout／個人導覽功能。**兩個活動入口、個人追蹤/待辦/日曆/預警、旅遊候選尚未完成；真實 ChatGPT connector、正式 production rollout 和本 SHA runtime 不因文件修改而自動 PASS。** 
