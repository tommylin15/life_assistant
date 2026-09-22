# life_assistant — Product Spec

最後更新：2026-09-22

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

## 3. Dashboard

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

## 4. Tasks / Items

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

## 5. Google Calendar

支援完整雙向整合：

- 讀取
- 新增
- 修改
- 刪除
- 待辦轉 Calendar
- Gmail 轉 Calendar
- 簡化月／週視圖

整合失敗不得破壞 life_assistant 主資料。

## 6. Gmail

支援：

- 必要 metadata / snippet
- 重要郵件摘要
- 郵件轉待辦
- 郵件轉 Calendar
- 郵件掛到專案

不把 life_assistant 做成完整 Mail Client。

## 7. Projects

每個生活專案可聚合：

- 摘要
- Tasks
- Calendar refs
- Notes
- Attachments
- Gmail refs
- 最近活動

Phase 1 不做完整專案管理平台、甘特圖或複雜依賴。

## 8. Notes / Knowledge

支援：

- Markdown
- 標籤
- 搜尋
- 雙向連結
- 專案關聯
- 附件
- 轉待辦／行程

## 9. Habits / Shopping / Templates

Habits：週期、提醒、完成紀錄。

Shopping：快速新增、分類、勾選、專案關聯。

Templates：內建與自訂範本，可套用到待辦與生活專案。

## 10. Attachments

支援圖片、PDF、一般文件。

新的中央資料模型不得依賴單一手機的絕對本機路徑；實際 storage 方案需可由 Backend 管理或以安全 reference 表示。

## 11. Search

至少搜尋：

- Tasks
- Projects
- Notes
- Calendar cached refs

Gmail 遠端全文搜尋非 Phase 1 必要條件。

## 12. Notification / Background Jobs

life_assistant 可有一般 background jobs，例如：

- Calendar / Gmail sync
- reminders / notification dispatch
- migration
- export / backup
- maintenance

這些 worker 不包含 Agent reasoning loop。

## 13. Activity / Execution Log

所有重要操作應可記錄：

- 時間
- actor / source
- action
- 成功／失敗／部分成功
- entity reference
- error reference

不得把 token、PIN、secret 或不必要的敏感正文寫入一般 log。

## 14. ChatGPT Bridge Backend

ChatGPT Bridge Backend 是 life_assistant 的正式能力，**不得移除**。

用途：

1. 對 ChatGPT 或其他授權 client 提供允許讀取的生活狀態。
2. 接收 proposed actions。
3. 驗證 schema、版本、權限、idempotency 與 policy。
4. 必要時要求使用者確認。
5. 由 life_assistant Backend 執行實際 action。
6. 回傳 action result 並寫入 Activity / execution log。

### 14.1 Google Drive Bridge

既有 Google Drive Bridge 保留作 legacy / fallback integration。

舊版 `bridge_schema.md` 可繼續定義 Drive 檔案交換格式，但其中 SQLite 為主資料來源的歷史描述不再代表現行架構；現行主資料來源為 PostgreSQL。

### 14.2 MCP / Integration API

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

## 15. 與 omniAgent 的邊界

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

## 16. Security

- Google / external token 使用安全儲存或適當 secret mechanism。
- token / secret 不進一般 DB 欄位、export、Bridge payload 或一般 log。
- destructive / sensitive action 必須經 Backend policy。
- proposed action 不等於已執行。
- partial success 不得呈現成 full success。

## 17. Backup / Migration

- 既有 SQLite 資料不得清空或 drop。
- SQLite → PostgreSQL 必須可驗證。
- migration 應可安全重跑或具 idempotency。
- 支援 JSON / CSV 等可搬遷匯出。
- restore / migration 失敗不得破壞原始資料。

## 18. UI / UX

UI 需求以 `ui.md` 為頁面與流程規格，以 `design_system.md` 為視覺與元件規範。

Phase 1 必須支援手機與桌面瀏覽器，並優先確保 responsive layout、loading / empty / error / data 狀態一致。

## 19. Phase 1 不做

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
