# life_assistant — Product Spec

最後更新：2026-09-24

## 1. 產品定位

`life_assistant` 是個人生活資料與實際執行系統：

> **Data + UI + API + Execution + Integration**

核心流程：

> 資訊進來 → 分類 → 形成事項 → 排程／提醒 → 執行 → 留下紀錄 → 必要時提供給 ChatGPT / omniAgent 分析與提出建議

life_assistant 本身不負責通用 Agent reasoning 或跨產品 orchestration；相關能力由獨立 `omniAgent` 專案負責。

## 2. Phase 1 正式架構

```text
Firebase Hosting
        ↓
Flutter Web / PWA
        ↓
Cloud Run — FastAPI Backend
        ↓
PostgreSQL
```

原則：

- Flutter Web / PWA 為 Phase 1 主要交付面。
- FastAPI 為主要 Backend 入口。
- PostgreSQL 為 operational source of truth。
- 前端不得直接連 PostgreSQL。
- 既有 SQLite 保留為 migration source；未來原生 App 如需 offline cache 可再使用。
- Android / iOS 原生封裝延後。

## 3. Release Strategy / Scope Freeze

目前採以下順序：

### Phase 1 — Platform Release

先完成並上線目前 Web / Cloud 主線：

- Flutter Web / PWA。
- FastAPI / Cloud Run。
- PostgreSQL。
- SQLite → PostgreSQL migration。
- Google integrations。
- ChatGPT Bridge Backend / MCP baseline。
- security / logging / observability。

Phase 1 採 **scope freeze**。可持續進行 Phase 2 的研究、UX flow、mockup、schema proposal 與 API contract proposal，但候選功能不得自動成為 Phase 1 implementation blocker。

### Phase 1.5 — Real-use Validation

Phase 1 上線後，以真實使用觀察：

- 首頁真正需要的資訊。
- 重複或干擾性提醒。
- Gmail / Calendar / Task 常見轉換流程。
- routine / prompt 使用頻率。
- 仍需手動跨頁完成的高摩擦流程。

優先修正 bug、資料一致性與高摩擦流程，再確認 Phase 2 實作順序。

### Phase 2 — Product Enhancement

候選優先順序：

1. Today Cockpit。
2. Attention Model / Focus。
3. Routine Library。
4. Global Capture。
5. Plan。
6. Review。
7. Contextual AI entry points。

詳細規格見 `future_product_enhancements.md`。

## 4. Dashboard

首頁採混合型設計，顯示：

- 今日待辦
- 今日行程
- 提醒
- 等待中
- 採買
- 習慣
- 近期專案
- 近期重要日期

首頁摘要 Phase 1 可先由規則產生，不依賴 AI。

排序原則：逾期 → 今天到期 → 高優先 → 即將到期 → 一般事項。

Phase 2 才評估將 Dashboard 演進為 Today Cockpit；此變更不屬於 Phase 1 Release Gate。

## 5. Tasks / Items

支援：

- CRUD
- 優先度
- 狀態
- 到期日期
- 提醒
- 標籤
- 專案
- Checklist
- 附件
- 建立／更新／完成時間

快速輸入可使用規則解析；解析失敗仍需保留原始輸入並允許後補欄位。

## 6. Google Calendar

支援完整雙向整合：

- 讀取
- 新增
- 修改
- 刪除
- 待辦轉 Calendar
- Gmail 轉 Calendar
- 簡化月／週視圖

整合失敗不得破壞 life_assistant 主資料。

## 7. Gmail

支援：

- 必要 metadata / snippet
- 重要郵件摘要
- 郵件轉待辦
- 郵件轉 Calendar
- 郵件掛到專案

不把 life_assistant 做成完整 Mail Client。

## 8. Projects

每個生活專案可聚合：

- 摘要
- Tasks
- Calendar refs
- Notes
- Attachments
- Gmail refs
- 最近活動

Phase 1 不做完整專案管理平台、甘特圖或複雜依賴。

## 9. Notes / Knowledge

支援：

- Markdown
- 標籤
- 搜尋
- 雙向連結
- 專案關聯
- 附件
- 轉待辦／行程

Markdown 是內容格式與可攜能力，不取代 PostgreSQL operational source of truth。

## 10. Habits / Shopping / Templates

Habits：週期、提醒、完成紀錄。

Shopping：快速新增、分類、勾選、專案關聯。

Templates：內建與自訂範本，可套用到待辦與生活專案。

## 11. Attachments

支援圖片、PDF、一般文件。

新的中央資料模型不得依賴單一手機的絕對本機路徑；實際 storage 方案需可由 Backend 管理或以安全 reference 表示。

## 12. Search

至少搜尋：

- Tasks
- Projects
- Notes
- Calendar cached refs

Gmail 遠端全文搜尋非 Phase 1 必要條件。

## 13. Notification / Background Jobs

life_assistant 可有一般 background jobs，例如：

- Calendar / Gmail sync
- reminders / notification dispatch
- migration
- export / backup
- maintenance

這些 worker 不包含 Agent reasoning loop。

## 14. Activity / Execution Log

所有重要操作應可記錄：

- 時間
- actor / source
- action
- 成功／失敗／部分成功
- entity reference
- error reference

不得把 token、PIN、secret 或不必要的敏感正文寫入一般 log。

## 15. ChatGPT Bridge Backend

ChatGPT Bridge Backend 是 life_assistant 的正式能力，**不得移除**。

用途：

1. 對 ChatGPT 或其他授權 client 提供允許讀取的生活狀態。
2. 接收 proposed actions。
3. 驗證 schema、版本、權限、idempotency 與 policy。
4. 必要時要求使用者確認。
5. 由 life_assistant Backend 執行實際 action。
6. 回傳 action result 並寫入 Activity / execution log。

### 15.1 Google Drive Bridge

既有 Google Drive Bridge 保留作 legacy / fallback integration。

舊版 `bridge_schema.md` 可繼續定義 Drive 檔案交換格式，但其中 SQLite 為主資料來源的歷史描述不再代表現行架構；現行主資料來源為 PostgreSQL。

### 15.2 MCP / Integration API

新的 Backend 應可逐步提供版本化 MCP / Integration API，例如：

- `task.list`
- `task.create`
- `task.update`
- `task.complete`
- `calendar.list`
- `calendar.create`
- `calendar.update`
- `note.search`
- `note.create`
- `project.get`
- `activity.list`

life_assistant 維護自己的 Capability Catalog，包括 tool schema、version、permission、risk 與 confirmation policy。

## 16. 與 omniAgent 的邊界

以下 **不屬於 life_assistant**：

- LangGraph Agent
- Global Tool Registry
- Workflow Registry
- Agent Runtime
- Agent Worker
- 跨系統 multi-tool orchestration
- 通用 Agent reasoning / planning / retry-resume loop

這些由獨立 `omniAgent` 專案負責。

omniAgent 若需操作生活資料，應透過 life_assistant 的 MCP / Integration API，不得繞過 Backend 直接寫 PostgreSQL。

完整邊界見 `project_boundary.md`。

## 17. Security

- Google / external token 使用安全儲存或適當 secret mechanism。
- token / secret 不進一般 DB 欄位、export、Bridge payload 或一般 log。
- destructive / sensitive action 必須經 Backend policy。
- proposed action 不等於已執行。
- partial success 不得呈現成 full success。

## 18. Backup / Migration

- 既有 SQLite 資料不得清空或 drop。
- SQLite → PostgreSQL 必須可驗證。
- migration 應可安全重跑或具 idempotency。
- 支援 JSON / CSV 等可搬遷匯出。
- restore / migration 失敗不得破壞原始資料。

## 19. UI / UX

UI 需求以 `ui.md` 為頁面與流程規格，以 `design_system.md` 為視覺與元件規範。

Phase 1 必須支援手機與桌面瀏覽器，並優先確保 responsive layout、loading / empty / error / data 狀態一致。

Phase 1 主導航先維持 Dashboard / Tasks / Calendar / Projects / More；Today / Focus / Plan / Review 等 situation-oriented navigation 屬於 Phase 2 候選。

## 20. Phase 1 不做

以下不作為目前 Phase 1 完成條件：

- Today Cockpit / Focus / Plan / Review 主導航重構
- Routine Library
- Global Capture 完整版
- Contextual AI entry points
- People / relationship context
- LangGraph / Agent orchestration
- Global Tool Registry / Workflow Registry
- Agent Runtime / Agent Worker
- 多人協作
- 完整 offline-first 雙向同步
- Android / iOS 正式上架
- OCR
- 完整人生 KPI
- 完整專案管理套件
- 完整語音 AI Assistant
- Temporal / Iceberg 等非必要高複雜基礎設施

## 21. 未來產品強化原則

未來功能需符合：

- 以真實使用 evidence 決定優先順序。
- 不因外部參考專案存在就直接加入。
- 缺值維持缺值，不推測 completion / score。
- Today / Focus 等摘要規則需可解釋、可測試。
- AI 輸出與實際 execution result 清楚分離。
- mutation 仍需通過 Backend validation / permission / audit。
- 不改變 life_assistant / omniAgent 的正式責任邊界。
# CI/CD V2 release contract — 2026-10-08

Authorized infrastructure replacement retains Flutter Web/PWA on Firebase
Hosting, FastAPI on Cloud Run and PostgreSQL/Alembic. Main-push Cloud Build
2nd Gen runs CI only; an explicit full-SHA manual Release must separately pass
candidate, Preview and live API/UI/provider gates
before CLOSED; preserve existing failures and schedule timing. Full contract,
cost gate and recovery: `deployment_runbook.md`. Implementation is pending
real GCP/Firebase acceptance; no product capability is added by this section.

## Post-Calendar 台灣免費活動探索（核准規劃）

使用者核准在 Calendar #8 產品驗收完成後，以此項目為下一個第一優先產品開發。**MVP M0–M4**：來源 14 天新鮮度與授權、Event/Session/Registration Opportunity/Organizer 與來源安全/去重、Flutter 有效候選列表與 admin-only 來源健康、通知/待辦/筆記分別授權、GCP 每日 06:00/18:00 正式掃描切換。**E1**：主辦追蹤、進階偏好、摘要/靜音和報名管理；**E2**：使用者貼連結、交通距離、電子報和進階個人化。

採**精簡 PostgreSQL 活動卡**：核心活動/場次/報名窗口與資格、60–120 中文字摘要、標籤、官方連結、最低必要稽核；整站介紹與照片回主辦頁，缺圖採內建分類圖示。**12 小時增量掃描與 AI 推論解耦**：沒變動／規則足夠則 0 模型呼叫，AI 先在 Batch 產出可重用結果；一般使用者瀏覽或使用摘要建筆記不呼叫模型。統一模型備援政策見 [`ai_provider_policy.md`](ai_provider_policy.md)。

詳細規格、用例、工作切分與驗收見 [`taiwan_free_events_discovery_plan.md`](taiwan_free_events_discovery_plan.md)，正式排序見 [`phase1_delivery_order.md`](phase1_delivery_order.md)。此處僅為經同意的產品規劃，不代表已修改 PostgreSQL、部署 GCP 或新增 Flutter UI；也不自動覆蓋本規格既有 Phase 1 scope freeze / Release Gate。狀態：**APPROVED PLAN / NOT IMPLEMENTED**。
