# Life — Acceptance

## 2026-10-16｜01～03 本批驗收結案：PASS／DONE
- **01 定時匯入／資料一致性：PASS／DONE**。10/16 台灣時間 07:34:20 `life-assistant-free-events-ds4bq` Execution Completed=True；固定 Sheet 為 59 筆／58 ACKED／1 ERROR，07:34:15 五筆新 `CREATED`。以 [唯讀 #38825509671](https://github.com/tommylin15/life_assistant/actions/runs/38825509671) 的 `life-assistant-core-acceptance-xr6sq` 獨立比對該 5 筆 PostgreSQL 鍵、hash、來源版本與建立時間，Cloud Run Job 成功退出。正式固定 Job digest 已於 [V3 #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151) readback PASS。未再次執行 importer。
- **02 購物／待辦及 03 活動／Calendar：PASS／DONE**。使用者已於 10/15 明確確認兩項正式版人工驗收，詳見下方原始結案紀錄。
- **完成範圍與保留風險**：01 的 GAS 原始觸發 ID／Apps Script 單次紀錄未從 Apps Script 直接取得（NOT VERIFIED），但實際 07:30 附近的執行、五筆 ACKED 與 PostgreSQL 比對有 runtime 證據。1 筆 `invalid_handoff_record` 屬探索端來源品質，維持 `ERROR`，不假報 59/59 成功；獨立的 Gemini／Drive AI／運維待辦不受本批結案影響。


## 2026-10-15｜02／03 正式版使用者驗收結案（最新）
- **02 Shopping／待辦：PASS / DONE（人工功能驗收）** — 本輪預先定義的購物清單／品項各自修改與刪除、同一清單一次加入多品項、重新載入，以及待辦刪除不白畫面與相關權限操作。使用者於正式版發布後直接回報「02,03驗收完畢」。
- **03 活動探索／個人操作：PASS / DONE（人工功能驗收）** — 本輪預先定義的跨日搜尋及分頁、收藏、加入待辦／個人追蹤、Google Calendar 操作與讀回；依使用者同一回報結案。
- **證據區分**：機器端同一發布 SHA `6fdb4cf7e12f6c76d0b6955bc3f6e9325a5cbcce` 的 [CI #38730407125](https://github.com/tommylin15/life_assistant/actions/runs/38730407125)、[Cloud Run Release #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151) 與 [Firebase Hosting #38738435372](https://github.com/tommylin15/life_assistant/actions/runs/38738435372) 為 CI、runtime smoke 和正式部署 PASS；**使用者回報**是 02／03 真人操作的驗收證據。使用者未逐一提供測試帳號、 Calendar event ID、 API request ID、操作明細及每步截圖，故不作此類獨立機器核證聲明。
- **不包含（現行狀態更新）**：01 技術資料鏈已於 2026-10-16 PASS／DONE（見上方），僅 Apps Script 觸發 ID 及來源 ERROR 分別保留查核；其他獨立功能（例如登入後 Gemini UI、Drive AI 成本）依各自 gate 判定。更動 02／03 相關程式後照常回歸，不恢復本次已通過的人工 E2E 阻塞。


## 2026-10-15｜正式版真人驗收補正（現行）
- **Google OAuth 真人登入／授權／登入後正常使用：PASS**。由使用者明確回報已在正式發布版本操作並真人驗收無誤。
- **多使用者資料隔離：PASS**。由使用者明確回報已在正式發布版本真人驗收無誤。
- 驗收來源是**使用者正式環境操作回報**，非本次重新執行真人操作的工具紀錄；帳號數量、每個 API 的逐項矩陣及驗收當下精確 revision 未另附，不虛構。既有 production [Release #38572432707](https://github.com/tommylin15/life_assistant/actions/runs/38572432707) 與 [Hosting #38576667267](https://github.com/tommylin15/life_assistant/actions/runs/38576667267) 是部署證據，不假裝能獨立證明真人登入。
- **兩項從當前阻塞與高風險缺口清單結案**，不影響每次新版本的安全回歸，也不恢復人工 OAuth 發布阻擋。下方 2026-10-10 記錄為當時歷史快照，不得覆蓋本節。

## 2026-10-10 historical acceptance snapshot

## 本批開發與驗收安排（2026-10-10 最新）

- 新交接表、穩定去重、活動卡片、兩個入口及個人動作已在工作樹實作；開發驗證與 deployed／runtime 驗收分開記錄。細節見 [活動規格](curated_activity_user_features.md)。
- 活動能否開放一般使用者由 admin 在後台設定。AI 管理補強暫緩，僅 AI 管理相關能力限 admin；不把這項限制套用到全部新功能。
- 下一輪合併新活動功能、後台及個人首頁做正式上線驗收。真實 Sheet write scope／版本回執、GCP Job、Google Calendar 與新 SHA 的 CI／staging 尚待驗證；舊版測試站登入已完成。


## 測試站驗收更新（2026-10-10；優先於下方歷史快照）

- **固定測試站發布與真實 owner Google 登入驗收：PASS / 已完成。** [V3 run 38030697455](https://github.com/tommylin15/life_assistant/actions/runs/38030697455) 的 real database/auth、Preview、fixed staging preflight，以及「Promote exact Preview to independent fixed staging live and verify owner OAuth」均 success。使用者於本次對話確認 https://life-assistant-v3-stage-tl15.web.app 已能正常登入使用。
- 測試站 `release.txt` 實際讀回 `3fb06169ad01a065fef60eecc2010c459970746e`，與上述成功發布 SHA 一致。先前 wrong_callback、Missing session 與未驗收敘述是修復前歷史，不再列為目前登入 blocker。
- **後續版本發布是獨立狀態：** main `4219510cf2764c7b7bce9286ec2374d9ca36a1df` 的 CI success，但 [run 38037092043](https://github.com/tommylin15/life_assistant/actions/runs/38037092043) 在 real database/auth acceptance failure，尚未執行 Preview 或固定 staging 發布。不可據此把既有可用測試站改標 FAIL；也不可把測試站已驗收推定為最新 main 或 production 已發布。
- 下一步仍是新交接 Sheet → Life Job → PostgreSQL → ACK/ERROR 的實作與真實驗收，以及活動產品待辦；不要求重做已完成版本的測試站登入驗收。

**Overall PARTIAL.** Historic evidence: [archive](archive/acceptance_through_2026-10-09.md).

| Capability | State |
|---|---|
| Prior V3 GHCR release [37959057237](https://github.com/tommylin15/life_assistant/actions/runs/37959057237) | PASS for its previous SHA/gates |
| Old MoC/TDX/Queue/14-day observations / additional publication gate | CANCELLED — no longer a release requirement |
| Legacy ChatGPT task writing Google Sheets Queue | DISABLED |
| Old GitHub scheduled source workflows and crawler code | Removed from main; external GCP triggers NOT VERIFIED |
| Direct ChatGPT authenticated selected-item write / dedup / PostgreSQL | SOURCE IMPLEMENTED；新預設 Sheet importer 亦已實作；runtime NOT VERIFIED |
| Curated items GET and Flutter UI | SOURCE IMPLEMENTED / 新 SHA runtime NOT VERIFIED |
| Actual ChatGPT scheduled connector E2E | NOT VERIFIED |
| UI feature rollout / personal Home | SOURCE IMPLEMENTED / 真實後台與個人首頁驗收待整批進行 |
| Independent Life AI admin | 既有 admin 管理保留；補強暫緩，不阻擋本批驗收 |

New DONE requires actual code + regression+PG tests+CI+guarded V3 deploy+live API/DB/UI/connector proof. Do not delete the prior SQL migrations or data as part of cleanup.
