# life_assistant — Data Model Entry Point (2026-10-10)

**現行欄位與 migration 以 GitHub 原始碼為準**，這裡只記系統邊界和新核准的語意，避免留下重複／過時 schema 和「已實作」清單。過去 SQLite/早期 PostgreSQL 欄位盤點已存放 [historical data model](archive/data_model_legacy_2026-10-10.md)，僅供稽核，不是現行 DB schema。

- Cloud operational store：PostgreSQL；現行 models 在 `backend/app/models/`，Alembic 在 `backend/alembic/versions/`。Runtime migration 是否套用必須獨立驗證。
- 已有 source：Alembic `20261010_0015_curated_ui_ai.py` 建立 `curated_activities`、`feature_rollouts`、`user_ui_preferences`、`life_ai_policies`。前兩者相關 endpoints 見 `backend/app/api/curated.py` 和 `backend/app/api/ui_policies.py`；這不是部署成功證據。
- **共用精選實體**：現有 `identity_key`（canonical original URL + occurrence_key）、來源、標題、日期、地區、費用、benefit、`importance`、`registration_required`、`registration_status`、`limited_offer`、`registration_deadline`。不能將重要性等於分類或自動聲稱還有名額。
- **使用者自己的記錄（新增需求，尚未實作）**：以 `user_sub` 為權限邊界，設計對 curated identity 的收藏／追蹤、個人報名進度、預警偏好與發送記錄、與待辦/行事曆的 idempotent linkage、行程候選。預設不產生任何個人記錄，必須由使用者明確操作；不准跨帳號存取。設計時需區分「報名行動時間」「活動範圍標記」「確定行程」，含時間區／來源可信度／失敗狀態。
- **活動/場次**：一個精選活動可在限時機會與活動探索交叉呈現；既有 `occurrence_key` 可區別同網址場次。未來若導入母子關聯／open-at／庫存條件，需正式 additive migration 與 API contract；不要只靠目前的 `registration_deadline` 假造開放時間。
- **個人 UI 政策**：現有 `user_ui_preferences` 是個人導覽/首頁偏好，不等於精選池追蹤/通知資料；`feature_rollouts` 是共用釋出政策，不含個人同意。

產品語意唯一詳述：[精選池使用者功能](curated_activity_user_features.md)；當前 ingress/API：[direct curated contract](free_events_candidate_ingestion_contract.md)；實作／部署狀態：[CURRENT_STATE](CURRENT_STATE.md)。所有 DB 寫入都需 idempotency、授權和適用 audit；不得 destructive migration。
