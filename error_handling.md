# 生活助理 App v0.1 — Error Handling

## 1. 錯誤分類

### Recoverable

- 網路中斷
- Google token 過期
- Calendar 暫時失敗
- Drive sync 部分失敗
- notification permission 未開

### User Action Required

- Google 未授權
- Local folder 權限失效
- Bridge schema 不相容
- sync conflict

### Fatal / Data Integrity

- SQLite migration 失敗
- DB corruption
- backup restore 失敗

## 2. UI 規則

錯誤訊息要包含：

- 發生什麼
- 哪個功能受影響
- 本機資料是否安全
- 可採取什麼動作

避免只顯示：

`Something went wrong`

## 3. Retry

可重試：

- Gmail
- Calendar
- Drive
- Folder Sync
- Bridge read/write

不可盲目重試：

- destructive action
- duplicate Bridge action
- schema mismatch

## 4. Logging

Debug log 不記：

- OAuth token
- PIN
- Password
- 完整敏感郵件正文

Activity Log 與 debug log 分離。
