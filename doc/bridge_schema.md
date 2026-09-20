# 生活助理 App v0.1 — ChatGPT Drive Bridge Schema

## 1. Purpose

本文件定義 ChatGPT ↔ Google Drive ↔ 生活助理 App 之間交換資料的 JSON schema、檔案責任與驗證規則。

核心原則：

- SQLite 是 App 主資料來源
- Google Drive 是交換層
- ChatGPT 不直接操作 SQLite
- App 不信任外部 JSON，所有匯入必須驗證
- 破壞性動作需經使用者確認
- 所有 schema 都必須帶版本
- 未識別欄位應盡量忽略，不應直接造成整包失敗
- 未識別 action type 必須拒絕執行

---

## 2. Bridge Folder

預設：

```text
生活助理/
└── ChatGPT_Bridge/
    ├── README.md
    ├── bridge_manifest.json
    ├── current_state.json
    ├── inbox.json
    ├── projects.json
    ├── pending_actions.json
    ├── action_results.json
    └── history/
```

### 2.1 檔案責任

| File | Writer | Reader | 用途 |
|---|---|---|---|
| `README.md` | App | ChatGPT / User | 操作說明 |
| `bridge_manifest.json` | App | ChatGPT / App | Bridge identity / schema |
| `current_state.json` | App | ChatGPT | 目前生活狀態 |
| `inbox.json` | App | ChatGPT | 待分析事項 |
| `projects.json` | App | ChatGPT | 進行中生活專案 |
| `pending_actions.json` | ChatGPT | App | 建議動作 |
| `action_results.json` | App | ChatGPT | 執行結果 |
| `history/*` | App | User / ChatGPT | 歷史快照 / 稽核 |

App 不應修改 ChatGPT 正在產生中的 `pending_actions.json`；可採 temporary file + rename 或 version file 避免部分寫入。

---

## 3. Common Envelope

所有 JSON 根節點應包含：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:30:00+08:00",
  "source": "app"
}
```

### 3.1 Required common fields

- `schema_version`: string
- `bridge_id`: string
- `generated_at`: RFC 3339 / ISO 8601 with timezone
- `source`: `app` | `chatgpt`

### 3.2 Time

所有 datetime 使用：

```text
YYYY-MM-DDTHH:mm:ss±HH:mm
```

不得傳 ambiguous local time。

日期型欄位：

```text
YYYY-MM-DD
```

---

## 4. bridge_manifest.json

用途：

- Bridge 驗證
- 版本檢查
- 能力宣告

範例：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:30:00+08:00",
  "source": "app",
  "app": {
    "name": "Life Assistant",
    "app_version": "0.1.0",
    "platform": "android"
  },
  "capabilities": [
    "read_current_state",
    "read_inbox",
    "read_projects",
    "propose_create_task",
    "propose_update_task",
    "propose_create_calendar_event",
    "propose_update_calendar_event",
    "propose_create_note",
    "propose_add_shopping_item"
  ],
  "files": {
    "current_state": "current_state.json",
    "inbox": "inbox.json",
    "projects": "projects.json",
    "pending_actions": "pending_actions.json",
    "action_results": "action_results.json"
  }
}
```

---

## 5. current_state.json

用途：讓 ChatGPT 快速理解「現在」。

範例：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:30:00+08:00",
  "source": "app",
  "context": {
    "timezone": "Asia/Taipei",
    "local_date": "2026-09-20"
  },
  "summary": {
    "open_tasks": 8,
    "due_today": 2,
    "overdue": 1,
    "waiting": 2,
    "today_events": 3
  },
  "tasks": [
    {
      "id": "task_01",
      "title": "回覆裝修廠商",
      "status": "waiting",
      "priority": "high",
      "due_at": "2026-09-21T18:00:00+08:00",
      "project_id": "project_home",
      "tags": ["居家"],
      "note": "等待對方更新報價"
    }
  ],
  "calendar": [
    {
      "id": "event_local_ref_01",
      "google_event_id": "abc123",
      "title": "牙醫",
      "starts_at": "2026-09-20T09:00:00+08:00",
      "ends_at": "2026-09-20T10:00:00+08:00"
    }
  ],
  "habits": [],
  "shopping": [],
  "recent_activity": []
}
```

### 5.1 current_state restrictions

不得放：

- OAuth token
- PIN
- 本機絕對敏感路徑
- 不必要的完整 Gmail 正文
- 私密附件內容

---

## 6. inbox.json

用途：提供需要 ChatGPT 分析的候選事項。

範例：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:30:00+08:00",
  "source": "app",
  "items": [
    {
      "id": "inbox_001",
      "type": "gmail",
      "subject": "預約時間變更",
      "sender": "example@example.com",
      "received_at": "2026-09-20T16:20:00+08:00",
      "snippet": "您的預約時間已調整為...",
      "suggested_project_id": null,
      "available_actions": [
        "create_task",
        "create_calendar_event",
        "ignore"
      ]
    }
  ]
}
```

---

## 7. projects.json

用途：提供 ChatGPT 專案上下文。

範例：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:30:00+08:00",
  "source": "app",
  "projects": [
    {
      "id": "project_home",
      "name": "家中裝修",
      "status": "active",
      "summary": "目前等待設備與報價確認",
      "open_task_ids": ["task_01"],
      "note_ids": ["note_01"],
      "attachment_count": 4
    }
  ]
}
```

---

## 8. pending_actions.json

用途：ChatGPT 提出「建議動作」，App 讀入並顯示給使用者確認。

根節點：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:35:00+08:00",
  "source": "chatgpt",
  "request_id": "req_20260920_183500_001",
  "summary": "建議建立一個高優先待辦並更新一個行程",
  "actions": []
}
```

### 8.1 Common action fields

每個 action 至少：

```json
{
  "action_id": "act_001",
  "type": "create_task",
  "reason": "此郵件有明確截止日期，需要追蹤",
  "confidence": "high",
  "requires_confirmation": true,
  "payload": {}
}
```

Required：

- `action_id`
- `type`
- `requires_confirmation`
- `payload`

Optional：

- `reason`
- `confidence`: `low` | `medium` | `high`
- `source_refs`

所有 v0.1 actions 預設 `requires_confirmation = true`。

---

## 9. Supported Action Types

### 9.1 create_task

```json
{
  "action_id": "act_001",
  "type": "create_task",
  "requires_confirmation": true,
  "reason": "需要在明日前確認",
  "payload": {
    "title": "確認浴室設備報價",
    "note": "根據最新報價信件",
    "priority": "high",
    "status": "todo",
    "due_at": "2026-09-21T18:00:00+08:00",
    "project_id": "project_home",
    "tags": ["居家"]
  }
}
```

### 9.2 update_task

```json
{
  "action_id": "act_002",
  "type": "update_task",
  "requires_confirmation": true,
  "payload": {
    "task_id": "task_01",
    "changes": {
      "priority": "high",
      "due_at": "2026-09-22T18:00:00+08:00"
    }
  }
}
```

### 9.3 complete_task

```json
{
  "action_id": "act_003",
  "type": "complete_task",
  "requires_confirmation": true,
  "payload": {
    "task_id": "task_01"
  }
}
```

### 9.4 create_calendar_event

```json
{
  "action_id": "act_004",
  "type": "create_calendar_event",
  "requires_confirmation": true,
  "payload": {
    "title": "牙醫回診",
    "starts_at": "2026-09-23T14:00:00+08:00",
    "ends_at": "2026-09-23T15:00:00+08:00",
    "location": "",
    "description": "",
    "calendar_id": "primary"
  }
}
```

### 9.5 update_calendar_event

```json
{
  "action_id": "act_005",
  "type": "update_calendar_event",
  "requires_confirmation": true,
  "payload": {
    "google_event_id": "abc123",
    "changes": {
      "starts_at": "2026-09-23T15:00:00+08:00",
      "ends_at": "2026-09-23T16:00:00+08:00"
    }
  }
}
```

### 9.6 delete_calendar_event

```json
{
  "action_id": "act_006",
  "type": "delete_calendar_event",
  "requires_confirmation": true,
  "payload": {
    "google_event_id": "abc123"
  }
}
```

### 9.7 create_note

```json
{
  "action_id": "act_007",
  "type": "create_note",
  "requires_confirmation": true,
  "payload": {
    "title": "浴室設備比較",
    "body_markdown": "## 比較\n- A\n- B",
    "project_id": "project_home",
    "tags": ["居家"]
  }
}
```

### 9.8 update_note

```json
{
  "action_id": "act_008",
  "type": "update_note",
  "requires_confirmation": true,
  "payload": {
    "note_id": "note_01",
    "changes": {
      "body_markdown": "更新內容"
    }
  }
}
```

### 9.9 add_shopping_item

```json
{
  "action_id": "act_009",
  "type": "add_shopping_item",
  "requires_confirmation": true,
  "payload": {
    "list_id": "shopping_default",
    "name": "濾芯",
    "category": "居家"
  }
}
```

### 9.10 create_project

```json
{
  "action_id": "act_010",
  "type": "create_project",
  "requires_confirmation": true,
  "payload": {
    "name": "日本旅行",
    "summary": "規劃住宿、交通與行程",
    "tags": ["旅行"]
  }
}
```

---

## 10. Action Validation

App 匯入 `pending_actions.json` 時：

1. 驗證 JSON 可解析
2. 驗證 `bridge_id`
3. 驗證 `schema_version`
4. 驗證 `request_id`
5. 驗證 action_id 唯一
6. 驗證 action type
7. 驗證 payload required fields
8. 驗證 datetime
9. 驗證 referenced IDs 是否存在
10. 顯示 Review UI
11. 使用者接受 / 修改 / 拒絕
12. 執行
13. 寫 Activity Log
14. 產生 `action_results.json`

若任一 action 無效：

- 該 action 標記 invalid
- 不應讓整包其他有效 action 無法預覽
- 但 bridge_id / schema envelope 無效時可拒絕整包

---

## 11. action_results.json

用途：App 回報使用者最後採取了什麼動作。

範例：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:40:00+08:00",
  "source": "app",
  "request_id": "req_20260920_183500_001",
  "results": [
    {
      "action_id": "act_001",
      "status": "accepted",
      "executed": true,
      "entity_id": "task_123",
      "message": "待辦已建立"
    },
    {
      "action_id": "act_005",
      "status": "rejected",
      "executed": false,
      "message": "使用者取消"
    }
  ]
}
```

### status

- `accepted`
- `accepted_with_changes`
- `rejected`
- `failed`
- `invalid`

---

## 12. History

每次 Bridge exchange 建議保留快照：

```text
history/
└── 2026-09-20/
    ├── 183000_current_state.json
    ├── 183500_pending_actions.json
    └── 184000_action_results.json
```

可設定 retention。

v0.1 可先保留有限筆數或有限天數，避免 Drive 無限膨脹。

---

## 13. Idempotency

`request_id + action_id` 必須可防止重複執行。

若 App 已執行：

```text
request_id = X
action_id = Y
```

再次看到同一 action 時，不得重複建立。

需要回報：

```json
{
  "status": "invalid",
  "executed": false,
  "message": "duplicate_action"
}
```

---

## 14. Concurrency

避免 ChatGPT 與 App 同時寫同一檔案。

建議：

- App writer files：App only
- ChatGPT writer file：`pending_actions.json`
- App 對 `pending_actions.json` 採 read-only + archive
- 寫入採 temporary file + atomic rename（若 API / Drive 操作模式允許）

若偵測檔案在讀取後又更新：

- 不執行舊版本
- 重新讀取

---

## 15. Schema Versioning

格式：

```text
major.minor
```

例如：

```text
1.0
1.1
2.0
```

### Minor

- 新增 optional field
- 新增 optional metadata

舊 App 應盡量忽略未知欄位。

### Major

- required field 改變
- payload 結構不相容
- action semantics 改變

Major 不一致時：

```text
Bridge schema incompatible
```

停止自動匯入。

---

## 16. Error Envelope

若 App 需要輸出 Bridge error：

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:50:00+08:00",
  "source": "app",
  "error": {
    "code": "SCHEMA_MISMATCH",
    "message": "Unsupported schema major version",
    "recoverable": false
  }
}
```

建議 error code：

- `INVALID_JSON`
- `BRIDGE_ID_MISMATCH`
- `SCHEMA_MISMATCH`
- `UNKNOWN_ACTION`
- `INVALID_PAYLOAD`
- `MISSING_ENTITY`
- `DUPLICATE_ACTION`
- `GOOGLE_AUTH_REQUIRED`
- `DRIVE_UNAVAILABLE`
- `CALENDAR_ACTION_FAILED`
- `LOCAL_WRITE_FAILED`

---

## 17. ChatGPT Rules

`README.md` 應告知 ChatGPT：

1. 先讀 `bridge_manifest.json`
2. 確認 bridge_id 與 schema version
3. 只讀 App writer files
4. 建議動作只寫 `pending_actions.json`
5. 不修改 `current_state.json`
6. 不修改 `projects.json`
7. 不修改 `inbox.json`
8. 不直接假設動作已執行
9. 等待 `action_results.json` 才能視為完成
10. 不輸出 schema 未支援的 action type
11. 日期時間需含 timezone
12. 缺乏資訊時可少做，不要捏造 ID

---

## 18. Privacy

Bridge 不應包含：

- OAuth token
- PIN
- 密碼
- Authentication secrets
- App secure storage values

Gmail：

- 優先只輸出 metadata / snippet
- 除非使用者明確要求，不輸出完整信件正文

附件：

- v0.1 Bridge 僅傳 metadata / Drive reference
- 不內嵌 base64

---

## 19. Example Full Exchange

### Step 1 — App export

`current_state.json`

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:30:00+08:00",
  "source": "app",
  "context": {
    "timezone": "Asia/Taipei",
    "local_date": "2026-09-20"
  },
  "summary": {
    "open_tasks": 1,
    "due_today": 0,
    "overdue": 0,
    "waiting": 1,
    "today_events": 0
  },
  "tasks": [
    {
      "id": "task_01",
      "title": "等待裝修廠商回覆",
      "status": "waiting",
      "priority": "medium",
      "due_at": null,
      "project_id": "project_home",
      "tags": ["居家"]
    }
  ],
  "calendar": [],
  "habits": [],
  "shopping": [],
  "recent_activity": []
}
```

### Step 2 — ChatGPT proposal

`pending_actions.json`

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:35:00+08:00",
  "source": "chatgpt",
  "request_id": "req_001",
  "summary": "建議設定一個追蹤期限",
  "actions": [
    {
      "action_id": "act_001",
      "type": "update_task",
      "requires_confirmation": true,
      "reason": "等待事項已有追蹤需求",
      "confidence": "medium",
      "payload": {
        "task_id": "task_01",
        "changes": {
          "due_at": "2026-09-22T18:00:00+08:00",
          "priority": "high"
        }
      }
    }
  ]
}
```

### Step 3 — User confirms

App 寫入 SQLite。

### Step 4 — Result

`action_results.json`

```json
{
  "schema_version": "1.0",
  "bridge_id": "PA-7F42",
  "generated_at": "2026-09-20T18:40:00+08:00",
  "source": "app",
  "request_id": "req_001",
  "results": [
    {
      "action_id": "act_001",
      "status": "accepted",
      "executed": true,
      "entity_id": "task_01",
      "message": "待辦已更新"
    }
  ]
}
```

---

## 20. v0.1 Supported Action Registry

v0.1 正式支援：

- `create_task`
- `update_task`
- `complete_task`
- `create_calendar_event`
- `update_calendar_event`
- `delete_calendar_event`
- `create_note`
- `update_note`
- `add_shopping_item`
- `create_project`

未列出的 action 必須視為 unsupported。

---

## 21. Acceptance Criteria

- [ ] 所有 Bridge JSON 都有 schema_version
- [ ] 所有 Bridge JSON 都有 bridge_id
- [ ] 所有 datetime 都含 timezone
- [ ] App 可拒絕 bridge_id mismatch
- [ ] App 可拒絕不支援的 major schema
- [ ] App 可逐 action 驗證 payload
- [ ] Unsupported action 不會被執行
- [ ] Duplicate action 不會重複執行
- [ ] 所有 proposed actions 需經使用者確認
- [ ] App writer / ChatGPT writer 權責清楚
- [ ] action_results 可回報 accepted / rejected / failed
- [ ] OAuth token / PIN 不會出現在 Bridge
- [ ] ChatGPT 不可修改 App source-of-truth export files
