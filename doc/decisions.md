# 生活助理 App v0.1 — Confirmed Decisions

## 目前已確認

- Flutter / Dart 繼續作為主要前端技術。
- Phase 1 優先 Flutter Web / PWA，不以 Android / iOS 安裝包為主要交付方式。
- Android / iOS 原生版保留既有程式結構，但凍結開發；Web/PWA 是目前唯一主要交付目標。
- Flutter Web / PWA 由 Firebase Hosting 發布。
- Backend 採 Python FastAPI，部署於 Cloud Run。
- PostgreSQL 作為新的 operational source of truth。
- 前端不直接存取 PostgreSQL。
- 現有 SQLite 保留為既有版本資料與 migration source；若未來原生 App 需要離線能力，可保留為 local/offline cache。
- Android / iOS 原生封裝延後到 Web/PWA 與 Backend 穩定後。
- 不使用 Firestore 作為主 operational database。
- 不把 Iceberg 當第一階段 operational DB。
- 單人版優先。
- Google 登入。
- Gmail：讀取 + 轉待辦 + 必要時轉 Calendar。
- Google Calendar：完整雙向整合。
- Google Drive：保留作為 Bridge / Integration 能力，但不再承擔中央資料來源角色。
- ChatGPT Bridge Backend 保留在 life_assistant。
- life_assistant 可提供 MCP Server / Integration API 與自己的 Capability Catalog。
- 重要操作需保留 Activity / execution log。
- Google 權限採最小權限與延遲授權。
- 開發完成需符合 coding_rules.md 與 release_checklist.md。

## Phase 1 Scope Freeze / Release Strategy

- 目前 Phase 1 先完成 Web / Cloud 平台換軌並通過 Release Gate，再加入 Life OS 類產品強化功能。
- Phase 1 期間可持續做產品研究、UX、資料模型與 API contract proposal，但這些候選功能不得自動變成 Phase 1 implementation blocker。
- 不採「把所有新功能一起做完再第一次上線」的策略。
- Phase 1 上線後先進入 Phase 1.5 real-use validation，以真實使用資料與 friction 決定 Phase 2 實作順序。
- 若新需求只需要未來可擴充性，優先保留 extension point，而不是提前實作完整功能。
- 若需打破 scope freeze，必須記錄明確原因，且限於不可逆架構風險、資料安全、migration correctness 或其他會讓 Phase 1 上線後難以修正的問題。

## Phase 1.5 / Phase 2 方向

Phase 1.5 先觀察：

- 首頁真正需要顯示的資訊。
- 被忽略、重複或干擾的提醒。
- Gmail / Calendar / Task 常見轉換流程。
- routine 使用頻率。
- 仍需手動跨頁完成的高摩擦流程。

Phase 2 優先候選：

1. Today Cockpit。
2. Attention Model / Focus。
3. Routine Library。
4. Global Capture。
5. Plan。
6. Review。
7. Contextual AI entry points。

詳細候選規格見 `future_product_enhancements.md`。

## life_assistant 核心定位

`life_assistant` 定位為：

> **Data + UI + API + Execution + Integration**

它負責生活資料、UI、Backend、實際 action execution、Google integrations、ChatGPT Bridge、MCP 能力、安全、權限與 audit。

## 與 omniAgent 的邊界

以下責任由獨立的 `omniAgent` 專案負責，不列入 life_assistant 的正式 roadmap / WBS：

- LangGraph Agent。
- Agent reasoning loop。
- Global Tool Registry。
- Workflow Registry。
- Agent Runtime。
- Agent Worker。
- 跨產品 multi-tool orchestration。
- 跨 Gmail、Calendar、Drive、Web、life_assistant 與其他 MCP 的全域 workflow planning / routing。

life_assistant 只維護自己的 Capability Catalog / MCP Tool Catalog。

life_assistant 可有一般 background worker，但不得把 Agent reasoning worker 與一般同步 / maintenance job 混為一談。

## ChatGPT Bridge / MCP 決策

- ChatGPT Bridge Backend 屬於 life_assistant。
- Bridge 負責 context access、proposed actions、schema validation、idempotency、permission / confirmation、action execution、result 與 audit。
- 舊版 Google Drive Bridge 可保留作相容 / fallback integration。
- 新雲端架構可逐步以 Backend API / MCP 作為主要整合面。
- ChatGPT Bridge 不等於 LangGraph，也不負責跨工具 Agent orchestration。
- omniAgent 可透過 life_assistant MCP / API 使用 life_assistant；不得繞過 Backend 直接寫 PostgreSQL。

## 既有實作保留原則

- Repository 目前已有大量 Flutter + SQLite + Android 相關實作，這些成果不刪除、不假裝不存在。
- SQLite schema 與資料不得為了轉向雲端架構而直接 drop 或清空。
- SQLite → PostgreSQL 必須有明確、可驗證的 migration 路徑。
- 現有 local-first / offline-first 行為在 migration 期間仍屬既有版本能力；新的 Web/PWA Phase 1 不要求完整離線寫入。
- 舊 Bridge schema / Drive exchange 文件可作歷史與相容性依據，但若與 `PROJECT_RULES.md`、`project_boundary.md` 或本文件衝突，以最新專案邊界為準。

## life_assistant 後續階段可考慮

- MCP / Integration API capability 擴充。
- 一般 background jobs / scheduler（不含 Agent reasoning）。
- Today / Focus / Plan / Review 等 situation-oriented UX。
- Routine Library / Global Capture。
- Contextual AI entry points。
- Android / iOS 正式封裝。
- SQLite local/offline cache 同步機制。
- Temporal / Iceberg 等 infrastructure 僅在具體 workload 證明需要時再評估。

## 明確取消的舊決策

以下舊決策不再作為目前架構基準：

- `SQLite only for v0.1 primary app data`
- `不使用 GCP backend`
- `SQLite 為 source of truth，Drive 僅為交換層`
- `原生手機 App 優先於 Web/PWA`
- `LangGraph / Global Tool Registry / Workflow Registry / Agent Runtime 屬於 life_assistant roadmap`

這些內容可作為歷史背景理解，但後續新實作應以本文件、`PROJECT_RULES.md` 與 `project_boundary.md` 的最新架構為準。
# CI/CD V2 decision — 2026-10-08

User-authorized replacement target: regional Cloud Build 2nd Gen repository
push CI trigger (`^main$`, full SHA) plus explicitly invoked full-SHA manual
Release trigger, GCP-led tests, one immutable backend image,
no-traffic Cloud Run candidate, Firebase Hosting Preview before live promotion,
all existing and true live acceptance gates. Fixed us-central1 and
CLOUD_LOGGING_ONLY. Production cutover only after actual cost comparison and
complete live gates; latest user instruction retires Actions automatic deployments,
manual recovery remains. Scheduler and shared OmniAgent Codex boundaries stay.
Status: IMPLEMENTING, not operational completion. Runbook:
`deployment_runbook.md`. Existing single-user API must enforce its owner email
allowlist; multi-owner core data separation/collaboration stays out of scope.

## CI/CD V3 replacement decision — 2026-10-08 (latest)

The user has superseded the Cloud Build-led V2 target above with the GitHub Actions + **public GHCR** design. Main pushes run complete Actions quality gates; an explicitly invoked, exact-main-SHA release builds/publishes one GHCR image and deploys Cloud Run by **immutable digest** with **0% tagged candidate**, candidate/Preview/live acceptance, controlled traffic promotion and rollback. New workflows never invoke Cloud Build or proactively write GCS/Artifact Registry; Cloud Build history remains reachable through an independent WIF read-only diagnostic GitHub Actions workflow and masked logs. Read-only WIF and deployer WIF are separate permission sets. Source of truth for detailed behavior is `ci_cd_ghcr_release_policy.md` and latest `PROJECT_RULES.md`. The V2 paragraph above is history only. **Status: APPROVED SPEC / IMPLEMENTATION NOT VERIFIED**; no runtime completion claim.

### Cloud Run V3 revision retention amendment — 2026-10-08

User-approved target changed from the earlier conversational 2-revision proposal to **the latest 10 service revisions**. The final V3 release stage prunes only unprotected, 0%-traffic, older revisions **after successful live acceptance**, with rollback/traffic/tag safeguards, post-delete readback and independent GHCR digest preservation; >10 when protected is PARTIAL, not a license for destructive cleanup. No runtime pruning has yet been performed. Canonical detail: `ci_cd_ghcr_release_policy.md` §3F. **Status: APPROVED SPEC / IMPLEMENTATION NOT VERIFIED**.

## 2026-10-09 — 台灣免費活動探索已核准的產品路線（規劃，未實作）

- 使用者指定 **Calendar #8 正式產品驗收完成後，台灣免費活動探索與報名追蹤為下一個第一優先產品項目**；排序依 `phase1_delivery_order.md`，完整規格依 `taiwan_free_events_discovery_plan.md`。
- 採階段式交付：**M0–M4 為 MVP**（14 天來源新鮮度／授權觀測、來源與資料正規化/安全、一般使用者與 admin-only UI、三項獨立個人動作、GCP Cloud Scheduler 正式切換）；**E1 第一版增強**（主辦單位追蹤、進階偏好、通知摘要與手動參與狀態管理）；**E2 第二階段**（貼連結、交通距離、電子報來源、進階個人化）。
- 第一線高價值官方 RSS、新聞稿、主辦單位及合法接入報名網站每天 **06:00、18:00 Asia/Taipei** 掃描；開放資料每日補漏，data.gov.tw 只發現來源。ChatGPT 定時掃描為過渡，**GCP 正式排程未實作/未驗收**；正式驗收完成後停用過渡任務。
- 核心結構需區分 **Event / Session / Registration Opportunity / Organizer / User Participation**；支援免費條件、不同報名窗口、待公布、候補、取消等生命週期；無來源證據的報名精確時刻不推測。
- 一般使用者自由決定通知、待辦、筆記與筆記資料夾；不因瀏覽/收藏即建立個人物件；未追蹤者不推新活動。管理來源健康只給 verified admin UID/RBAC，不另建後台。提供的 email `tommylin15@gmai.com` 疑有拼字問題，身份核實前不授權。
- 活動過期停止可操作、30 天後清理非必要內容並保留最小去重與使用者自有資料；真實 production 大量不可逆清理不因本規劃自動授權。
- 不做自動替使用者報名/付款、繞過反爬、完整票務平台或常駐 VM。MVP 的安全、授權、幂等、資料品質、真實 Google 整合、mobile/desktop 以及 runtime evidence 不可降標。
- 原有 Phase 1 11-package 完成數與 #9–#11 封板工作保留。此次優先順序變更**不是默認修改 Phase 1 Release Gate/scope freeze**；進入實作須依現有治理紀錄是否列為 release blocker。當前 **APPROVED PLAN / NOT IMPLEMENTED**。

## 2026-10-09 — 全功能 AI Router 正式政策（最新，覆蓋歷史 Codex-first）

**批准的順位**：Gemini `latest-3-flash` → Gemini `latest-3-flash-lite` → Groq → OpenRouter → 現有私有 Shared Codex（使用者所稱 Codex CLI）。每組 Gemini 由實際 API 模型清單選最多三個穩定文字候選，PostgreSQL 分別保存最後成功型號，下一輪本組優先用仍有效的該型號，失敗才在本組及後備供應商輪替。不以 preview/TTS 湊滿數量；不代表每次工作都必須呼叫五層。

遵守既有 consent、失敗/partial、model fingerprint/cache、個別 provider direct-health、Cloud Run owner identity 和 Secret 隔離；未經正式部署/E2E 不得標示已上線。**詳情以 [`ai_provider_policy.md`](ai_provider_policy.md) 為唯一正式政策**，不得在 `decisions.md` 和 `integrations.md` 複製另一份 fallback 演算法。

## 2026-10-09 — 活動探索最小資料與 Batch AI 省用量決策

Post-Calendar P0 活動探索採**公用精簡活動卡＋少量必要證據／個人選擇分離**：儲存 Event、Session、Registration Opportunity、Organizer、核心場次與報名時間／狀態、免費/資格條件、主辦來源、60–120 中文字短摘要、標籤、可合法使用的圖片 URL；不長期複製整站 HTML、圖片原始檔、完整 LLM prompt。沒有合法圖片時用 Flutter 內建主題圖示與模板資訊維持 UI 品質，詳細內容連回主辦原站。

每 12 小時 06:00／18:00 只做**來源增量掃描**，不代表執行 AI；資料未改、結構化資料能規則解析、一般使用者瀏覽或建立既有摘要筆記時，AI 呼叫應為 0。批次使用內容 hash、schema/policy fingerprint、PostgreSQL idempotency/lease/backoff 避免跨輪與併發重複，昂貴例外才採 AI。活動 UI/正式 GCP 排程仍未實作，詳見 [`taiwan_free_events_discovery_plan.md`](taiwan_free_events_discovery_plan.md)。
