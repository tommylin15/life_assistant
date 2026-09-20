# 生活助理 App v0.1 — Folder Sync Specification

## 1. Scope

本文件定義手機指定資料夾與 Google Drive 指定資料夾之間的手動雙向同步規則。

v0.1 目標：

- 一個 Local Folder 對一個 Google Drive Folder
- 使用者手動觸發同步
- 支援子資料夾
- 支援 Markdown、文字、圖片、PDF、一般文件
- Local 可離線編輯
- Google Drive 作為首次同步的唯一來源
- 正常同步後支援雙向新增、修改、改名、刪除
- 避免雙方同時修改造成靜默覆蓋

不包含：

- 背景即時同步
- 多組 Folder Pair
- 自動三方 merge
- SQLite DB 檔案同步
- ChatGPT_Bridge 系統檔案的一般 Folder Sync

---

## 2. 核心規則

### Rule 1 — 不靜默覆蓋雙方都修改過的檔案

若 Local 與 Drive 在上次成功同步後都發生內容變更，必須進入 Conflict。

### Rule 2 — 刪除屬於正常同步動作

若一端在上次成功同步後刪除檔案，而另一端未再修改該檔案，刪除直接同步到另一端，不做額外確認。

Google Drive 的垃圾桶 / 版本能力視為遠端復原機制，不由本 App 額外建立刪除確認流程。

### Rule 3 — 首次同步以 Google Drive 為主

第一次建立 Folder Pair 時：

- Google Drive 指定資料夾為 Source of Truth。
- Local 指定資料夾必須為乾淨的空資料夾。
- App 驗證 Local Folder 為空後才允許開始首次同步。
- 首次同步只執行 Drive → Local。
- 首次同步成功後建立 Initial Sync Snapshot。
- 後續才進入正常雙向同步。

### Rule 4 — SQLite 不走一般 Folder Sync

App 主資料庫、WAL、SHM、backup working files 等均排除。

### Rule 5 — ChatGPT_Bridge 預設不走一般 Folder Sync

`ChatGPT_Bridge/` 由 Bridge 模組自行管理，避免兩個同步機制同時修改同一批系統交換檔案。

### Rule 6 — Snapshot 只在驗證成功後更新

一次同步若部分失敗，不得把失敗項目標記為已同步。

---

## 3. Folder Pair Model

v0.1 只允許一組 Folder Pair：

```text
Local Folder
    ↕
Google Drive Folder
```

建議資料：

- `local_root_uri`
- `drive_folder_id`
- `drive_folder_name`
- `include_subfolders`
- `enabled_extensions`
- `last_successful_sync_at`
- `sync_schema_version`

Local Folder 使用平台提供的持久化 folder permission / URI，不應僅保存不穩定的絕對 path。

Drive 端以 `drive_folder_id` 作為正式識別，不以名稱作唯一識別。

---

## 4. File Identity

每個已同步檔案至少保存：

- relative_path
- drive_file_id
- local_size
- drive_size
- local_modified_at
- drive_modified_at
- local_content_hash
- drive_content_hash
- last_synced_hash
- last_synced_relative_path
- last_successful_sync_at
- mime_type

### 4.1 Hash

內容變更的主要判斷依據為 SHA-256。

修改時間與 size 可作快速掃描與 optimization，但不可作為唯一內容一致性依據。

### 4.2 Drive File ID

Drive file ID 必須保存，用於：

- 改名辨識
- 路徑變更
- 避免只靠檔名配對
- Drive metadata 追蹤

---

## 5. Snapshot Model

每個已同步檔案都要有 Last Successful Sync Snapshot。

概念：

```text
Last Sync
Local = AAA
Drive = AAA
```

後續掃描：

### Local only changed

```text
Local = BBB
Drive = AAA
Last = AAA
```

Action：Upload

### Drive only changed

```text
Local = AAA
Drive = CCC
Last = AAA
```

Action：Download

### Both changed

```text
Local = BBB
Drive = CCC
Last = AAA
```

Action：Conflict

Snapshot 必須是「最後一次確認兩端一致」的狀態，不是單純最近掃描狀態。

---

## 6. Initial Sync

### 6.1 建立 Folder Pair

使用者：

1. 選擇 Local Folder
2. 選擇 Google Drive Folder
3. App 檢查 Local Folder
4. 若 Local 非空，拒絕建立 Pair
5. 顯示「首次同步將以 Google Drive 為主並下載到此空資料夾」
6. 使用者開始首次同步

### 6.2 Local Clean Folder Definition

Local Folder 必須：

- 不含檔案
- 不含子資料夾中的使用者檔案

平台系統自動產生且明確可安全忽略的 metadata 檔案，可由實作定義 exclusion list。

若發現使用者內容：

```text
此資料夾不是空的。
首次同步必須使用乾淨的空資料夾，Google Drive 將作為初始資料來源。
```

不可提供「直接覆蓋」按鈕。

### 6.3 Initial Download

首次同步：

```text
Drive scan
↓
Build download plan
↓
Create local folders
↓
Download files
↓
Verify each file
↓
Create snapshot
↓
Mark initial sync complete
```

若部分下載失敗：

- 已成功檔案可保留
- Initial Sync 不標記完成
- 下次執行繼續補齊
- 不啟用正常雙向同步，直到 Initial Sync 完整成功

---

## 7. Change Detection

每次正常同步掃描：

```text
Local Current State
Drive Current State
Last Successful Snapshot
```

建立 Change Plan。

主要狀態：

| Local | Drive | 相對 Snapshot | Action |
|---|---|---|---|
| 未變 | 未變 | None | No-op |
| 已改 | 未變 | Local changed | Upload |
| 未變 | 已改 | Drive changed | Download |
| 已改 | 已改 | Both changed | Conflict |
| 新檔 | 不存在 | Local new | Upload |
| 不存在 | 新檔 | Drive new | Download |
| 已刪 | 未變 | Local delete | Delete Drive |
| 未變 | 已刪 | Drive delete | Delete Local |

---

## 8. Upload

Local → Drive：

1. 確認 Drive target folder
2. 若為既有檔案，以 drive_file_id 更新
3. 若為 Local new，建立 Drive file
4. 上傳完成
5. 重新取得 Drive metadata
6. 必要時重新計算 / 驗證
7. 更新該檔案 snapshot

若上傳失敗：

- Local 保留
- Snapshot 不前進
- Activity Log 記錄失敗
- 下次重試

---

## 9. Download

Drive → Local：

1. 取得 Drive file metadata
2. 下載至 temporary file
3. 驗證下載完成
4. 計算 hash
5. atomic replace / move 到正式路徑
6. 更新 snapshot

避免直接覆寫正式檔案造成下載中斷後檔案損壞。

---

## 10. Delete

### 10.1 Local Delete

條件：

- Snapshot 有該檔案
- Local 已不存在
- Drive 自上次同步後沒有新的內容變更

Action：

```text
Delete / Trash Drive File
```

完成後移除 / 更新 snapshot mapping。

### 10.2 Drive Delete

條件：

- Snapshot 有該檔案
- Drive 已不存在或已被 trash
- Local 自上次同步後沒有新的內容變更

Action：

```text
Delete Local File
```

完成後移除 / 更新 snapshot mapping。

### 10.3 Delete vs Modify Conflict

若一端刪除、另一端在上次同步後修改：

```text
Local deleted
Drive modified
```

或：

```text
Drive deleted
Local modified
```

不得直接刪除修改後內容。

進入 Conflict，提供：

- 保留修改後版本
- 接受刪除

若保留修改後版本，需重新建立被刪除端的檔案。

---

## 11. Rename / Move

優先利用 Drive file ID 與 snapshot 判斷。

### 11.1 Drive Rename

同一 `drive_file_id`，relative path 改變：

- 若 Local 未改名 / 未修改造成衝突
- Local 跟著 rename / move

### 11.2 Local Rename

若 Local 舊檔消失、新路徑出現，且內容 hash 與 snapshot 相符：

- 可判斷為 rename candidate
- 更新 Drive 檔名 / folder location
- 保留原 drive_file_id

若無法安全判斷：

- 視為 delete + new
- 仍遵循 Delete / Upload 規則

第一版不需要追求 100% rename intelligence。

---

## 12. Conflict Resolution

### 12.1 Text / Markdown

顯示：

- File name
- Local modified time
- Drive modified time
- Diff（若可產生）
- 保留 Local
- 保留 Drive
- 兩份都保留

v0.1 不自動 merge。

### 12.2 Binary

圖片、PDF、Office 文件等：

- 保留 Local
- 保留 Drive
- 兩份都保留

不做 diff。

### 12.3 Keep Both

產生 conflict copy，例如：

```text
日本旅行.md
日本旅行 (Drive Conflict 2026-09-20 1825).md
```

命名需避免覆蓋既有檔案。

---

## 13. Sync Execution Order

一次 `立即同步`：

```text
1. Check Google authentication
2. Check folder pair permission
3. Verify initial sync state
4. Scan Local
5. Scan Drive
6. Load Last Successful Snapshot
7. Build Change Plan
8. Resolve blocking conflicts
9. Execute downloads
10. Execute uploads
11. Execute rename/move
12. Execute deletes
13. Verify results
14. Update successful snapshots
15. Write Activity Log
16. Show summary
```

若有 blocking conflict，可先處理其他互不相依的安全項目；衝突項目維持未同步。

---

## 14. Partial Failure / Retry

範例：

```text
同步部分完成

成功：11
失敗：1
未完成：8
衝突：2
```

每個 file operation 個別記錄結果。

下次同步：

- 不重做已成功且 snapshot 已更新的項目
- 重試失敗 / 未完成項目
- 重新掃描衝突項目的現況

不得用單一 global flag 把整批錯誤標記成成功。

---

## 15. Offline Behavior

無網路：

- Workspace 可正常瀏覽 Local
- Markdown 可編輯與儲存 Local
- 顯示 `本機有變更`
- `立即同步` 顯示無網路，不破壞 Local 資料

恢復網路後由使用者再次觸發同步。

---

## 16. Exclusion Rules

至少排除：

```text
ChatGPT_Bridge/
*.db
*.sqlite
*.sqlite3
*-wal
*-shm
temporary sync files
app internal metadata files
```

若 Local Workspace root 包含 App 自己的 hidden metadata directory，也必須排除。

建議 App 的同步 metadata 放在 App private storage，而不是使用者 Workspace 內。

---

## 17. Supported File Types

預設：

- `.md`
- `.txt`
- `.json`
- 常見圖片
- `.pdf`
- 常見一般文件

可由設定控制部分類型是否同步。

v0.1 不解析 binary 內容。

---

## 18. Activity Log

一次同步至少記：

- 開始時間
- 結束時間
- Upload count
- Download count
- Delete count
- Rename count
- Conflict count
- Failure count
- 結果：成功 / 部分成功 / 失敗

使用者 UI 顯示簡化版本。

詳細 debug log 可獨立保存。

---

## 19. UI Requirements

設定頁：

```text
Markdown Workspace

手機資料夾
[已選擇資料夾]

Google Drive
[已選擇資料夾]

包含子資料夾  ✓

最後同步
今天 18:32

本機待上傳  3
Drive 待下載 2
衝突         0

[立即同步]
```

同步狀態：

- 已同步
- 本機有變更
- Drive 有更新
- 同步中
- 衝突
- 同步失敗

狀態不可只靠顏色。

---

## 20. Security

- Google OAuth token 使用 secure storage
- Drive token 不進 SQLite export / JSON export / Bridge
- Local folder permission 使用平台正式機制
- 不允許 Folder Sync 任意掃描整個手機
- 使用者必須明確選擇 Local Folder 與 Drive Folder
- destructive operation 僅限已建立 Folder Pair 的同步範圍內

---

## 21. Data Structures

建議 SQLite 內增加：

### sync_pairs

- id
- local_root_uri
- drive_folder_id
- include_subfolders
- allowed_types_json
- initial_sync_completed
- last_successful_sync_at
- created_at
- updated_at

v0.1 可限制只有一筆 active pair。

### sync_files

- id
- sync_pair_id
- relative_path
- drive_file_id
- mime_type
- last_synced_hash
- local_hash
- drive_hash
- local_modified_at
- drive_modified_at
- last_successful_sync_at
- sync_status

### sync_operations

- id
- sync_pair_id
- relative_path
- operation_type
- status
- error_code
- started_at
- finished_at

---

## 22. Acceptance Criteria

### Initial Sync

- [ ] Local Folder 非空時不可建立首次同步
- [ ] Initial Sync 僅 Drive → Local
- [ ] 全部成功後才設定 `initial_sync_completed = true`
- [ ] 首次成功後有完整 snapshot

### Normal Sync

- [ ] Local new → Drive
- [ ] Drive new → Local
- [ ] Local modify → Drive
- [ ] Drive modify → Local
- [ ] Local delete → Drive delete
- [ ] Drive delete → Local delete
- [ ] Local delete + Drive modify → Conflict
- [ ] Drive delete + Local modify → Conflict
- [ ] Both modify → Conflict
- [ ] Rename 可在安全情況下同步
- [ ] Markdown 衝突可查看 diff
- [ ] Binary 衝突不做 diff
- [ ] Partial failure 不會錯誤前進 snapshot
- [ ] 無網路時不破壞 Local
- [ ] SQLite / ChatGPT_Bridge 不進一般 Folder Sync
- [ ] 所有同步操作有 Activity Log
