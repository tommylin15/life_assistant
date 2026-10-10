# Life 活動精選池 — 唯一現行流程（2026-10-10）

**DESIGN APPROVED / BACKEND + FLUTTER SOURCE IMPLEMENTED; CHATGPT CONNECTOR & LIVE DEPLOYMENT NOT VERIFIED.** This document supersedes all former MoC/TDX/Queue plans. Historical details are in Git history and doc/archive; do not restart collectors.

**本文件只定義精選資料如何進池，不再放使用者側分類／待辦／日曆規格。使用者功能唯一規格：[curated_activity_user_features.md](curated_activity_user_features.md)。**

## Only active pipeline

ChatGPT Chat（自主搜尋、篩選和去重） → Life 認證 API 接收精選活動 → PostgreSQL 精選池 → Flutter 用戶自行瀏覽。

Life 不做前置文化部/TDX/官網 Excel 資料抓取，**不建立／不讀取／不處理 Queue**，不部署活動擷取 Job，不在伺服端進行第二次 AI 分析或正式推薦／報名審核。ChatGPT 自行管理來源與模型；Life 自己的 Drive AI Provider 路由無關。

## Minimum Life scope

- Authenticated bounded POST of ChatGPT-curated activity records: stable official/original HTTPS link, title, optional city/date/category/fee/summary, unknown fields explicitly unknown. Caller cannot assert official validity or booking availability on behalf of Life.
- Backend validates payload size, role/capability, HTTPS source safety, dedup stable identity, idempotent retry and database transaction. Do not fetch attacker-supplied URLs or add any external crawler.
- Additive PostgreSQL curated-pool table and a GET API for signed-in user viewing with basic filters and original source link. Users decide for themselves; minor factual ambiguity is acceptable but cannot be presented as a verified fact.
- Actual ChatGPT Chat scheduled task/API connector credential flow must be proved in real E2E. Prior '台灣活動探索' ChatGPT task writing Sheets/Queue has been disabled; no new task is activated by this design.
- Keep prior migrations 0011–0014/legacy catalog only for backward-compatible database history; no destructive production drop. Existing Cloud Run Job still exists as external resource, but new Python source-job entrypoint is inert and former GitHub cron workflows are removed.

## What is cancelled

MoC, TDX, official-site workbook, source registry, event discovery/normalization source adapters, scheduled source scanner, Queue/claim/lease/ACK, source Job image pinning, M0–M4, source acceptance observations and extra publication gates. The 14-day source-observation failure is historical evidence and **not a blocker** of the new direct flow.

## Validation before DONE

Real PostgreSQL tests of safe input, idempotent upsert, stable dedup, unauthorized access, failure rollback; Flutter card empty/error/unknown states; GitHub CI / guarded V3 deploy; owner/runtime DB readback; real ChatGPT connector/Tasks run. No current assertion that this E2E already works.
