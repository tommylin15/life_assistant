# 生活助理 App v0.1 — Architecture

## 1. 架構原則

- Local-first
- Offline-first for core local functions
- SQLite 為唯一 App 主資料來源
- Google 服務整合失敗時，核心本機功能仍可使用
- 外部資料透過 Adapter 隔離
- ChatGPT Bridge 不直接成為主資料來源

## 2. 建議模組

```text
Flutter App
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
│   ├── Reminder Scheduler
│   └── Bridge Coordinator
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
├── Data
│   ├── SQLite
│   ├── File Storage
│   └── Secure Storage
│
└── Integrations
    ├── Google Auth
    ├── Gmail Adapter
    ├── Calendar Adapter
    ├── Drive Bridge Adapter
    ├── Notification Adapter
    └── Speech-to-Text Adapter
```

## 3. State Management

可使用 Riverpod / Bloc / 其他成熟方案。

要求：

- UI 不直接存取 SQLite
- Repository / Use Case 分層
- 外部整合不得與 UI 強耦合
- 所有寫入需可被 Activity Log 記錄

## 4. Offline 行為

沒有網路時仍可：

- 查看與管理待辦
- 管理專案
- 管理筆記
- 管理習慣
- 管理採買
- 查看已同步行程快照
- 使用本機提醒
- 匯出資料

需要網路：

- Gmail
- Calendar 同步
- Google Drive Bridge
- Google 登入

## 5. 未來可擴充點

保留 Adapter：

- Cloud Sync Adapter
- Iceberg Export Adapter
- MCP Adapter
- OpenAI / Other AI Adapter

v0.1 不實作。
