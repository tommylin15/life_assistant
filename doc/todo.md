# life_assistant — Active TODO

最後更新：2026-10-08

> 本檔只保留**目前 active / next / non-blocking backlog**。正式封板進度以 `progress.md` 為準；完成條件與 runtime evidence 以 `acceptance.md`、GitHub Actions 與 deployed runtime 為準。不要在本檔維護另一套歷史完成清單。

## Current

### CI/CD V3 實作與 GCP/AR/GCS 清理驗收（2026-10-08）

- 目前實際驗證：完整 CI 和 GCP WIF 唯讀資源盤點 PASS；首次 V3 Release 的 runner 因 Trivy action 引用錯誤而在 Set up job FAIL（沒有 Docker push、Cloud Run deployment 或 GCS/AR 刪除）。已改用官方有效 `aquasecurity/trivy-action@v0.36.0` 並重新安排受控 release；結果以後續 Actions readback 為準。


- 使用者核准先切換 GitHub Actions → 公開 GHCR 固定 digest → Cloud Run 0% candidate → Firebase Preview → 正式流量與回滾驗收；成功後才停用兩個舊 Cloud Build triggers。舊 release 路線在切換成功前保留。
- 新增 CI main push 完整測試、V3 manual release、GHCR scan/publish、候選/Preview/live gates、十版 revision fail-closed 清理、read-only GCP 清冊與受控 triggers disable workflow。**部署/實際驗收要由 Actions 執行紀錄證明，不因 workflow 進 main 就宣稱 DONE。**
- 刪除範圍限已逐項證明無依賴的舊 GCS CI/CD 檔案、CI/CD 專用且無備份/應用資料的 bucket、失去所有 live/job/回滾依賴的 AR image/digest、確認全庫無共用後的 AR repository。備份/業務資料絕對保留；見 `v3_cleanup_and_cutover_inventory.md`。
- **本輪 GCP 讀回、Cloud Run 真實流量/rollback、10 revisions 實際刪除、triggers disable、GCS/AR 刪除都需個別列 PASS / FAIL / NOT VERIFIED。**

### CI/CD V3 — 已核准新設計、等待實作與全鏈驗收

**本輪範圍：文件先行，NOT DEPLOYED / PARTIAL**。正式設計以 `ci_cd_ghcr_release_policy.md` 為準：GitHub Actions 完整測試 → manual full-SHA GHCR 公開映像發布 → Cloud Run 固定 digest 0% 候選 → Firebase Preview / 真實 acceptance → promotion / rollback。新流程禁止 Cloud Build 呼叫及主動 GCS/Artifact Registry 寫入；歷史 Cloud Build 僅獨立 WIF 唯讀診斷＋遮罩 Actions logs。Cloud Build V2 操作文件保留歷史追溯，不再作為未來 release target。

**新增核准 retention 規則**：Cloud Run `life-assistant-api` 保留最新 **10 個 Revision**（非 2）；候選／正式驗收期間暫時可超過，只有 promotion 與 live gates PASS 後才能於 release Pipeline 最後安全清理。不得刪目前流量、rollback baseline 或 active candidate，且 GHCR digest 另需保留。執行與 runtime **NOT VERIFIED**。

下一輪：盤點／取代現有 Cloud Build V2 triggers 與舊 GitHub Actions 發布入口；建立 Actions tests、公開 GHCR package / immutable digest、診斷與部署分離的 WIF、Cloud Run candidate / rollback 和 Firebase Preview gates。**本輪沒有停用舊 trigger、沒有修改 IAM 或部署**。保留上述 V2 cancelled candidate 與 runtime history 於 `acceptance.md`；不得把它算成 V3 PASS。

### Paused after #7 — per user instruction

狀態：**#7 Shopping = DONE / PASS；7/11 = 63.6%**。本對話不啟動 #8。

獨立 cross-feature health：歷史 #63 / run `37625447402` exit `91` = Gemini only；更新一輪 #70 / run `37702785541` exit `93` = Gemini + OpenRouter，Groq 不在 failure mask。此項保持 OPEN，不影響 #7 的直接完成證據。Diagnostic candidate `8dedf655` 已加入分別測試，CI #574 PASS；新 deployment / live acceptance 尚待驗證。

## Just Closed

### #7 — Shopping 完整產品化

狀態：**DONE / PASS**；closure progress **7/11 = 63.6%**。

- final release `1dd0b1f15827ae9cf50a8f4fcb69a1fa3782f40d`。
- CI #566 / run `37621843816`、Firebase #384 / run `37622140411`、Cloud Run #438 / run `37622140547`、Shopping UI #4 / run `37622504893`、Post-deploy Runtime #104 / run `37624483194`：PASS。
- Shopping list/create item/category/toggle/progress、responsive UI、More navigation、mobile/desktop production acceptance、真實 PostgreSQL persistence evidence 完整。
- 詳細 evidence 見 `progress.md`、`acceptance.md`。

## Next

1. **#8 — Calendar 完整產品化**：依 `doc/calendar_productization_checkpoint_v0_1.md` 的 implementation / tests / CI / deployment / runtime / true Google account / mobile+desktop UI gates 完成封板；不能因規劃新需求降低 Calendar gate。最新狀態須依 GitHub/runtime evidence，不沿用本檔較舊的「NOT STARTED」快照。
2. **日曆後第一優先（P0 after Calendar）— 台灣免費活動探索與報名追蹤**：**APPROVED PLAN / NOT IMPLEMENTED**；[分階段完整規格](taiwan_free_events_discovery_plan.md)。MVP 順序：**M0 來源時效／授權 14 天觀測 → M1 Event/Session/Registration Opportunity、來源與安全/去重 → M2 Flutter 候選清單及 admin-only 健康 → M3 通知/待辦/筆記獨立操作及 Google 整合 → M4 GCP 每 12 小時正式排程切換**。接續 **E1**：主辦單位追蹤、進階偏好、摘要/靜音、報名狀態；**E2**：貼連結、交通距離、電子報來源與進階個人化。正式 GCP 定時工作尚未建置，ChatGPT 06:00/18:00 只是過渡；每個階段都不得以文件當作 deployment/runtime PASS。
3. #9 — Activity / Execution Log + Integrations productization（保留，延後於上述新項目）。
4. #10 — Integration / foundation tail closure（保留）。
5. #11 — Phase 1 final Release Gate / 封板 checkpoint（保留原有必需驗收、不跳過）。

> 本優先級異動由 `phase1_delivery_order.md` 單一正式排序文件維護。新增 Post-Calendar 工作軌不重算原 11-package 已完成比例；正式納入 release blocker 與否須另依 scope freeze 治理明示。

## Non-blocking backlog

以下仍需完成，但只有在成為直接 dependency 或進入對應工作包時才提升優先級：

- Attachment central storage/reference strategy。
- versioned Bridge / MCP API contract。
- Bridge/MCP input/output schema、proposed action、permission / confirmation、idempotency 與 failure evidence 完整化。
- 真實 Google provider failure / Drive partial-success 驗收。
- 真實帳號 Calendar read/list 重驗。
- 真實歷史 SQLite migration：只有在實際 legacy SQLite source file 可定位時執行。
- Artifact Registry latest-only retention 的最終 physical inventory evidence。
- Drive Knowledge provider-health regression：#63 exit `91`（historical Gemini-only），#70 exit `93`（Gemini + OpenRouter），均仍為歷史 FAIL evidence。Codex-first consumer adapter 已在 main 送 CI/runtime 驗收，completion 為 PARTIAL。只呼叫 omniAgent 私有 shared Cloud Run；其認證由共用服務專屬 `omniagent-shared-codex-auth` 管理，life_assistant 不新建、不讀取、不複製任何 Codex Secret，舊 `janus-mart-codex-auth` 不作為消費端來源。

## Product DONE 規則

使用者功能至少要依工作包需求具備：

1. implementation
2. tests
3. CI
4. deployment
5. runtime / integration
6. UI entry + 可操作 flow
7. mobile / desktop UX acceptance

Backend-only PASS 可標 foundation PASS，但不能等同產品功能 DONE。
