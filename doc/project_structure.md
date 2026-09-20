# 生活助理 App v0.1 — Flutter Project Structure

## 1. 目標

確保 Flutter 專案在功能增加後仍維持清楚邊界，避免 UI、SQLite、Google API、同步與 Bridge 邏輯混在一起。

採用：

- Feature-first
- Clean-ish Architecture
- Repository + Use Case
- Adapter 隔離外部服務
- UI 不直接呼叫 SQLite / Google API
- Domain 不依賴 Flutter framework

## 2. 建議目錄

```text
lib/
├── app/
│   ├── app.dart
│   ├── router/
│   ├── theme/
│   └── bootstrap/
│
├── core/
│   ├── constants/
│   ├── errors/
│   ├── logging/
│   ├── utils/
│   ├── extensions/
│   ├── widgets/
│   ├── storage/
│   └── platform/
│
├── features/
│   ├── dashboard/
│   │   ├── domain/
│   │   ├── application/
│   │   └── presentation/
│   ├── tasks/
│   ├── calendar/
│   ├── gmail/
│   ├── projects/
│   ├── notes/
│   ├── habits/
│   ├── shopping/
│   ├── templates/
│   ├── attachments/
│   ├── activity_log/
│   ├── search/
│   ├── notifications/
│   ├── voice_input/
│   ├── folder_sync/
│   ├── chatgpt_bridge/
│   ├── backup/
│   ├── security/
│   └── settings/
│
├── data/
│   ├── db/
│   │   ├── app_database.dart
│   │   ├── migrations/
│   │   ├── dao/
│   │   └── models/
│   ├── secure_storage/
│   └── file_storage/
│
└── integrations/
    ├── google_auth/
    ├── gmail/
    ├── calendar/
    ├── drive/
    ├── speech/
    └── notifications/
```

## 3. Feature 內部結構

```text
feature/
├── domain/
│   ├── entities/
│   ├── value_objects/
│   └── repositories/
├── application/
│   ├── use_cases/
│   ├── services/
│   └── state/
└── presentation/
    ├── pages/
    ├── widgets/
    └── controllers/
```

## 4. Repository 責任

Repository interface 放在 domain。

實作放在 feature 的 infrastructure/data layer 或 integration adapter。

範例：

```text
TaskRepository
├── getTasks()
├── createTask()
├── updateTask()
└── deleteTask()
```

UI 不得直接操作 DAO。

## 5. Use Case

每個可追蹤的重要動作都用 use case 包裝，例如：

- CreateTask
- CompleteTask
- ConvertGmailToTask
- CreateCalendarEvent
- SyncWorkspace
- ImportBridgeActions
- RestoreBackup

Use case 負責：

- 驗證
- repository orchestration
- activity log
- error mapping

## 6. Service

Service 用於跨 feature 或外部能力：

- RuleEngine
- ReminderScheduler
- FolderSyncEngine
- BridgeCoordinator
- BackupService
- SearchService

避免建立過大的 God Service。

## 7. Adapter

外部服務一律經 adapter：

```text
GoogleCalendarAdapter
GmailAdapter
GoogleDriveAdapter
SpeechToTextAdapter
NotificationAdapter
```

未來可替換實作，而不改 domain。

## 8. State Management

可選 Riverpod / Bloc。

要求：

- State 不直接包含 raw API client
- 非同步錯誤有統一表示
- loading / empty / error / data 狀態一致
- feature state 不互相隨意引用

## 9. Dependency Rule

```text
Presentation
    ↓
Application
    ↓
Domain

Data / Integrations
    ↑
implement Domain interfaces
```

Domain 不依賴 Flutter、SQLite、Google SDK。

## 10. 禁止事項

- Page 直接寫 SQL
- Widget 直接呼叫 Google API
- 全域 mutable singleton 到處使用
- 同一 model 同時代表 DB row / API response / domain entity
- sync engine 直接操作 UI state
- Bridge JSON 直接 deserialize 後執行，未經 validator
