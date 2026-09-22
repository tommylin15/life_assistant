# life_assistant 專案邊界

最後更新：2026-09-22

## 1. 核心定位

`life_assistant` 是個人生活資料與實際執行系統：

> **Data + UI + API + Execution + Integration**

它負責保存生活資料、提供使用介面、執行經授權的操作、整合外部服務，並向 ChatGPT 或其他 Agent 提供安全且版本化的介面。

它不是通用 Agent orchestration 平台。

## 2. life_assistant 內的正式責任

- Flutter Web / PWA 使用者介面。
- FastAPI Backend。
- PostgreSQL operational source of truth。
- Tasks、Projects、Notes、Habits、Shopping、Calendar reference、Activity / execution records 等 domain data。
- Google Login、Gmail、Google Calendar、Google Drive 等 integration。
- ChatGPT Bridge Backend。
- MCP Server 或等價的 Integration API。
- life_assistant 自己的 Capability Catalog / MCP Tool Catalog。
- action schema validation、idempotency、permission / confirmation policy。
- 實際 action execution 與 execution result。
- Activity / execution log。
- migration、backup / restore、security、observability。
- 不含 AI reasoning 的一般 background jobs，例如同步、通知、migration、export、backup、maintenance。

## 3. ChatGPT Bridge Backend

ChatGPT Bridge Backend **保留在 life_assistant**。

它的目的不是實作 LangGraph，而是讓 ChatGPT 或其他授權 client 安全地：

1. 讀取允許分享的 life_assistant context。
2. 提出 proposed actions。
3. 經 schema、權限與 policy 驗證。
4. 在需要時由使用者確認。
5. 由 life_assistant 執行實際操作。
6. 回傳 action result 並寫入 audit / execution log。

舊版 Google Drive Bridge 可保留作相容或 fallback integration；新雲端架構下，主要能力可逐步由 Backend API / MCP 提供。

## 4. MCP / Capability Catalog

life_assistant 可以提供自己的 MCP tools，例如：

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

life_assistant 只維護自己能力的 schema、版本、permission、risk 等 metadata；這是 **Capability Catalog**，不是跨產品的 Global Tool Registry。

## 5. 明確不屬於 life_assistant

以下由獨立的 `omniAgent` 專案負責，不列入 life_assistant 的正式 roadmap / WBS：

- LangGraph Agent。
- Agent reasoning loop。
- Global Tool Registry。
- Workflow Registry。
- Agent Runtime。
- Agent Worker。
- 跨 Gmail、Calendar、Drive、Web、life_assistant 與其他 MCP 的 multi-tool orchestration。
- 通用型 multi-agent platform。
- 跨產品全域 tool routing、workflow planning、retry / resume orchestration。

## 6. Worker 邊界

life_assistant 仍可有一般 background worker，例如：

- Calendar / Gmail sync。
- notification dispatch。
- migration job。
- export / backup。
- maintenance job。

這類 worker 不做 Agent reasoning。

如果 worker 執行 LangGraph state、reason → choose tool → execute → observe → continue / finish 等 Agent loop，則屬於 omniAgent。

## 7. 呼叫關係

### ChatGPT 直接使用 life_assistant

```text
ChatGPT
    ↓ MCP / Bridge API
life_assistant Backend
    ↓ validation / permission / policy
PostgreSQL / Google integrations
    ↓
Activity / execution log
```

### omniAgent 使用 life_assistant

```text
omniAgent / LangGraph
    ↓ Global Tool Registry
life_assistant MCP
    ↓
life_assistant Backend
    ↓
PostgreSQL / integrations
```

omniAgent 不應繞過 life_assistant Backend 直接寫入 life_assistant PostgreSQL。

## 8. Source of Truth 與治理

- PostgreSQL 是 life_assistant 的 operational source of truth。
- omniAgent 不取代 life_assistant 主資料來源。
- destructive / sensitive action 最終仍需通過 life_assistant 的 auth、permission、policy 與 validation。
- AI 建議不等於已執行；只有 life_assistant 回傳成功結果後才可視為實際完成。
- partial success 必須明確呈現，不得包裝成 full success。

## 9. 專案完成條件互相獨立

life_assistant 完成不需要等待 omniAgent 完成。

life_assistant 的完成條件是自身 UI、Backend、PostgreSQL、integrations、Bridge / MCP、execution、安全與 logging 可以獨立運作。

omniAgent 則可在之後透過版本化 MCP / API contract 使用 life_assistant 作為其中一個 execution provider。
