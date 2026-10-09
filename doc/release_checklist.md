# 生活助理 App v0.1 — Release Checklist

最後更新：2026-10-09（新增 Calendar #8 可信 rollup；下列未勾選 Final Gate 不等於通過）

> 本清單定義目前 **Phase 1 Web / Cloud Release Gate**。尚未完成的項目維持未勾選；完成判定需有實際 tests / CI / deployment / runtime evidence。

## Latest checkpoint — 2026-10-09（優先於下方 2026-10-07 歷史快照）

- **Completed packages：8/11 = 72.7%；#8 Calendar DONE / PASS**，完成依據 [CI 37882690249](https://github.com/tommylin15/life_assistant/actions/runs/37882690249) → [V3 37882875014](https://github.com/tommylin15/life_assistant/actions/runs/37882875014) → [Firebase 37885328134](https://github.com/tommylin15/life_assistant/actions/runs/37885328134) → [真實 Google read/list 37885330178](https://github.com/tommylin15/life_assistant/actions/runs/37885330178) → [Calendar UI 37885544932](https://github.com/tommylin15/life_assistant/actions/runs/37885544932)，全數為 `5c8d2fca8c9b17f6e4a013c02ba5d2b9fba86aa7`；Bootstrap 37882690327 PASS。
- 原 Phase 1 #9、#10、#11 **NOT STARTED**；Post-Calendar P0 台灣免費活動 M0 按核准優先序先行，尚 **NOT IMPLEMENTED**；Phase 1 全案仍 PARTIAL。
- Google write-side real account E2E 與獨立跨功能 Drive Knowledge model/provider regression 不能由 Calendar mocked UI 或其他 Gate 偷渡；狀態另看 `acceptance.md`。
- 下列舊 **2026-10-07 checkpoint** 是歷史證據，不是現行完成分子或本輪宣稱。保留未勾選最終 Release Gate，不因工作包 #8 通過而批量勾選。

## Historical checkpoint — 2026-10-07

本清單仍是 **Phase 1 final gate**，未勾選項不因單一工作包通過而自動變成完成。當前 rollup：

- Phase 1 closure：**5/11 = 45.5%，PARTIAL**。
- Just closed：**#5 Task 9 — Drive Knowledge production delivery + acceptance，DONE / PASS**；下一包 **#6 Habits，NOT STARTED**。
- release SHA `2d08118a13c71c6fec97e8bfba0857b861eefd1e`：CI #551、Cloud Run #423、Firebase #369、Notes UI run `37568672137`、Drive Knowledge #47 final mandatory gate PASS。
- Picker developer key / app id、三個 live AI provider、real Picker-selected Drive fixture 與 production UI 已 PASS；完整 evidence 見 `acceptance.md`、`integrations.md`。
- CI/CD stuck-recovery hardening（heartbeat / hard timeout / diagnostics / workflow-run concurrency isolation）已有 production runtime evidence PASS。
- 因此本文件不得被解讀為「CI 綠燈即可 release complete」；其餘 #6–#11 closure packages 仍需逐包完成，以下 Phase 1 final checklist 不因 Task 9 PASS 而自動勾選。

## 1. Web / PWA

- [ ] Flutter Web production build 成功
- [ ] Firebase Hosting dev/test 可存取
- [ ] 手機瀏覽器主要流程可用
- [ ] 桌面瀏覽器主要流程可用
- [ ] Responsive layout 無重大阻斷
- [ ] Loading / Empty / Error / Data state 可辨識
- [ ] PWA baseline 驗證（若當期設定支援）

## 2. Backend / Cloud Run

- [ ] FastAPI Backend 可部署到 Cloud Run dev/test
- [ ] health / readiness 或等價 runtime check 可驗證
- [ ] Backend error response contract 一致
- [ ] environment / secret handling 已驗證
- [ ] production-sensitive secret 不進 repo /一般 log
- [ ] runtime log 可追溯請求與錯誤

## 3. PostgreSQL / Data

- [ ] PostgreSQL schema 建立成功
- [ ] Core CRUD persistence 驗證
- [ ] transaction / failure path 驗證
- [ ] 前端未直接連 PostgreSQL
- [ ] operational source of truth 明確為 PostgreSQL
- [ ] Activity / execution log 可保存重要操作

## 4. SQLite → PostgreSQL Migration

- [ ] 既有 SQLite 原始資料保留
- [ ] export 可執行
- [ ] import 可執行
- [ ] migration 可安全重跑
- [ ] 重跑不造成 duplicate
- [ ] row count 可核對
- [ ] 關鍵 relation 可核對
- [ ] migration failure 不破壞 SQLite
- [ ] success / partial success / failure 可區分
- [ ] 有實際 runtime migration evidence

## 5. Core Product Flows

- [ ] Dashboard
- [ ] Tasks
- [ ] Calendar
- [ ] Gmail conversion
- [ ] Projects
- [ ] Notes / Markdown
- [ ] Habits
- [ ] Shopping
- [ ] Attachments / storage reference baseline
- [ ] Activity / Execution Log
- [ ] Integrations / Connections
- [ ] Settings

## 6. Google Integrations

- [ ] Google Web Sign-In / Backend token flow
- [ ] Calendar read
- [ ] Calendar create
- [ ] Calendar update
- [ ] Calendar delete
- [ ] Gmail metadata / snippet
- [ ] Gmail → Task
- [ ] Gmail → Calendar
- [ ] Gmail → Project
- [ ] reconnect / revoke / failure path 可追蹤
- [ ] integration failure 不破壞 PostgreSQL 主資料

## 7. ChatGPT Bridge / MCP

- [ ] Bridge / MCP entrypoint 可用
- [ ] versioned schema / contract 明確
- [ ] Capability Catalog / MCP Tool Catalog baseline
- [ ] context read path 經 Backend
- [ ] proposed action schema validation
- [ ] permission / risk / confirmation policy
- [ ] request_id + action_id idempotency
- [ ] action execution 由 life_assistant Backend 執行
- [ ] action result 可回傳
- [ ] execution result 寫入 Activity / execution log
- [ ] partial success 不呈現為 full success
- [ ] legacy Drive Bridge 如保留，明確標示 fallback / compatibility

## 8. Security / Governance

- [ ] authentication / authorization baseline
- [ ] minimum permission baseline
- [ ] OAuth token / secret 安全儲存
- [ ] sensitive log filtering
- [ ] destructive / sensitive action confirmation
- [ ] export 不包含 secrets
- [ ] audit trail 可追蹤重要 mutation
- [ ] life_assistant / omniAgent boundary 未被繞過

## 9. Tests / CI

- [ ] Flutter analyze 通過或已明確記錄非阻斷 info
- [ ] Flutter tests 通過
- [ ] Backend tests 通過
- [ ] API tests 通過
- [ ] migration tests 通過
- [ ] Calendar integration tests 通過
- [ ] Gmail integration tests 通過
- [ ] Bridge / MCP tests 通過
- [ ] CI status 可追溯到 release commit

## 10. Observability / Recovery

- [ ] 重要 external API failure 有 log
- [ ] important mutation 有 execution log
- [ ] failure / partial success / success 狀態可區分
- [ ] failure recovery runbook 可用
- [ ] backup / export baseline 可用
- [ ] deployment / rollback 或等價可逆處理方式已記錄

## 11. Release Evidence

以下 evidence 至少需保留：

- [ ] release commit / version
- [ ] CI result
- [ ] Flutter Web build result
- [ ] Firebase Hosting deployment result
- [ ] Cloud Run deployment result
- [ ] PostgreSQL runtime persistence evidence
- [ ] migration runtime evidence
- [ ] Google integration evidence
- [ ] Bridge / MCP validation evidence

## 12. Explicitly Deferred — 不阻塞 Phase 1

- [ ] Android release build — deferred
- [ ] iOS release build — deferred
- [ ] App Store / Play Store release — deferred
- [ ] full offline-first sync — deferred
- [ ] SQLite live local-cache bi-directional sync — deferred
- [ ] Today Cockpit — Phase 2
- [ ] Attention Model / Focus — Phase 2
- [ ] Routine Library — Phase 2
- [ ] Global Capture full version — Phase 2
- [ ] Plan / Review — Phase 2
- [ ] Contextual AI entry points — Phase 2
- [ ] People / relationship context — later candidate

> Deferred 項目未勾選不代表 Phase 1 Release Gate 失敗；它們只是用來明確記錄未納入本次上線範圍。

## 13. Final Release Decision

CI/CD V2 additionally requires:

- [ ] Real main Push CI PASS; no automatic runtime/Live deployment.
- [ ] Full-SHA manual Release Ready review/tests/contracts PASS.
- [ ] Idempotent migration and no-traffic candidate PASS.
- [ ] Firebase Preview and separate exact Live SHA acceptance PASS.
- [ ] Existing runtime/UI/Google/provider/Shared Codex mandatory gates PASS.
- [ ] Scheduler unchanged; Cloud Run Jobs/image references read back.
- [ ] Measured cost comparison and recovery evidence recorded.
- [ ] Legacy automatic deployment retired; manual diagnostics preserved.

Phase 1 只有在 `acceptance.md`、本 Release Checklist、CI、deployment、runtime、migration、integration evidence 一致時，才可標記為完成。

**文件更新、程式碼存在、單一測試通過或 partial success 均不得單獨宣告 release complete。**
