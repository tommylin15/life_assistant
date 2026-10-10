# Life — Acceptance (2026-10-10)

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
