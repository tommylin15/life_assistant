# Cloud Domain Parity — Implementation Progress

最後更新：2026-09-26（Task 5）

對應設計：`doc/cloud_domain_parity_design.md`

對應計畫：`docs/superpowers/plans/2026-09-26-cloud-domain-parity.md`

## 狀態摘要

| Task | Scope | Implementation | Tests | CI | Deployment | Runtime |
|---|---|---|---|---|---|---|
| 1 | PostgreSQL target models + Alembic migration | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 2 | Notes API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 3 | Habits API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 4 | Shopping API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 5 | Templates API parity | PASS | PASS | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 6 | Project delete guard | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 7 | Full backend verification | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| 8 | CI / deployment / runtime acceptance | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |

## Task 1 — PostgreSQL target models + Alembic migration

狀態：**PASS（implementation / local tests）**

- 建立 Notes / Habits / Shopping / Templates ORM target models。
- Alembic revision：`20260926_0004`，`down_revision=20260925_0003`。
- model contract tests：6/6 PASS。
- Python compile：PASS。
- Runtime DB revision/table state、historical SQLite backfill：NOT VERIFIED。

## Task 2 — Notes API parity

狀態：**PASS（implementation / local tests）**

- Notes CRUD、bidirectional links、delete link cleanup、legacy nullable read。
- `note.create` / `note.update` / `note.delete` / `note.link`。
- Notes tests：12/12 PASS；Task 1–2 regression：18/18 PASS。
- CI / deployment / PostgreSQL runtime CRUD：NOT VERIFIED。

## Task 3 — Habits API parity

狀態：**PASS（implementation / local tests）**

- active-only list、create/get/patch、append completion、descending history。
- 不新增 delete / activate / deactivate。
- `habit.create` / `habit.update` / `habit.complete`。
- Habits tests：14/14 PASS；Task 1–3 regression：32/32 PASS。
- CI / deployment / PostgreSQL runtime completion persistence：NOT VERIFIED。

## Task 4 — Shopping API parity

狀態：**PASS（implementation / local tests）**

- Shopping List create/read、item create、nested sorted read、`is_done` toggle。
- `project_id` 原樣保存，本批不做 project existence validation。
- 不新增 delete / quantity / price / store。
- `shopping_list.create` / `shopping_item.create` / `shopping_item.toggle`。
- Shopping tests：14/14 PASS；Shopping + execution-log：17/17 PASS；Task 1–4 regression：49/49 PASS。
- CI / deployment / PostgreSQL runtime Shopping persistence：NOT VERIFIED。

## Task 5 — Templates API parity

狀態：**PASS（implementation / local tests）**

本 Task 建立 / 更新：

- `backend/app/api/templates.py`
- `backend/app/models/schemas.py`：新增 `TemplateCreate` / `TemplateUpdate` / `TemplateOut`
- `backend/app/main.py`：註冊 `/api/v1/templates`
- `backend/tests/test_templates.py`

API contract：

- `GET /api/v1/templates`
- `POST /api/v1/templates`
- `GET /api/v1/templates/{template_id}`
- `PATCH /api/v1/templates/{template_id}`

重要行為：

- Create 必須提供 `name` / `template_type` / `payload_json`。
- PATCH 只允許 `name` / `template_type` / `payload_json`；空 PATCH 與三欄 explicit null 都拒絕。
- request 長度限制與 DB 欄位一致：name 500、template_type 64。
- `payload_json` 保持 opaque `TEXT` string；不 `json.loads`、不 serialize、不 normalize、不重排 JSON key。
- JSON-like payload 與任意非 JSON 字串皆 lossless round-trip。
- 不新增 template delete / apply / version-history endpoint。
- mutation action types：`template.create` / `template.update`。
- provider 固定 `life_assistant`。
- execution summaries 不包含 `payload_json` 本文。

TDD / verification evidence：

- RED：Template schemas、router、main registration 尚不存在時，contract tests 如預期失敗。
- GREEN：Templates tests 12/12 PASS。
- Templates + execution-log regression（warnings-as-errors）：15/15 PASS。
- Full Task 1–5 regression（warnings-as-errors）：61/61 PASS。
- Python compile：PASS。
- JSON parse/serialize static scan：PASS。

尚未驗證：

- GitHub Actions CI：NOT VERIFIED
- Cloud Run deployment：NOT VERIFIED
- PostgreSQL runtime Template create/update/read persistence：NOT VERIFIED
- opaque payload runtime round-trip：NOT VERIFIED
- execution log runtime visibility：NOT VERIFIED

## 執行規則

1. 一次只完成一個 Task。
2. Task 完成後回寫本文件。
3. 停下來向使用者報告 PASS / FAIL / NOT VERIFIED。
4. 使用者要求繼續後才進下一個 Task。
5. 文件、程式碼、CI、deployment、runtime 的狀態分開判定；不得用其中一層 PASS 代替整體 DONE。
