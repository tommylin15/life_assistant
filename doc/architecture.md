# 生活助理 App v0.1 — Architecture

## 1. 目前正式目標架構

```text
Firebase Hosting
        ↓
Flutter Web / PWA
        ↓
Cloud Run — FastAPI Backend
        ↓
PostgreSQL
```

Phase 1 先以 Web/PWA 為主要交付方式，Android / iOS 原生安裝包延後。

`life_assistant` 的核心定位是：

> **Data + UI + API + Execution + Integration**

它不是通用 Agent orchestration 平台。

## 2. 架構原則

- Flutter / Dart 繼續作為前端主技術。
- Firebase Hosting 負責 Flutter Web / PWA 靜態資源發布。
- FastAPI 部署於 Cloud Run，作為前端主要後端入口。
- PostgreSQL 作為新的 operational source of truth。
- 前端不得直接連 PostgreSQL。
- Google、Drive、通知、語音與其他外部服務透過 adapter / connector 隔離。
- 現有 SQLite 保留為既有版本 migration source；未來若保留原生 App，可作 local/offline cache。
- ChatGPT Bridge Backend 與 life_assistant MCP / Integration API 屬於本專案。
- LangGraph、Global Tool Registry、Workflow Registry、Agent Runtime、Agent Worker 與跨系統 Agent orchestration 不屬於本專案，由獨立 `omniAgent` 負責。

## 3. 建議模組

```text
Flutter Web / PWA
│
├── Presentation
│   ├── Dashboard
│   ├── Tasks
│   ├── Calendar
│   ├── Projects
│   ├── Notes
│   ├── Shopping
│   ├── Habits
│   ├── Logs
│   └── Settings
│
├── Application
│   ├── Use Cases
│   ├── Rule Engine
│   ├── Search
│   └── API Coordination
│
├── Domain
│   ├── Item
│   ├── Project
│   ├── Note
│   ├── Habit
│   ├── ShoppingItem
│   ├── CalendarEventRef
│   ├── ActivityLog
│   └── Template
│
└── Infrastructure
    ├── API Client
    ├── Local Cache（optional）
    └── Secure Browser / Platform Storage

Cloud Run — FastAPI
│
├── API Routes
├── Auth / Permission
├── Application Services
├── Repositories
├── PostgreSQL Data Access
├── Google / External Integrations
├── ChatGPT Bridge Backend
├── MCP / Integration API
├── Capability Catalog
├── Background Jobs（non-agent）
└── Logging / Execution Records
```

## 4. State Management

前端可使用 Riverpod / Bloc / 其他成熟方案。

要求：

- UI 不直接存取 PostgreSQL、SQLite DAO 或 Google API。
- Repository / Use Case 分層。
- 外部整合不得與 UI 強耦合。
- 所有重要寫入需可被 Activity / execution log 記錄。

## 5. Web / PWA 行為

Phase 1 以網路連線為前提完成主要功能。

可逐步加入：

- PWA 安裝至手機主畫面。
- Service Worker / cache 改善載入體驗。
- 必要的唯讀快取或短期 local cache。

完整離線寫入與衝突同步不是第一階段必要條件；若未來需要原生 App offline-first，再以 SQLite 作 local cache 並設計同步協議。

## 6. SQLite 與 PostgreSQL 的關係

目前 repository 既有 SQLite schema 與大量功能仍需保留並可驗證。

目標狀態：

```text
Existing SQLite
    ↓ migration
PostgreSQL
    ↓
FastAPI
    ↓
Flutter Web / PWA
```

SQLite 不再是新架構的中央 source of truth，但在 migration 完成前仍是既有資料的有效來源。

## 7. ChatGPT Bridge 與 MCP

ChatGPT Bridge Backend 留在 life_assistant，負責：

- context export / read model。
- proposed action schema。
- schema validation。
- idempotency。
- permission / confirmation policy。
- action execution。
- action result / audit log。

life_assistant 可提供 MCP Server 或等價 Integration API，讓 ChatGPT 或 omniAgent 使用 life_assistant 能力。

life_assistant 只維護自己的 Capability Catalog；不維護跨產品 Global Tool Registry。

## 8. Background Worker 邊界

life_assistant 可有不含 AI reasoning 的一般 background jobs，例如：

- Calendar / Gmail sync。
- notification dispatch。
- migration / export / backup。
- maintenance。

Agent Worker、LangGraph state machine、reason → choose tool → execute → observe loop 屬於 omniAgent。

## 9. 與 omniAgent 的責任邊界

```text
omniAgent / LangGraph
        ↓ Global Tool Registry
life_assistant MCP / Integration API
        ↓
life_assistant FastAPI
        ↓ validation / permission / policy
PostgreSQL / Google integrations
```

omniAgent 不應直接寫入 life_assistant PostgreSQL。

詳細規則見 `project_boundary.md`。

## 10. 後續可擴充點

life_assistant 後續可擴充：

- MCP capability coverage。
- Bridge Backend 能力。
- 一般 background jobs。
- Android / iOS packaging。
- SQLite local/offline cache。

以下不再列為 life_assistant roadmap：

- LangGraph。
- Global Tool Registry。
- Workflow Registry。
- Agent Runtime。
- Agent Worker。
- 通用型 multi-agent orchestration。

除非有具體 workload 證明需求，暫不優先導入 Temporal、Iceberg 或其他高複雜基礎設施。
