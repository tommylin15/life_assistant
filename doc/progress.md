# 生活助理 App v0.1 — 開發進度

最後更新：2026-09-22
目前狀態：**flutter analyze 0 error（68 info）、flutter test 7/7 通過；P2 Polish 全部完成；等待 Android SDK 安裝後進行實機驗收**

## 狀態定義

- `已實作`：已有程式碼與畫面；不代表已通過測試。
- `已備妥測試`：測試案例已寫入，但依目前工作約定尚未執行。
- `待驗證`：需執行 analyze、test、裝置或外部服務驗收。
- `待外部設定`：需要 Android SDK／簽章或 macOS/Xcode 等環境資料。

## 2026-09-22 完成

### permissions status service

- 新增 `lib/application/permissions_status_service.dart`：封裝 `checkAll()` / `request()` / `openSettings()`，覆蓋通知、相機、麥克風、儲存空間四個權限。
- `providers.dart` 加入 `permissionsProvider`。
- `app.dart` 加入 `PermissionsPage`：列出各權限狀態（已授權 / 未授權），未授權時顯示「授權」按鈕，拒絕後自動跳系統設定；SettingsPage 加入入口。

### CI（GitHub Actions）

- 新增 `.github/workflows/ci.yml`：push / PR 到 main 時自動執行 `flutter pub get` → `flutter analyze` → `flutter test`。
- Flutter 版本固定 3.47.3，`--fatal-infos=false` 避免既有 style info 阻斷 CI。

### todo.md 補勾

- `[x] 建立 permissions status service`
- `[x] 建立 test baseline / CI`

### Accessibility pass

- `NavigationBar` destinations 補 `selectedIcon`。
- `TaskTile` Checkbox 加 `semanticLabel`。
- `TaskTile` 編輯按鈕加 `tooltip`。
- `Busy` 加 `semanticsLabel: '載入中'`。
- `Message` 用 `Semantics(label:)` 包住，子節點加 `ExcludeSemantics`。
- `LockGate` PIN 欄位加 `autofillHints`。
- `CalendarIntegrationPage` 刪除行程按鈕加 `tooltip`。
- `WorkspaceEditorPage` 三個 AppBar 按鈕補 tooltip。

### todo.md 補勾（Accessibility / Empty states / Templates）

- `[x] Templates`（移除「另存入口待補」備註）
- `[x] Empty states`
- `[x] Accessibility`

- `NavigationBar` 五個 destination 補上 `selectedIcon`，提供視覺選中回饋。
- `TaskTile` Checkbox 加 `semanticLabel`，TalkBack / VoiceOver 朗讀「任務標題，已完成／未完成」。
- `TaskTile` 編輯按鈕加 `tooltip: '編輯待辦'`。
- `Busy` widget 的 `CircularProgressIndicator` 加 `semanticsLabel: '載入中'`。
- `Message` widget 用 `Semantics(label: text)` 包住整體，圖示與文字子節點各加 `ExcludeSemantics`，避免螢幕閱讀器重複朗讀。
- `LockGate` PIN 欄位加 `autofillHints: [AutofillHints.password]`。
- `CalendarIntegrationPage` 刪除行程 `IconButton` 加 `tooltip: '刪除行程'`。
- `WorkspaceEditorPage` 預覽切換、儲存、刪除三個 AppBar `IconButton` 補 tooltip。

### todo.md 補勾

- `[x] Templates`（移除「另存入口待補」備註）
- `[x] Empty states`
- `[x] Accessibility`

## 2026-09-21 完成

### flutter analyze 修正（0 error、0 warning）

- `app.dart`：`ConsumerState.build` 移除多餘的 `WidgetRef` 參數。
- `app_lock.dart`：`local_auth v3` API 改用 `persistAcrossBackgrounding`，移除 `AuthenticationOptions`。
- `feature_pages.dart` + `attachment_service.dart`：`file_picker v11` 改為靜態方法 `FilePicker.pickFiles()` / `FilePicker.getDirectoryPath()`。
- `folder_sync_engine.dart`：`Stream.isNotEmpty` 不存在，改為 `.any((_) => true)`；`jsonEncode(_extensions)` 改為 `.toList()`。
- `safe_logger.dart`：Dart 不支援 `(?i)` regex inline flag，改用 `caseSensitive: false`。
- `backup_service.dart`：`sqlite3.Database.dispose()` 改為 `close()`，移除 unused drift import，`sqlite3` 加入 pubspec.yaml dependencies。
- `google_integration_service.dart`：移除 unused `_uuid` field 與 uuid import。
- `google_services_adapter.dart`：修正兩處 unawaited Future in try block。
- `speech_adapter.dart`：deprecated `localeId` 移入 `SpeechListenOptions`。
- `providers.dart`：移除 unused `flutter/material.dart` import。

### flutter test 修正（7/7 通過）

- `folder_sync_test`：`jsonEncode(_extensions)` 無法序列化 `const Set`，改為 `.toList()`。
- `widget_test`：mock `AppLockService`（`_NoLock`）避免 `local_auth` platform channel 在測試環境 hang；override `appLockProvider`。

### Google OAuth 設定

- Google Cloud 專案 `life-assistant-509213` 已建立。
- Calendar API、Gmail API、Google Drive API 已啟用。
- OAuth 同意畫面已設定（外部、測試階段）。
- Android OAuth 用戶端已建立（套件名稱 `com.lifeassistant.life_assistant`，SHA-1 `45:0B:28:B8:9D:C1:9C:6F:CD:35:46:28:F3:B4:D9:D3:76:16:B1:E5`）。
- Web OAuth 用戶端已建立（`705113310914-c96ndkj4dhk2epk3o2ssqponeu0ub3p0.apps.googleusercontent.com`）。
- `AndroidManifest.xml` 加入 Web client ID meta-data。
- `GoogleServicesAdapter` 所有 `GoogleSignIn` 實例加入 `serverClientId`。
- 不使用 Firebase，不需要 `google-services.json`。
- debug.keystore 已在 `C:\Users\Administrator\.android\debug.keystore` 建立。

## 先前完成（2026-09-20）

### 基礎與資料層

- Flutter 專案、Riverpod、GoRouter、Drift/SQLite、Repository 與 adapter 邊界已建立。
- Database schema 已升至 v3；v2 新增 Folder Sync／Bridge 執行表，v3 新增 Calendar 專案關聯欄位，均保留 migration 路徑。
- Notes FTS5、預設標籤、內建範本、Activity Log、Preferences 已實作。
- SQLite backup、restore staging、JSON／CSV export 已實作；還原前有明確確認，原 DB 會保留為 `life_assistant.pre_restore.db`。

### App 功能

- Dashboard：規則摘要、優先排序、待辦／行程／提醒／等待中／採買／習慣／專案區塊、自訂顯示與順序、快捷列。
- Tasks：CRUD、狀態、優先度、日期、提醒、Checklist、標籤、專案、附件、快速輸入。
- Calendar：快取、讀取／新增／修改／刪除、簡化週／月範圍、重疊提示、專案關聯。
- Gmail：metadata 快取、轉待辦／行程、掛到專案、離線快取錯誤狀態。
- Projects：待辦、行程、筆記、Gmail、附件與最近活動彙整。
- Notes：Markdown 編輯／預覽、自動儲存、FTS、標籤、雙向連結、專案、附件、轉待辦／行程。
- Habits、Shopping、Templates、Activity Log、每日回顧、長期視圖、語音快速輸入已實作。
- 溫暖、極簡、深色三套 Theme 與主題偏好持久化已實作。

### Folder Sync

- 首次同步強制空 Local folder，且只做 Drive → Local。
- 正常同步支援新增、修改、刪除、子資料夾、排除 DB／Bridge／暫存檔。
- Snapshot 只在單檔成功後前進；每個 operation 另存成功／失敗紀錄。
- 雙方修改、刪除對修改會進入 conflict；可保留本機、Drive 或兩份。
- 內建 Local Markdown Workspace，可建立、開啟、編輯、預覽與刪除 `.md`。

### ChatGPT Bridge 與安全

- versioned schema validator、action registry、`request_id + action_id` 防重複、逐項確認與 `action_results.json` 已實作。
- Drive folder／manifest／README、current state、inbox、projects export、pending actions import 已實作。
- App Lock、salted PIN hash、biometric fallback、安全 log scrubber 已實作。

## 測試狀態

| 測試檔案 | 狀態 |
|---------|------|
| `test/application_rules_test.dart` | ✅ 3/3 通過 |
| `test/repository_test.dart` | ✅ 2/2 通過 |
| `test/folder_sync_test.dart` | ✅ 1/1 通過 |
| `test/widget_test.dart` | ✅ 1/1 通過 |

## 下一步

### 需要 Android Studio（優先）

1. 安裝 Android Studio → 自動安裝 Android SDK。
2. `flutter doctor` 確認 Android toolchain OK。
3. 接上實機或啟動模擬器，執行 `flutter run`。
4. 驗收 Google Sign-In → Calendar → Gmail → Drive Bridge → Folder Sync。
5. 驗收 App Lock、backup/restore、通知、離線行為。
6. 勾選 `release_checklist.md` 對應項目。

### 不需要 Android SDK 可繼續做

目前已全部完成。

## 已知尚未完成

- Android release signing 尚未設定。
- iOS build／權限驗收需在 macOS + Xcode 執行。
- Release Gate 各項需實機驗收後才能勾選。
- 未 commit、未 push、未部署。
