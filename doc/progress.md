# 生活助理 App v0.1 — 開發進度

最後更新：2026-09-20  
目前狀態：**暫停於正式測試／驗收前**

## 狀態定義

- `已實作`：已有程式碼與畫面；不代表已通過測試。
- `已備妥測試`：測試案例已寫入，但依目前工作約定尚未執行。
- `待驗證`：需執行 analyze、test、裝置或外部服務驗收。
- `待外部設定`：需要 Google OAuth 專案、Android SDK／簽章或 macOS/Xcode 等環境資料。

## 本次完成

### 基礎與資料層

- Flutter 專案、Riverpod、GoRouter、Drift/SQLite、Repository 與 adapter 邊界已建立。
- Database schema 已升至 v3；v2 新增 Folder Sync／Bridge 執行表，v3 新增 Calendar 專案關聯欄位，均保留 migration 路徑。
- Notes FTS5、預設標籤、內建範本、Activity Log、Preferences 已實作。
- `build_runner` 卡住問題已解除；2026-09-20 曾成功完成 93 outputs，修正語法後再次完成 91 outputs。
- SQLite backup、restore staging、JSON／CSV export 已實作；還原前有明確確認，原 DB 會保留為 `life_assistant.pre_restore.db`。

### App 功能

- Dashboard：規則摘要、優先排序、待辦／行程／提醒／等待中／採買／習慣／專案區塊、自訂顯示與順序、快捷列。
- Tasks：CRUD、狀態、優先度、日期、提醒、Checklist、標籤、專案、附件、快速輸入。
- Calendar：快取、讀取／新增／修改／刪除、簡化週／月範圍、重疊提示、專案關聯。
- Gmail：metadata 快取、轉待辦／行程、掛到專案、離線快取錯誤狀態。
- Projects：待辦、行程、筆記、Gmail、附件與最近活動彙整。
- Notes：Markdown 編輯／預覽、自動儲存、FTS、標籤、雙向連結、專案、附件、轉待辦／行程。
- Habits、Shopping、Templates、Activity Log、每日回顧、長期視圖、語音快速輸入已實作。
- 相機／圖片／一般檔案會複製到 App private storage；OCR 明確不在 v0.1。
- 溫暖、極簡、深色三套 Theme 與主題偏好持久化已實作。

### Folder Sync

- 首次同步強制空 Local folder，且只做 Drive → Local。
- 正常同步支援新增、修改、刪除、子資料夾、排除 DB／Bridge／暫存檔。
- Snapshot 只在單檔成功後前進；每個 operation 另存成功／失敗紀錄。
- 雙方修改、刪除對修改會進入 conflict；可保留本機、Drive 或兩份。
- Markdown／文字衝突可看雙方內容；binary 不嘗試 diff。
- 以 Drive file ID 或完全相同 SHA-256 做安全 rename 辨識；不確定時不猜測。
- 內建 Local Markdown Workspace，可建立、開啟、編輯、預覽與刪除 `.md`。
- Bridge 使用 `drive.file`；使用者主動啟用 Folder Sync 時才延遲要求完整 Drive scope，並由 App 列出資料夾選擇。

### ChatGPT Bridge 與安全

- versioned schema validator、action registry、`request_id + action_id` 防重複、逐項確認與 `action_results.json` 已實作。
- Drive folder／manifest／README、current state、inbox、projects export、pending actions import 已實作。
- Bridge onboarding、測試指令、Bridge ID／schema 驗證、Share Sheet 已接上。
- App Lock、salted PIN hash、biometric fallback、安全 log scrubber 已實作。
- Google Calendar／Gmail／Drive 採功能觸發後才授權；設定頁可檢查與撤銷連線。
- Android／iOS 權限說明、Android FragmentActivity、通知 desugaring 與裝置時區已設定。

## 已備妥但尚未執行的測試

- `test/application_rules_test.dart`：中文快速輸入、Bridge validator、Sync planner。
- `test/repository_test.dart`：核心資料、FTS 搜尋、Activity Log、Preferences、schema v3。
- `test/folder_sync_test.dart`：initial sync、雙方修改 conflict、keep-local resolution。
- `test/widget_test.dart`：local-first onboarding smoke test。

## 暫停點與下一步

恢復後先完成下列開發收尾，再進入正式驗收：

1. 重新執行 formatter 與 `build_runner`（最後新增 `@ReferenceName` 與 Drive folder picker 後尚未重跑）。
2. 修完 `flutter analyze` 揭露的型別／lint 問題；目前尚未執行 analyze，因此不可宣稱可編譯。
3. 執行 `flutter test`，修正所有 unit／repository／widget／sync 測試。
4. 安裝或接通 Android SDK 後做 Android debug/release build 與實機權限驗收。
5. 提供 Google OAuth client 設定後，驗收 Calendar、Gmail、Drive Bridge 與 Folder Sync。
6. iOS build／權限驗收需在 macOS + Xcode 執行。
7. 完成 backup/restore、offline、migration chain、通知、App Lock 的實機驗收後，才能勾選 `release_checklist.md`。

## 已知尚未完成

- Task／Project「另存範本」的入口尚未完成；自訂範本與內建範本已可用。
- Google OAuth client、Android release signing、production identifiers 尚未提供，程式不可替使用者虛構。
- CI 尚未建立。
- 正式 accessibility pass、release build 與跨平台實機測試尚未執行。
- 未 commit、未 push、未部署、未建立付費 GCP 資源。
