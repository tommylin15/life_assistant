# Life 活動精選池 — 唯一現行流程（2026-10-10）

**最新核准方向：ChatGPT → Drive 精選池表 → GCP 定時 Python Job → PostgreSQL → Flutter。**

Google Drive 指定原生試算表只當 ChatGPT 精選結果的**交接站**，不是 PostgreSQL 的替代資料庫。GCP Job 透過 Sheets API 唯讀取得已選活動，Python 使用現有欄位與後端驗證、穩定去重鍵和 upsert，**不使用第二次 AI 分析**。完整欄位、安全閘門和驗收見 [精選池 Sheet 匯入契約](curated_sheet_job_ingestion.md)。

舊 TDX／文化部擷取、官網清單掃描、Queue/ACK/claim、Cloud Run source crawler 與 14 天來源觀察持續取消；**這次僅新增已精選 Sheet 入庫 Job**，不得重新啟動來源爬蟲。不得以 Excel 草稿、未核准、取消或過期狀態冒充已上架資料，不建立個人任務／行事曆／提醒。

目前 GitHub 程式與部署驗收各自判定：程式存在不等於 Cloud Run Job 已部署，也不等於真實 Drive、PostgreSQL、Flutter readback PASS。
