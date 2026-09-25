# 生活助理 App v0.1 — Error Handling

最後更新：2026-09-25

## 1. 定位

正式 Web / Cloud 主線的錯誤處理以 FastAPI Backend 為準。所有 API error 必須可追蹤、不得洩漏 secret / token / 原始敏感 exception，且外部 action 的 failure / partial success 不得包裝成 full success。

## 2. Backend Error Envelope

目前 baseline：

```json
{
  "error": {
    "code": "machine_readable_code",
    "message": "safe user-facing message",
    "request_id": "traceable-request-id"
  }
}
```

HTTP response 同時回傳：

```text
X-Request-ID: <request_id>
```

規則：

- `error.code`：machine-readable category。
- `error.message`：不包含 secret、token、password 或未過濾 exception detail。
- `error.request_id`：對應 server-side request trace。
- client 提供合法 `X-Request-ID` 時可沿用；否則 Backend 產生新的 UUID。
- validation error 統一使用 `validation_error` baseline。
- 未捕捉 exception 對 client 只回 `internal_error` / `Internal server error`，server log 只記 request id 與 exception type baseline。

## 3. 錯誤分類

### Recoverable / External

- network / Google API unavailable
- Google token 過期，可嘗試 refresh
- Google scope / reauthorization required
- Calendar / Gmail / Drive provider failure

### User Action Required

- Google 未授權或 scope 不足
- session / identity 不存在
- destructive action 尚未取得必要 confirmation（完整 enforcement 尚待實作）
- Bridge schema / contract 不相容

### Audit / Partial Success

- `audit_unavailable`：mutation 尚未執行；因 audit start 失敗而 fail closed。
- `audit_finalize_failed`：action 可能已完成，但 execution record finalize 失敗；不得宣稱 full success。
- `audit_failure_record_failed`：原 action 已失敗，而且 failure audit 亦無法落盤。
- `partial_success`：已完成部分外部 mutation，但後續步驟失敗；目前 Drive Bridge ensure 有 baseline。

### Fatal / Data Integrity

- PostgreSQL / migration data integrity failure
- SQLite migration / export corruption
- backup / restore failure

## 4. Execution / Activity Log

Cloud Backend 使用 `execution_logs` operational table 記錄 mutation evidence。

目前欄位 baseline 包含：

- id
- request_id
- action_id
- user_sub
- action_type
- entity_type / entity_id
- provider
- status
- summary
- result
- error_category
- started_at / finished_at

mutation baseline 行為：

```text
start execution record (running)
↓
execute internal / external action
↓
finish success / failure / partial_success
↓
/activity 可查詢
```

若 `start_execution` 無法落盤，action 不執行。

## 5. Google Integration Failure

Google mutation 目前已接 execution log：

- calendar.create
- calendar.update
- calendar.delete
- gmail.to_task
- gmail.to_calendar
- drive.bridge.ensure

規則：

- provider failure 記錄 execution failure category。
- Calendar / Gmail / Drive error 不得修改不相關 PostgreSQL 主資料。
- Drive ensure 若 root folder 已建立但後續 bridge folder 失敗，記錄 `partial_success` baseline。
- 真實帳號外部 failure → execution evidence 的 end-to-end runtime acceptance 仍為 NOT VERIFIED。

## 6. UI 規則

使用者可見錯誤應說明：

- 發生什麼
- 哪個功能受影響
- action 是否可能已完成 / 部分完成
- 資料是否安全
- 可採取什麼動作
- 可提供 request id 供追查

避免只顯示：

`Something went wrong`

也避免把 `partial_success` 顯示成「完成」。

## 7. Retry

可以依明確 policy 重試：

- read-only Gmail / Calendar / Drive request
- 明確 idempotent operation
- provider transient failure

不可盲目重試：

- destructive action
- 尚無 idempotency key 的 external mutation
- duplicate Bridge / MCP action
- schema mismatch
- action 已可能成功但 audit finalize 失敗的情境

## 8. Logging / Sensitive Data

Debug / error log 不得記錄：

- OAuth access / refresh token
- client secret
- password / database credential
- PIN / biometric secret
- 完整敏感郵件正文

Activity / execution log 與 debug log 分離；execution log 只保留足以追蹤 action 的 metadata / result category，不作敏感正文鏡像。
