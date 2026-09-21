# 生活助理 App v0.1 — Project Structure

## 1. 目標

確保 Flutter Web / PWA 與 FastAPI Backend 在功能增加後仍維持清楚邊界，避免 UI、資料庫、Google API、同步與 Bridge 邏輯混在一起。

採用：

- Flutter 前端 Feature-first
- Clean-ish Architecture
- Repository + Use Case
- Adapter / API Client 隔離外部服務
- UI 不直接呼叫 PostgreSQL / SQLite / Google API
- Domain 不依賴 Flutter framework 或特定 DB implementation

## 2. Flutter 前端建議目錄

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
│   ├── api/
│   └── platform/
│
├── features/
│   ├── dashboard/
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
│   ├── chatgpt_bridge/
│   ├── backup/
│   ├── security/
│   └── settings/
│
└── infrastructure/
    ├── api_client/
    ├── auth/
    ├── local_cache/
    └── secure_storage/
```

既有 `data/db`、SQLite DAO、migrations 等程式碼在遷移完成前保留，不強制一次重構或刪除。

## 3. Backend 建議目錄

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── repositories/
│   ├── db/
│   │   ├── models/
│   │   └── migrations/
│   ├── integrations/
│   ├── auth/
│   ├── logging/
│   └── settings/
└── tests/
```

實際目錄可依現有 repository 狀態調整，但需維持責任邊界。

## 4. Feature 內部結構

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

## 5. Repository 責任

Repository interface 放在 domain。

前端 repository implementation 通常透過 Backend API；Backend repository implementation 負責 PostgreSQL 或外部 integration。

UI 不得直接操作 DAO、SQL 或 Google API。

## 6. Use Case

每個可追蹤的重要動作都用 use case 包裝，例如：

- CreateTask
- CompleteTask
- ConvertGmailToTask
- CreateCalendarEvent
- ImportBridgeActions
- RestoreBackup

Use case 負責：

- 驗證
- repository orchestration
- activity / execution log
- error mapping

## 7. Adapter / Integration

外部服務一律經 adapter / connector：

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

- State 不直接包含 raw API client。
- 非同步錯誤有統一表示。
- loading / empty / error / data 狀態一致。
- feature state 不互相隨意引用。

## 9. Dependency Rule

```text
Presentation
    ↓
Application
    ↓
Domain

Infrastructure / API Client / Integrations
    ↑
implement Domain interfaces
```

Domain 不依賴 Flutter、PostgreSQL、SQLite、Google SDK 或 FastAPI。

## 10. 禁止事項

- Page 直接寫 SQL。
- Widget 直接呼叫 Google API。
- Flutter Web 直接連 PostgreSQL。
- 全域 mutable singleton 到處使用。
- 同一 model 同時代表 DB row / API response / domain entity。
- sync engine 直接操作 UI state。
- Bridge JSON 直接 deserialize 後執行，未經 validator。
