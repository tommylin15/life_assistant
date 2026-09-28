# 生活助理 App v0.1 — 開發進度摘要

最後更新：2026-09-28

目前狀態：**Phase 1 = PARTIAL。**

> 本檔只提供人類可快速閱讀的 rollup，不再重複維護所有 run id、revision、job execution 與逐項 evidence。最新 PASS / FAIL / NOT VERIFIED 與 release evidence 請以 `acceptance.md` 為準；目前開發先後順序請以 `phase1_delivery_order.md` 為準。

## 已建立的主要平台能力

目前 `main` 已具備並經不同層級驗證的核心基線包括：

- Firebase Hosting → Flutter Web / PWA。
- Cloud Run FastAPI Backend。
- PostgreSQL operational source of truth。
- Google identity / protected API baseline。
- Task Cloud CRUD + Web interaction path。
- Project Cloud CRUD、relation guard 與 Gmail → Project。
- Note / Habit / Shopping / Template Cloud API + persistence baseline。
- Gmail metadata + Gmail → Task / Calendar / Project。
- Calendar read/create/update/delete API。
- Drive Bridge ensure compatibility path。
- unified error envelope + request id。
- execution / activity log、failure / partial-success semantics。
- SQLite → PostgreSQL deterministic backfill tooling與 synthetic success/failure runtime gate。
- Calendar destructive confirmation baseline。
- action-id idempotency implementation baseline。
- shared immutable backend image / Artifact Registry cleanup strategy baseline。

上述「平台能力存在」不等於所有產品 UI 已完成；各項真正完成狀態仍以 `acceptance.md` 的 evidence 層級為準。

## 目前最重要的缺口

### UI-critical foundation

1. action-id idempotency release/runtime evidence 收尾。
2. authorization / minimum-permission + destructive/sensitive policy 核心版。
3. Checklist Cloud 主線。

這三項完成後，正式切入 UI vertical slice，不等待其他底層 backlog 全部清零。

### Product UI

目前 Web 使用者介面明顯落後 Backend domain 能力。接下來的主要產品交付為：

- App Shell / responsive navigation。
- Task 完整 UX：日期、priority、reminder、tags、project、checklist、edit flow。
- Project UX。
- Notes + full-text search。
- Habits。
- Shopping。
- Calendar 一般使用者 UI。
- Activity / Integrations 的可理解呈現。

產品功能只有在 UI entry、操作 flow、mobile/desktop UX acceptance 與 backend/runtime evidence 都完整時，才可標示 DONE。

## 不再阻塞 UI 的尾端項目

以下仍保留在 Phase 1 / integration backlog，但不再因它們未完成而延後主要 UI，除非成為直接 dependency：

- Bridge / MCP 完整 versioned contract 與完整 policy/schema evidence。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- Attachment central storage/reference strategy（在附件 UI 前完成）。
- 真實歷史 SQLite migration；目前缺實際 legacy source file 時維持 NOT VERIFIED。
- Artifact Registry cleanup 的最終 physical inventory evidence。

## 文件與 evidence 分工

- `phase1_delivery_order.md`：目前執行順序。
- `todo.md`：active / next backlog。
- `acceptance.md`：逐項 completion truth 與 release evidence。
- `release_checklist.md`：Phase 1 final release gate。
- `wbs.md`：scope decomposition，不代表排程。
- 歷史 batch progress 文件：保留稽核價值，不再當 current status。

## 下一步

依 `phase1_delivery_order.md`：

1. 收尾 idempotency evidence。
2. policy 核心版。
3. Checklist Cloud。
4. App Shell → Task 完整 UX → Project UX。

之後再逐一產品化其他已完成 Cloud domain。
