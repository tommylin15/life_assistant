## 2026-10-28 更新：原版已找回

原版位於 `/workspace/scratch/ce8451bfc5e6/life-line`；檔案 SHA256 見 [manifest](evidence/line_original_manifest_20261028.json)，原始內容見 [patch](archive/line-original-20261028.patch)，重跑 153 項（LINE 15 項）收據見 [test log](evidence/line_original_tests_20261028.txt)。Owner 明確指定我們這版優先，已解除下方歷史復原停止線。整合僅新增 0024，保留 0023 及其他 main 改動。

# LINE 方案 B｜前次已測試版本復原證據與隔離決策（2026-10-28）

## 使用者決策與停止條件
- 唯一希望延續的工程基線是前次對話「LINE整合方案評估」中實際已開發與測試的原版；後次「接續工作」重新實作的成果不納入正式完成清單，亦不得當作已測試原版繼續擴寫。
- **復原先於回退**：須先取得原版真實 source/artifact、路徑/commit/SHA、可重跑測試輸出或測試檔，才能比對後有界恢復。不能僅憑前次助理回報 153/15 項通過，就把不同程式宣稱同版測試 PASS。
- 在前次原始版本未定位前，不做 `main` reset／rebase／force push、不移除已提交檔案、不對任何 DB 執行 downgrade/DELETE、不部署或啟用 LINE bridge。

## 真實查核收據
1. **歷史對話**：2026-10-28 前次 LINE 方案 B 開發過程確曾回報後端 synthetic tests **153 PASS，其中 LINE 15 PASS**；未提供或未能恢復可直接讀取的程式碼檔案、git commit SHA、log artifact、精確測試命令。這不是與目前 main 同版的驗收證據。
2. **GitHub baseline**：後次第一個 LINE commit `4d6dbe58674af6ce59a0840dd7d9541e88d4743c` 之前的 `main` commit [`56275487`](https://github.com/tommylin15/life_assistant/commit/56275487ee120bba75965011d15715d937a055fe) 完整 git tree 共 765 entries，未見 `line_bridge`、`liff`、`webhook` 等 LINE 專項檔名。現存其餘 GitHub 分支 tree 也未見此類原始檔。
3. **Drive**：限查授權根 [life_assistantGPT](https://drive.google.com/drive/folders/1k6l41gjglDRphjMY5oJOlWe1bL0bnMLF) 及其可見「歷史文件」「討論構想區」子資料夾；查無可辨識的前次 LINE 原始碼或測試 artifact。Project/Library 文件搜尋亦未找到匹配檔案。現階段的工作環境 `/mnt/data` 無保存前次原始碼。
4. **後次 GitHub 改動**：[`56275487...a21979c` 比較](https://github.com/tommylin15/life_assistant/compare/56275487ee120bba75965011d15715d937a055fe...a21979ced73e46d3341fd857e0358e7ddfbf8f0b) 顯示 24 commits、18 files；除 LINE API、models、migration 0023、LIFF、測試、文件、release revision 修改外，**同區間另有獨立的 `scripts/import_snapshots_to_curated.py`**，不得整體回到舊 SHA。
5. **目前後次 CI**：[`#40616784019`](https://github.com/tommylin15/life_assistant/actions/runs/40616784019)，HEAD `a21979c`，整體 **FAIL**；Backend 743 tests、1 failure、22 skipped，唯一 failure `test_v3_curated_release_gate.CuratedV3ReleaseGateTests.test_0018_migration_runs_before_live_traffic_without_retired_job`：測試仍 assert `gmail_v2_db_readback=PASS revision=20261019_0022`，但目前 release workflow 文件已改為 revision 0023；其他 CI jobs（Flutter、Deployment Scripts、Free Events PostgreSQL、Gmail ONNX image）為 success。**不**把舊 153 PASS 視為目前 743 測試 PASS。
6. **執行環境/部署**：LINE staging、LINE Console 真人 OAuth/Webhook、production 及 migration 是否真正執行：NOT VERIFIED。本輪未修改 runtime、secrets、IAM、DB；LINE feature 開關依 source 預設 false，但部署環境實值未讀回。

## 狀態矩陣
| Gate | 結果 |
| --- | --- |
| 前次原版存在於歷史工作回報 | PASS（只有對話報告） |
| 前次原版 source / SHA / artifact 恢復 | **NOT VERIFIED／BLOCKED** |
| 前次測試 153/15 可重跑證據 | **NOT VERIFIED／BLOCKED** |
| 後次 main diff/與他案隔離 | PASS（靜態 Git 證據） |
| 後次當前 CI | **FAIL**（上述 run） |
| 直接回退／替換 GitHub 程式 | **NOT RUN，刻意暫停** |
| staging/runtime/真實 LINE 整合 | **NOT VERIFIED** |
| 正式 LINE 交付 | **PARTIAL，非 DONE** |

## 原版取得後的唯一可執行 WI
WI-REC-01：取得前次完整原始碼與 15 項 LINE 測試（版本、路徑、內容 hash、測試依賴／命令／報告），在隔離環境核實且不使用私密實際 LINE 憑證。
WI-REC-02：使用 GitHub main 最新 SHA 與前次版本逐檔對照，列出 API/router/model/LIFF/schema/migration/CI/文檔差異；保護同期間非 LINE 的快照匯入改動，辨認 0023 是否僅存在 source 或已被 staging/prod DB 套用。
WI-REC-03：若原版已確認可恢復，採 additive/forward-only migration 相容策略，正常 git commit 有界移除後次重寫，恢復原版實作和原版測試，新增僅限不可避免的適配層。未核對 DB 狀態前，不執行 Alembic downgrade。
WI-REC-04：跑同 SHA targeted tests → 五項 CI → staging readback → 交使用者完成 LINE OAuth、Webhook、Rich Menu 真實 WI；沒有 runtime 整合證據標 NOT VERIFIED，正式發布只能在 gate 成功後獨立核准。

**當前唯一下一入口：定位前次可讀 source/artifact 與測試證據。無檔案時不得依後次版本繼續產品開發。**

