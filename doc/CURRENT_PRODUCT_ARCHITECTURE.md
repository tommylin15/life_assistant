# Life — Current Approved Product Architecture (2026-10-10)

**產品方向 APPROVED；部署及使用者功能以 current GitHub source / runtime 為準。** 具體最新證據請看 [CURRENT_STATE](CURRENT_STATE.md) 和 [P0/P1 acceptance](P0_P1_CONSOLIDATED_ACCEPTANCE_2026-10-10.md)。

## 系統與責任邊界

Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL。Life 負責 Data + UI + API + Execution + Integration，不是通用 Agent reasoning 系統。

最新核准入口：**ChatGPT 探索／核證 → Drive 精選池 → [獨立交接 Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) → Life 每日 GCP Job → 單一 PostgreSQL curated pool**；Life 不做來源爬蟲、舊 Queue 或第二次 AI。既有 direct batch API 尚是相容 source 實作，不能冒充新 Job 已部署。唯一輸入規格：[Sheet Job 交接契約](curated_sheet_job_ingestion.md)；[現有 API](free_events_candidate_ingestion_contract.md) 作相容對照。

## 使用者產品（活動 UX V3，2026-10-11）

**唯一正式細節規格：[活動 UX V3](curated_activity_user_features.md)**。前端只有「限時機會／活動探索」兩個活動入口，單一精選池，第三個「精選」退出導覽；無使用者星等顯示／排序／篩選。各入口預設從 PostgreSQL 查 5 個主活動群組，續看 10 個，支援最新收錄、時間速查、一般搜尋與少量篩選。使用者僅能自行選擇收藏、建立既有 Task、Google Calendar 活動日期標記。**Task 與 Life 日曆都要可從既有項目直接點「前往網址」**；日曆標記是全天 transparent、不占 busy。這些是核准 UX，不等於已實作或部署，現況見 [CURRENT_STATE](CURRENT_STATE.md)，工項見 [TODO](todo.md)。

## 管理端與個人化

- Life admin：精選資料與錯誤、系統健康、內部 Life Drive AI Provider 策略、feature rollout。不可閱讀他人 Google Drive 文件、OAuth secret 或替他人建立私人物件。
- 個人：Google OAuth / Drive AI consent、手機底部／桌面左側導覽及排序、首頁卡片與提醒偏好；個人記錄依帳號隔離。保持 Material 3 responsive UI。
- ChatGPT 的活動探索和獨立 Google Drive 優惠研究不屬 Life 內部 Drive AI Provider；互不改動。

## Implementation ≠ release

現有 GitHub main 已有 curated API/資料模型、兩入口 source、帳號隔離 action 與 Task/Google Calendar 的基本來源寫入；但 UX V3 的查詢、收藏、連結可點、刪除重複入口與實際 runtime **NOT VERIFIED**。源碼、CI、staging 與 production E2E 各自判定，不以本文件宣稱完成。
