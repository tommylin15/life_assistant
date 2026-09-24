# 生活助理 App v0.1 — Release Checklist

最後更新：2026-09-24

> 本清單定義目前 **Phase 1 Web / Cloud Release Gate**。尚未完成的項目維持未勾選；完成判定需有實際 tests / CI / deployment / runtime evidence。

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

Phase 1 只有在 `acceptance.md`、本 Release Checklist、CI、deployment、runtime、migration、integration evidence 一致時，才可標記為完成。

**文件更新、程式碼存在、單一測試通過或 partial success 均不得單獨宣告 release complete。**
