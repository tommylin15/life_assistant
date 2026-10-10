# Life 活動精選池 — 最新唯一交接路徑（2026-10-10）

**APPROVED DESIGN：ChatGPT Chat 探索／核證 → Drive 精選池 → [獨立「交接資料」Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) → Life GCP 每日 Job → PostgreSQL 共用精選池 → Flutter。**

- 探索原始證據、去重和星等規則以 Drive 正式探索 01～05 為準；探索任務終點是**精選池 → 交接表 READY → 讀回驗證**。**以提前通知為優先**：具有可回查來源、穩定活動鍵及有據的活動日或開報節點即可交接，包含 1／3／5 星與「五星潛力待核」；即時名額、部分資格和費用未知不是一律阻擋。未知／衝突如實留白並在 evidence_summary 標示，不捏造或抹去疑義；已取消、確定過期及無可追溯來源者不交接。探索不連 Life API／DB。
- 固定 Google Sheet ID `1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4`，`交接資料` 為資料分頁，`交接規格` 定義 30 欄語意。**不是**舊精選池 45 欄 `精選活動` 分頁。
- Life 用一般 Python/Pydantic 讀 READY/ERROR、PostgreSQL 永久穩定 `event_key`／`content_hash` 去重 upsert，DB commit 且版本一致才寫 ACKED。探索端只清成功 ACK 超過 30 天的列，未 ACK 不刪；交接表不是永久資料庫。
- 原 direct ChatGPT bearer API 與既有 URL-based identity 暫留相容；目前 importer 可能仍讀舊精選池、僅 readonly，**不代表新設計已實作**。必須先補 ID mapping、Sheet 最小寫權限、真實 DB/ACK/UI 與 Scheduler 驗收。全部規則見 [Life 端唯一交接契約](curated_sheet_job_ingestion.md)。
- Life 不負責文化部／觀光署／官網／第三方網站探索或爬蟲，不做第二次 AI、舊候選 Queue／claim／lease、舊來源觀測／獨立二次發布，也不自動建立私人待辦／行事曆／通知。Drive 上游自行維護來源快照，不屬於 Life 爬蟲。

**狀態：設計核准，交接表已建立；Life 新 Job、定期讀取、資料庫去重及 ACK 實際整合仍 NOT VERIFIED。**
