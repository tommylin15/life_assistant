# Life — Active engineering TODO
Updated 2026-10-16. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

| Priority | Work / exit gate | Status |
| --- | --- | --- |
| P1-G1 | **Gmail 手動快掃／三天補檢／收件匣輕量轉存**：[唯一規格](gmail_smart_radar_spec.md)。保留最近七天最新 20 封快掃；最近三天列出 ID 與已查／未查封數，手動 40 封一輪補檢（無冷卻、無排程、只記 ID 去重、不呼叫 Gemini）。卡片主要兩動作為原信與送 Life 收件匣；Gmail 信箱備援與手動處理移至「⋯ 更多」。Life 分類後需本人確認存入待辦／筆記／日曆／購物，後端只依已成功 inbox.create 回執標記 Gmail 已完成，重試共用穩定 action ID。已存項目目前連至功能**入口**，不是保證直達單筆；完整 entity deep link 仍待驗證。 | **PARTIAL**：同一程式 SHA `739e8d1` 四項 CI [#38990177498](https://github.com/tommylin15/life_assistant/actions/runs/38990177498) **PASS**，固定 Staging [#38990390261](https://github.com/tommylin15/life_assistant/actions/runs/38990390261) 的 Preview 精確 SHA／API 401／OAuth 自動 redirect 與 staging live readback **PASS**。真人 Gmail 授權、三天補檢、收件匣分類與目標 PostgreSQL readback、手機原信／備援及不同帳號隔離 **NOT VERIFIED**；正式新版未切換。 |
| P1-G2 | **唯一 Google Drive 檔案總管**：[正式規格](google_drive_file_manager_spec.md)。依 2026-10-17 決策移除「智能整理」使用者頁面，導航／`/more/drive` 一律為 Explorer；舊 `/more/drive/files`、`/more/drive/settings` 轉址。新增 Google Picker 選取更多檔案／資料夾、官方 Drive 全檔外開入口、限制說明；保留清單搜尋、分頁、原檔預覽／開啟、建立資料夾、改名、移動及小型文字編輯。原資料／筆記／專案關聯不刪除，舊 AI API 先保留不由 UI 觸發供相依審查。**drive.file 僅逐檔授權**，不宣稱可瀏覽全 Drive 或選資料夾即授權所有子檔案。 | **PARTIAL**：同一程式 SHA `739e8d1` 四項 CI [#38990177498](https://github.com/tommylin15/life_assistant/actions/runs/38990177498) **PASS**；Staging [#38990390261](https://github.com/tommylin15/life_assistant/actions/runs/38990390261) Preview／官方 Hosting 版本／API 401／固定站 live readback **PASS**，Cloud Run 正式流量未切換。本人 Google Picker 實際選取檔案／資料夾、手機讀回、原檔修改與筆記／專案關聯隔離 **NOT VERIFIED**；完整全帳號權限不擴張，上傳／複製仍未完成。 |
| P1-5 | **預設保持登入（Cloud Run 相容）**：將 Google 登入後短效 ID token Cookie 改成資料庫可撤銷、隨機 opaque Life session；建議同裝置 30 天、有感知的失效／重新登入、使用者主動登出即撤銷，不能只延長已過期 Google token。沿用 Firebase Hosting 的 `__session`、HttpOnly／Secure／SameSite、固定 staging 來源隔離及既有 Google per-user consent；先建立非破壞性 migration、權限測試／CI／真實 Google 瀏覽器 E2E，再發版。 | **NOT VERIFIED／尚未實作**：目前 `auth.py` 成功登入仍寫最長約 3600 秒的 Google ID token session；此項不能因日曆／活動 UI 提交而標 DONE。 |
| P1-6 | **2026-10-16 行程與活動視覺整合驗收**：月曆格狀及小圖示、點選日期摘要與詳情；單一活動探索入口／三模式、首頁及個人化去重、舊連結／rollout／收藏資料兼容。 | **PARTIAL**：Flutter source 已提交 main，新增 nav／主活動分組及月曆選日詳情 widget 測試；本 SHA 的 Flutter analyze/test、4 項 CI、staging、正式 Hosting 及真實 Google Calendar 操作 **NOT VERIFIED**。 |
| P1-1 | Complete **signed Gemini through logged-in Life `/ai/text` and UI** including 429/502/503/timeout, permission/quotas and no implicit Google Drive content transfer. | Signed synthetic smoke **PASS**, UX E2E **NOT VERIFIED** |
| P1-4 | **已取消獨立 Drive AI 管理產品**：不再新增 Drive AI admin／個人 AI 智慧整理 UI、模型成本管理；僅保留為了歷史資料及舊 API 相容所需的既有程式／資料，後續確認無其他依賴再安全移除。 | **PRODUCT CANCELED／COMPATIBILITY RETAINED**：不可刪除使用者檔案、資料庫紀錄、筆記／專案的既有關聯；不可從新檔案總管觸發 AI。 |
| P2-2 | Audit dependency/action pinning, public-repository hygiene, access to operational docs, observability, backup restoration and scheduled-job dedupe. | Risk follow-up **NOT VERIFIED** |


## 2026-10-17｜本輪合併交付及一次整合驗收（唯一驗收矩陣）

使用者決定：P1-G1 Gmail、P1-G2 Drive 檔案總管、P1-5 30 天登入、P1-6 月曆／活動整合、P2-3 生活收件匣及日期萬年曆 **同版完成後一次驗收**；不逐項邀請真人重驗、不提前開啟 Gmail/Drive AI 自動排程、不為取消的 Drive AI 再增加新功能。已通過的既有 01–03 正式版驗收不重做。

| Gate | 同一 main SHA 的整合驗收範圍 | 判定 |
| --- | --- | --- |
| 1 Implementation / Tests | Gmail 九類及第三方授權警示／快掃／三天補檢與重判／Inbox 轉存與 receipt；Drive Picker＋檔案讀寫／逐檔 scope；登入 Session 30 天／登出撤銷；月曆＋活動入口；生活收件匣日期解析、萬年曆與 FAILED/UNKNOWN 分流；四項 CI | **待本次整合 commit CI 讀回** |
| 2 Staging | 完整同 SHA CI、候選 0%／遷移／獨立固定 Staging Flutter+API SHA/readback、Google OAuth redirect、資料庫與權限 smoke | **待同 SHA V3 readback** |
| 3 真實外部整合 | Owner 與一般帳號 Gmail 重新授權、近三天郵件快掃／40 封重判／原信／Life 轉存；Google Drive Picker 檔案與資料夾、編輯版本讀回；生活收件匣複合項目→Task/Shopping/Note/Google Calendar 真實寫入、PG／Calendar 讀回與重試；跨帳號拒絕；瀏覽器關閉重開的 30 天 Session／登出 | **NOT VERIFIED（需要實際帳號與 Google 授權）** |
| 4 Production | 通過固定 Staging 後受控 V3 promote、postdeploy live gate、rollback、Job digest、Hosting 同 SHA 發布與正式讀回 | **NOT VERIFIED；不能以 staging success 代替** |

嚴格以 PASS / FAIL / NOT VERIFIED 標示；只有 1–4 所需證據完整才標 DONE。Drive 上傳／複製／全雲端硬碟存取、Gmail 自動排程與安全事件真偽保證**不在核准的本批範圍**。單筆 entity deep link 尚未實作時，按鈕僅宣稱「開啟功能」，不能宣稱「開啟該筆」。

**P1-5 舊狀態更正**：最新 `backend/app/api/auth.py` 已實作 `LifeLoginSession` DB 雜湊 bearer、30 天 Session、Staging/Production 來源隔離、logout 伺服器撤銷；原表「尚未實作」為歷史快照。`backend/tests/test_life_login_session.py` 與 `backend/tests/test_auth.py` 已涵蓋核心流程，仍須同 SHA CI、真實登入與正式發布驗收，不得將 source PASS 等同產品 DONE。

## P2-3｜生活收件匣 V1 已開發、CI 與 Staging 通過（2026-10-16）

| Priority | Work / exit gate | Status |
| --- | --- | --- |
| P2-3 | **Life 生活收件匣＋快速新增＋筆記網址摘要**：已實作獨立 Gemini `life_inbox` 路徑、文章摘要、錯誤診斷及用戶確認寫入；本輪 CI/CD 效能重構修復版 `2cfe1c9` 已通過四項 CI、固定 Staging 與使用者人工操作。**2026-10-17 日期簡化增修**：待辦與 Calendar 原本需手打 ISO8601，已改萬年曆與時間選擇器；公曆／民國、完整日期、只有年月／只有月日及今天／明天／後天以精度線索處理，缺值不造假。日曆全日結束日由 UI 自動做 exclusive 換算，待辦無時間僅作明示的 23:59 當日截止。見[規格](life_inbox_quick_capture_spec.md)。**未逐項確認的剩餘 gate**：本次四 CI／同 SHA Staging／真人手動日期選取與真實 Google Calendar／PG 讀回，以及複合語意分類、多項確認、收據重送、管理員 rollout、跨帳號拒絕矩陣、正式版發布。 | **既有 2026-10-16 基準：IMPLEMENTATION/CI/STAGING PASS，真人操作 PASS（使用者回報），細項 E2E PARTIAL；2026-10-17 日期增修：IMPLEMENTATION 已提交，最新四 CI／Staging／真人日期與 Google Calendar readback 另行追蹤，均不得沿用舊 PASS 判定**。[CI #38886583192](https://github.com/tommylin15/life_assistant/actions/runs/38886583192)、[Staging #38886894486](https://github.com/tommylin15/life_assistant/actions/runs/38886894486) 同 SHA `2cfe1c9` PASS；Production 未切流、一般使用者全面開放未驗收。 |

**02／03 使用者正式版人工驗收：PASS／DONE（2026-10-15）**。使用者明確回報「02,03驗收完畢」：02 購物清單／品項修改、刪除、批次新增、重載及待辦刪除不白畫面；03 活動跨日搜尋／分頁、收藏、個人待辦／追蹤及 Calendar 操作與讀回。已從 active backlog 移除 P1-2／P1-3；正式版操作是使用者回報，非自動化每條 API log。原有 CI/正式部署證據分開保留見 [acceptance.md](acceptance.md) 與 [CURRENT_STATE.md](CURRENT_STATE.md)。**01 已於 2026-10-16 由真實 Execution + Sheet／PG 版本比對 PASS 結案**。

**01–03 本批全部 PASS／DONE（2026-10-16）**：01 匯入器 [Execution ds4bq](https://console.cloud.google.com/run/jobs/executions/details/us-central1/life-assistant-free-events-ds4bq?project=gen-lang-client-0593591102) 2026-10-16 07:34:20 台北時間成功，Sheet 59 筆／58 ACKED／1 ERROR；[PostgreSQL readback #38825509671](https://github.com/tommylin15/life_assistant/actions/runs/38825509671) 精確比對本輪 5 筆新 ACKED 版本全部 PASS；02／03 使用者正式版人工驗收 PASS。**01 已從 active backlog 移除**。Apps Script Trigger ID 未直接核證、來源單筆 ERROR 屬獨立可觀測性／資料品質追蹤，不作為本批功能結案的阻擋。

**01–03 正式部署／Hosting：PASS（2026-10-15）**：[V3 #38734655151](https://github.com/tommylin15/life_assistant/actions/runs/38734655151) 完成 production promotion、回滾演練、importer Job 映像同 digest；[Hosting #38738435372](https://github.com/tommylin15/life_assistant/actions/runs/38738435372) 同 SHA live readback PASS。這只關閉部署 gate，不代替 GAS 同輪匯入或使用者 E2E。

**01–03 開發／PostgreSQL／Staging 最新驗收：PASS（2026-10-15）**：同 SHA `8d27207` [CI #38719801492](https://github.com/tommylin15/life_assistant/actions/runs/38719801492) 四項 PASS；[V3 #38720078074](https://github.com/tommylin15/life_assistant/actions/runs/38720078074) 固定 Staging PASS、活動交接 DB 檢查 + Shopping rollback-only runtime PASS，修復了舊 [#38715747623](https://github.com/tommylin15/life_assistant/actions/runs/38715747623) 的新驗收失敗，production traffic unchanged。上表僅保留尚待核實的外部來源與系統整合事項；P1-2／P1-3 已經使用者正式人工驗收 PASS 並自 active backlog 移除。

**Closed / removed from active blockers:** P2-1 Revision 清理 **PASS**（68→10、刪 58、未刪 Service/Job、live unchanged），證據見 [Release #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751)。P0/P1 CI/CD workflow 收斂 **PASS**（同 SHA CI + staging）。

**Accepted / removed from active blocker list (2026-10-15):** production Google OAuth human sign-in and production multi-user data isolation — both **PASS by user-reported live human acceptance**. Do not reopen solely because workflow artifacts do not include a human interaction log. Keep automated OAuth and tenant-ownership security tests. See [acceptance](acceptance.md).

**2026-10-15 P0/P1 CI/CD 收斂：DONE（有 CI/staging/真實 GCP readback 證據）。** 已歸檔 8 個過時 workflow（29→21），保留四項 CI gate；純文件修改不自動 staging；Gemini synthetic smoke 改按需執行。最後 main 程式 SHA `23d898c` 的 [四項 CI #38674814026](https://github.com/tommylin15/life_assistant/actions/runs/38674814026) 與 [staging/retention Release #38675052751](https://github.com/tommylin15/life_assistant/actions/runs/38675052751) **PASS**；GCP 讀回 **68→10**、刪除 **58**、正式流量不變、四個 Life Jobs 均未刪除。此 DONE 不涵蓋其他功能尚未驗證的 Live E2E。

Release reference: [latest verified original source SHA and actions](CURRENT_STATE.md). New `main` documentation commits start a new SHA and do not inherit production evidence. A standard `main` push runs the four CI jobs and staging-only flow; production promotion has its distinct manual V3 release gate. Do not run a second importer on top of GAS without checking the execution ledger.