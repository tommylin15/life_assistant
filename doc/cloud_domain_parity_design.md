# Cloud Domain Parity Design — Notes / Habits / Shopping / Templates

最後更新：2026-09-26

狀態：**Design approved in chat; implementation not started**

## 1. 目的

本設計將既有 SQLite / Flutter domain 中已存在的以下四個正式產品 domain，補齊到目前 PostgreSQL / FastAPI Cloud target：

- Notes
- Habits
- Shopping
- Templates

這不是新增 Phase 2 產品功能，而是把既有 local contract 升級成目前正式 Cloud 架構下可持續維護、可 migration、可測試、可 audit 的 backend contract。

正式架構仍維持：

```text
Firebase Hosting
    ↓
Flutter Web / PWA
    ↓
Cloud Run — FastAPI Backend
    ↓
PostgreSQL
```

本設計遵守：

- `doc/PROJECT_RULES.md`
- `doc/decisions.md`
- `doc/spec.md`
- `doc/architecture.md`
- `doc/project_structure.md`
- `doc/migration_spec.md`
- `doc/coding_rules.md`
- `doc/testing_strategy.md`
- `doc/release_checklist.md`

## 2. 現況與問題

目前 repository 的 Flutter / SQLite 層已存在：

- `LifeNote` / `Notes` / `NoteLinks`
- `LifeHabit` / `Habits` / `HabitLogs`
- `LifeShoppingList` / `LifeShoppingItem` / `ShoppingLists` / `ShoppingItems`
- `LifeTemplate` / `Templates`
- 對應 `LifeRepository` contract

但目前 Cloud Backend 主要只有 Task / Project 等 PostgreSQL model 與 FastAPI CRUD。四個 domain 尚未有 Cloud target schema/API，因此：

1. Web / Cloud 尚無法把這些 domain 當 PostgreSQL operational source of truth。
2. SQLite → PostgreSQL migration 無完整 target tables。
3. Phase 1 Release Checklist 的 Notes / Habits / Shopping persistence 尚無法用 Cloud runtime evidence 驗證。

## 3. 設計原則

採用 **Parity-first normalized schema**。

### 3.1 必須維持

- 優先保留既有 SQLite entity shape 與 stable ID。
- PostgreSQL schema 使用 versioned Alembic migration。
- mutation 經 FastAPI auth / validation / execution log。
- API 採既有 `/api/v1` pattern。
- 不清空或 drop SQLite 原資料。
- 不把 migration 時間偽裝成不存在的歷史業務時間。
- 不把 partial success 包裝成 full success。

### 3.2 本批不做

本設計不順便加入：

- Template version history
- advanced habit analytics / streak engine
- complex recurrence engine
- shopping quantity / price / store / inventory
- generic entity table
- generic JSONB everything model
- Notes full-text search implementation
- tags / attachments Cloud migration
- MCP capability expansion
- Phase 2 Routine Library / Today / Focus / Plan / Review

上述能力若後續需要，另立 contract / design。

## 4. PostgreSQL Target Schema

### 4.1 `notes`

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | `varchar(36)` | no | stable ID；migration 優先保留 SQLite ID |
| `title` | `text` | yes | 與既有 SQLite nullable 語意一致 |
| `body` | `text` | yes | Markdown content；不轉成檔案 source of truth |
| `project_id` | `varchar(36)` | yes | relationship reference；本批不新增 DB FK |
| `created_at` | `timestamptz` | no | preserve source value |
| `updated_at` | `timestamptz` | no | preserve source value；Cloud update 時更新 |

不在本批替 `project_id` 加 PostgreSQL FK，理由是既有 SQLite schema 本身沒有此 FK，migration 必須先接受並驗證既有資料，而不是用新約束讓 migration 失敗。

### 4.2 `note_links`

| Column | Type | Null | Notes |
|---|---|---:|---|
| `source_note_id` | `varchar(36)` | no | FK → `notes.id` |
| `target_note_id` | `varchar(36)` | no | FK → `notes.id` |

Primary key：

```text
(source_note_id, target_note_id)
```

規則：

- duplicate link 不建立第二筆。
- source 與 target note 必須存在。
- note delete 時清除該 note 相關的 note_links；不刪除另一端 note。
- self-link 視為 invalid request，不建立。

### 4.3 `habits`

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | `varchar(36)` | no | stable ID |
| `title` | `varchar(500)` | no | required |
| `recurrence_rule` | `text` | no | 第一階段保留既有 recurrence string contract |
| `reminder_time` | `varchar(16)` | yes | 保留既有 local representation；本批不改 recurrence engine |
| `is_active` | `boolean` | no | default true |
| `created_at` | `timestamptz` | no | preserve source value |

本批**不新增 `updated_at`**。既有 SQLite Habit 沒有該歷史欄位；若 migration 時用匯入時間代填，會製造不存在的歷史事實。

### 4.4 `habit_completions`

Cloud table 名稱使用 `habit_completions`，語意對應既有 SQLite `HabitLogs`。

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | `varchar(36)` | no | stable ID |
| `habit_id` | `varchar(36)` | no | FK → `habits.id` |
| `completed_at` | `timestamptz` | no | completion occurrence |

Index：

```text
(habit_id, completed_at DESC)
```

每次 complete 新增一筆 completion，不覆寫既有紀錄。

### 4.5 `shopping_lists`

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | `varchar(36)` | no | stable ID |
| `name` | `varchar(500)` | no | required |
| `project_id` | `varchar(36)` | yes | optional project reference；本批不新增 DB FK |
| `created_at` | `timestamptz` | no | preserve source value |

本批不新增 source 不存在的 `updated_at`。

### 4.6 `shopping_items`

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | `varchar(36)` | no | stable ID |
| `list_id` | `varchar(36)` | no | FK → `shopping_lists.id` |
| `name` | `varchar(500)` | no | required |
| `category` | `varchar(255)` | yes | optional |
| `is_done` | `boolean` | no | default false |
| `sort_order` | `integer` | no | default 0 |

本批不新增 source 不存在的 created/updated timestamp。

Shopping list 回傳資料時可組合 items；DB 保持 normalized tables。

### 4.7 `templates`

| Column | Type | Null | Notes |
|---|---|---:|---|
| `id` | `varchar(36)` | no | stable ID |
| `name` | `varchar(500)` | no | required |
| `template_type` | `varchar(64)` | no | 既有 template type string |
| `payload_json` | `text` | no | 第一階段保留既有 raw JSON string contract |
| `created_at` | `timestamptz` | no | preserve source value |
| `updated_at` | `timestamptz` | no | preserve source value；Cloud update 時更新 |

本批不直接改成 PostgreSQL `jsonb`。原因：SQLite 現有 contract 是 JSON string，先完成 lossless parity；未來若要 JSONB，需要另外定義 payload schema、validation 與 migration。

## 5. SQLAlchemy Model 邊界

Backend 新增 focused model modules，避免把所有 domain 塞進單一檔案：

```text
backend/app/models/
├── note.py
├── habit.py
├── shopping.py
└── template.py
```

Pydantic API schemas 可先沿用目前 `models/schemas.py` 慣例；若該檔因本批變得過大，實作時可拆成 domain schema modules，但不可為了抽象而抽象。

## 6. API Contract

所有 endpoint：

- prefix：`/api/v1`
- auth：沿用 `current_user`
- validation：Pydantic
- DB access：`AsyncSession`
- mutation：execution log
- not found：404
- relationship conflict / invalid relationship：409 或 validation error，依既有 error contract 統一

### 6.1 Notes

```text
GET    /api/v1/notes
POST   /api/v1/notes
GET    /api/v1/notes/{note_id}
PATCH  /api/v1/notes/{note_id}
DELETE /api/v1/notes/{note_id}
GET    /api/v1/notes/{note_id}/links
POST   /api/v1/notes/{note_id}/links
```

Create body：

```json
{
  "title": "optional title",
  "body": "markdown text",
  "project_id": "optional-project-id"
}
```

Patch 允許更新：

- title
- body
- project_id

空 PATCH 必須被拒絕。

Link body：

```json
{
  "target_note_id": "..."
}
```

Mutation action types：

- `note.create`
- `note.update`
- `note.delete`
- `note.link`

### 6.2 Habits

```text
GET    /api/v1/habits
POST   /api/v1/habits
GET    /api/v1/habits/{habit_id}
PATCH  /api/v1/habits/{habit_id}
POST   /api/v1/habits/{habit_id}/complete
GET    /api/v1/habits/{habit_id}/completions
```

Create / patch contract 對應：

- title
- recurrence_rule
- reminder_time
- is_active（patch only；create default true）

空 PATCH 必須被拒絕。

Complete：

- 建立一筆新的 `habit_completions`。
- 不修改過去 completion。
- inactive habit 是否允許 complete：本批定義為 **不允許**，回傳 conflict；避免 inactive state 與 completion 同時成立造成語意不清。

Mutation action types：

- `habit.create`
- `habit.update`
- `habit.complete`

本批不新增 habit delete endpoint，保持既有 repository contract 的最小 parity。

### 6.3 Shopping

```text
GET   /api/v1/shopping-lists
POST  /api/v1/shopping-lists
GET   /api/v1/shopping-lists/{list_id}
POST  /api/v1/shopping-lists/{list_id}/items
PATCH /api/v1/shopping-items/{item_id}
```

List create：

- name
- optional project_id

Item create：

- name
- optional category

Item patch 第一階段只允許：

```json
{
  "is_done": true
}
```

這與既有 `toggleShoppingItem` contract 對齊，不在本批擴成完整 shopping editor。

Mutation action types：

- `shopping_list.create`
- `shopping_item.create`
- `shopping_item.toggle`

本批不新增 list/item delete、quantity、price、store 等能力。

### 6.4 Templates

```text
GET   /api/v1/templates
POST  /api/v1/templates
GET   /api/v1/templates/{template_id}
PATCH /api/v1/templates/{template_id}
```

Create / patch：

- name
- template_type
- payload_json

`payload_json` 必須至少能被解析為 JSON；本批不限制其內部 business schema，因既有 repository 尚未定義 per-template-type schema。

空 PATCH 必須被拒絕。

Mutation action types：

- `template.create`
- `template.update`

本批不新增 template delete / version history / apply endpoint。

## 7. Project Relation 行為

Notes 與 Shopping Lists 已有 optional `project_id` contract。

為避免 Cloud 上刪除 Project 後留下明顯 orphan relationship，既有 `DELETE /api/v1/projects/{project_id}` guard 應擴充：

若任何以下 entity 仍 reference 該 project，回 409：

- Task
- Note
- Shopping List

本批不替 `project_id` 建 DB FK，因 migration correctness 優先；刪除 guard 屬 Backend invariant。

## 8. Execution Log / Audit

每個重要 mutation 沿用現有：

```text
start_execution
→ domain mutation / transaction
→ finish_execution
```

失敗：

```text
start_execution
→ exception
→ fail_execution
→ normalized API error
```

Log 至少保留：

- user_sub / actor
- provider = `life_assistant` 或現行 internal naming 慣例
- action_type
- entity_type
- entity_id（建立成功後補）
- result
- summary

不得把 Note body、Template payload、secret 或敏感正文完整寫入 summary / error log。

## 9. Migration Design

Alembic 使用 additive migration，接在目前 migration chain 後。

預期 migration 建立：

```text
notes
note_links
habits
habit_completions
shopping_lists
shopping_items
templates
```

### 9.1 SQLite → PostgreSQL mapping

| SQLite | PostgreSQL |
|---|---|
| `Notes` | `notes` |
| `NoteLinks` | `note_links` |
| `Habits` | `habits` |
| `HabitLogs` | `habit_completions` |
| `ShoppingLists` | `shopping_lists` |
| `ShoppingItems` | `shopping_items` |
| `Templates` | `templates` |

### 9.2 Mapping rules

- 保留 stable IDs。
- SQLite datetime → timezone-aware PostgreSQL timestamp，依 migration_spec 統一時區語意。
- boolean integer → PostgreSQL boolean。
- `payloadJson` → `payload_json` text，字串內容不重寫。
- `HabitLogs` table rename 不改 completion semantics。
- source 沒有的 timestamp 不補假歷史值。

### 9.3 Verification

至少核對：

- 每張主表 row count。
- note_links source / target existence。
- habit completion → habit relationship。
- shopping item → list relationship。
- project_id reference summary（合法 / orphan 必須可觀察，不靜默捏造）。
- template payload JSON parseability；無法解析時標 migration failure/partial，不自行修內容。
- stable ID uniqueness。

Migration 必須可重跑或以 stable ID / upsert 避免 duplicate。

## 10. Error Handling

最低行為：

- unknown entity → 404
- duplicate note link → idempotent success 或 409 二選一；本設計固定採 **idempotent success**，避免重試產生不必要 failure
- note self-link → 422 validation error
- inactive habit complete → 409
- shopping item list 不存在 → 404
- invalid template JSON → 422
- database failure → 使用既有 normalized backend error contract

Mutation failure 不得留下 success execution record。

## 11. Transaction Boundaries

每個單一 mutation request 使用單一 DB transaction 語意。

特別是：

- create note link：existence check + insert 視為同一 mutation。
- complete habit：habit state check + completion insert 視為同一 mutation。
- add shopping item：list existence check + insert 視為同一 mutation。

Execution log 依現有 service pattern 落地；若現行 log service 本身需跨 commit，實作必須保持「business mutation success / failure」與 log result 一致，不得把 business failure 記成 success。

## 12. Backend Files Expected to Change

預期至少：

```text
backend/app/models/note.py
backend/app/models/habit.py
backend/app/models/shopping.py
backend/app/models/template.py
backend/app/models/schemas.py                 # 或拆 domain schema modules
backend/app/api/notes.py
backend/app/api/habits.py
backend/app/api/shopping.py
backend/app/api/templates.py
backend/app/api/projects.py                  # delete guard
backend/app/main.py                          # router registration
backend/alembic/versions/<new_revision>.py
backend/tests/test_notes.py
backend/tests/test_habits.py
backend/tests/test_shopping.py
backend/tests/test_templates.py
backend/tests/test_projects.py               # relation delete guard
```

若 implementation 發現現有 migration/export code 已有 domain-specific mapping，需一併更新並加測試；不得只建立 target tables 而留下 SQLite → PostgreSQL mapping 缺口。

## 13. Tests

### 13.1 Schema / migration

- Alembic upgrade 建表成功。
- migration chain 可從現行 head 連續 upgrade。
- downgrade 僅在安全可定義時提供；不得以破壞 production data 的方式當一般 rollback。
- SQLite mapping 的 stable IDs / relationships / row count 可驗證。

### 13.2 Notes

- create / list / get / patch / delete。
- nullable title/body parity。
- note link create / list。
- duplicate link idempotent。
- self-link rejection。
- delete cleanup links。
- execution log。

### 13.3 Habits

- create / list / get / patch。
- default active。
- complete adds history row。
- multiple completions preserved。
- inactive completion rejected。
- execution log。

### 13.4 Shopping

- create list。
- create item。
- list returns expected items。
- toggle item。
- invalid list rejection。
- project relation preserved。
- execution log。

### 13.5 Templates

- create / list / get / patch。
- valid JSON accepted。
- malformed JSON rejected。
- payload round-trip unchanged。
- execution log。

### 13.6 Projects

Project delete：

- linked task → 409。
- linked note → 409。
- linked shopping list → 409。
- no linked entity → existing delete behavior remains valid。

## 14. CI / Deployment / Runtime Validation

Implementation 完成後，驗證順序遵守專案治理：

```text
implementation
→ backend tests
→ migration tests
→ CI
→ GitHub main
→ GitHub Actions deployment
→ Cloud Run runtime
→ PostgreSQL persistence / relation validation
```

Runtime 至少做 acceptance-style smoke：

```text
Note: create → update → read → link if applicable → delete
Habit: create → update → complete → history
Shopping: create list → add item → toggle → read
Template: create → update → read
Activity / execution log: verify mutations visible
```

測試資料使用明確 acceptance prefix，完成後依安全規則清除；不得誤刪正式資料。

## 15. Definition of Done

本批只有在所需 evidence 完整時才可標示 DONE。

| Layer | Required status |
|---|---|
| design/spec | PASS |
| PostgreSQL schema / Alembic | PASS |
| FastAPI models / routes | PASS |
| backend tests | PASS |
| migration verification | PASS |
| CI | PASS |
| deployment | PASS |
| runtime CRUD/persistence | PASS |
| execution log validation | PASS |

若只有程式碼或 CI 通過，整體仍是 PARTIAL。

## 16. Explicit Non-Goals / Deferred Decisions

本設計刻意不決定：

- Notes PostgreSQL FTS/search implementation。
- Tags / attachments 的 Cloud schema。
- Template apply semantics。
- Template typed payload schema。
- Habit streak / analytics。
- Shopping quantity / price / store。
- hard FK from Note/Shopping project_id to Projects。
- generic soft-delete model。

這些不阻礙本次 Cloud parity，但不得在 implementation 時偷偷加入。

## 17. Acceptance Summary

成功後，Cloud Backend 對 Note / Habit / Shopping / Template 提供與既有 local contract 對齊的 target schema/API，PostgreSQL 能作為這四個 domain 的 operational source of truth，並為 SQLite → PostgreSQL migration、Web/PWA 接線與後續 Bridge/MCP coverage 建立可驗證基線。
