# life_assistant — Active TODO

最後更新：2026-10-02

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### #4 — Task 8：智能整理 review UI

狀態：**PARTIAL / IN PROGRESS — design & implementation survey；product implementation NOT STARTED**。

已完成的 current-package discovery：

- 已盤點 GitHub `main` 的 Flutter route / App Shell、`IntegrationsPage`、shared `ApiClient`、Projects UI/test pattern、Warm Knowledge shared components，以及 Drive enrichment backend endpoints / schemas。
- 確認 repo 目前沒有獨立 Drive review page，也沒有 Drive-specific Flutter API facade。
- 確認現有 `IntegrationsPage` 的主要責任是 Google 授權、API 驗收與 legacy Drive Bridge ensure；智能整理 review workflow 應與授權/整合驗收 UI 分離。
- 已固定沿用 #3 provider-agnostic enrichment contract，不在 Flutter domain code 綁死單一 AI provider。

下一個 concrete gate：

- 完成 Task 8 architectural design/spec，明確定義 Drive Knowledge / 智能整理 review surface、狀態模型、資料流與錯誤/partial-success presentation。
- Design/spec 核准後才進 implementation plan 與 TDD。
- 依 Warm Knowledge Design System 實作 AI 狀態、建議檢視、接受/拒絕、consent UX 與 manual fallback。
- Related Note suggestion 只有使用者接受後才成為 authoritative Drive↔Note relation；拒絕不建立 relation。
- UI 必須清楚呈現 disabled / unavailable / succeeded / partial / failed / skipped 等狀態，不把 AI failure 包裝成 core Drive / Project failure。
- consent OFF 時不得暗示已送出內容做 AI 分析；仍保留手動 Tag / Note relationship 能力。
- 完成 Flutter tests、Analyze、Web build，以及對應 browser/mobile acceptance 後才可進下一 gate。

尚未完成：

- Task 8 written design/spec。
- implementation plan。
- product code。
- Task 8 Flutter tests / Analyze / Web build。
- Firebase deployment / production browser/mobile acceptance。

因此 #4 尚不計入 DONE；Closure progress 維持 **3/11 = 27.3%**。

## Just Closed

### #3 — Task 7：provider-agnostic AI enrichment

狀態：**DONE / PASS — backend foundation**。

封板 evidence：

- final release SHA `cd2fdcd5645a9f73141c7824b59a8349d15bb86c`。
- provider-agnostic adapter boundary、privacy/consent、stable fingerprint cache、shared Tag reuse、bounded Note candidates、accept/reject suggestion persistence、partial-success semantics 已落地。
- Alembic head `20261002_0009`；enrichment runs / Note-link suggestions persistence 已加入。
- CI #463 / run `36994280896` PASS；backend **315/315** tests PASS，Flutter / deployment-scripts PASS。
- Firebase Hosting #281 / run `36994497368` PASS。
- Deploy Cloud Run #335 / run `36994497260` PASS；migration、deploy、health/readiness、401、cloud-domain、Checklist、idempotency、Google failure-path、SQLite success/failure、image retention 全 PASS。
- Drive AI Enrichment Runtime Acceptance #3 / run `36997713417` PASS；exact release SHA / image verified；Cloud Run execution `life-assistant-drive-ai-acceptance-52fj9` PASS。
- 詳細 checkpoint：`doc/drive_ai_enrichment_checkpoint_v0_1.md`。
- 本包不宣稱 concrete external-AI provider 已接通；repo 尚無核准 vendor credential/config contract，default resolver 維持 disabled/unavailable degraded mode。真實 provider / Drive production delivery 留在後續 integration package。

## Next

1. #5 — Task 9：Drive Knowledge production delivery + acceptance。
2. #6–#9 — Habits / Shopping / Calendar / Activity + Integrations productization。
3. #10 — Integration / foundation tail closure。
4. #11 — Phase 1 final Release Gate / 封板 checkpoint。

## Non-blocking backlog

以下仍需完成，但只有在成為直接 dependency 或進入對應工作包時才提升優先級：

- Attachment central storage/reference strategy。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。
- Concrete AI provider adapter / deployment config；接入時補 provider/model-aware cache invalidation contract 與 external-provider integration evidence。

## Product DONE 規則

使用者功能至少要依工作包需求具備：

1. implementation
2. tests
3. CI
4. deployment
5. runtime / integration
6. UI entry + 可操作 flow
7. mobile / desktop UX acceptance

Backend-only PASS 可標 foundation PASS，但不能等同產品功能 DONE。
