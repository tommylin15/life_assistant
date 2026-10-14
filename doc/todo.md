# Life — Active TODO（2026-10-14；01～07 同批）
本檔是唯一現行工程待辦入口；歷史狀態及執行證據見 [CURRENT_STATE](CURRENT_STATE.md)。**所有未通過的整合驗收維持 PARTIAL / NOT VERIFIED；不要因本次推送就標 DONE。**

| 順序 | 範圍 | 已查證與剩餘門檻 |
|---|---|---|
| 01 | 活動 GAS→Job→PostgreSQL→Sheet ACK/ERROR | 2026-10-14 正式 release #38502483297 將 importer Job pin 到 live digest；**該 Release 不執行匯入**。舊 Execution 52 ACKED / 2 ERROR；新版本需手動 Job Exit 0、Sheet/DB 版本 readback，GAS 07:30 trigger 另驗 |
| 02 | Life→omniAgent Gateway→Gemini Flash-Lite | 10/13 Signed Smoke #38376914628 PASS；10/14 #38500240196 Job FAIL，原因尚未從該 Cloud Run Execution 安全讀回；再跑最新同版 signed smoke 並檢查 synthetic response；**登入使用者 API** 仍另驗 |
| 03 | 正式一般帳號隔離 | 2026-10-14 V3 Release 的 `run_private_ownership_acceptance` 在真實 PostgreSQL rollback-only PASS；真人跨 Owner／第二／第三帳號互相讀寫仍 NOT VERIFIED |
| 04 | 活動 V3 的多日、搜尋、5+10 分頁、收藏映射 | 已有 Flutter／API 主流程；持續補跨日速查、舊收藏和資料更新時 offset drift；PG 多人操作／Google Calendar 真實回讀須獨立驗 |
| 05 | Life Drive AI 管理 | 原已有 Provider 控制、健康探針、用量筆數；本次顯示分 Provider 結果，**Token／成本及預算不可推估**，實際多 Provider 與 budget gate NOT VERIFIED |
| 06 | Cloud Run revisions 留 10 個 | 2026-10-14 Release 清理結果仍 60、`PARTIAL_PROTECTED`；新增受保護原因唯讀診斷，不移除 tag、不強行刪除、不改正式流量 |
| 07 | GitHub 文件與 Issue 收斂 | 按本檔及 CURRENT_STATE 更新，不重複舊 10/10 待辦；Issue #10 direct-API 描述已由現行 Sheet Job 契約取代，暫保留追溯 |

**同批測試策略：** 將程式、測試、部署診斷與文件在一個 main commit 交付；先由 push 觸發四工作 CI，再由既有流程走 staging-only，同時一次性受控 workflow 核對正式 live digest 並可手動等價執行既有匯入 Job；該工作流 **無 cron / 無 production promotion / 不動 IAM**。正式發布仍需獨立符合人工 workflow_dispatch 門檻。不可用 staging PASS 推定正式生產新 SHA PASS。

**範圍排除：** 取消的人工作業 OAuth 驗收不恢復；自動 OAuth 安全檢查仍維持。Life 不重開活動 crawler、Queue、MCP 替代匯入、第二輪 AI，不把本次研究內容視為正式功能。
