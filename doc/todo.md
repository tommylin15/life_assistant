# Life — Active engineering TODO
Updated 2026-10-20. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

## 2026-10-21｜快速新增 P0–P1 混合事項拆解（ONNX P2 取消）

- **P0／P1 已提交程式待驗收：** 規則快速解析多件明確事項、擴充繁體中文購物分隔詞；Gemini 逐項拆解並補足可驗證遺漏；每個候選獨立日期依據，未提供的結束時間／日期不臆測；Flutter 顯示多項且分別勾選後才提交。完整規格見 [快速新增](life_inbox_quick_capture_spec.md)。
- **P2 ONNX 試點：CANCELLED**（使用者決策）。本功能不載入 Gmail ONNX 模型，不新增 Cloud Run 推論服務。
- **工程子項 DONE／PASS（2026-10-21）：** 同 SHA `5f41a86b0a210971d73467f409fb654746f13630`，Backend／Flutter／PostgreSQL／Deploy 四 CI [#39515249836](https://github.com/tommylin15/life_assistant/actions/runs/39515249836) PASS；V3 候選、固定 Staging、API/DB/OAuth 及 Flutter Preview [#39515593787](https://github.com/tommylin15/life_assistant/actions/runs/39515593787) PASS。此次僅 Staging，不切正式 Production。
- **仍需人工驗收（NOT VERIFIED）：** 使用者以混合事項測試 Gemini 複合拆解／補選行事曆結束時間／選購物清單／確認後各功能真實讀回；在真人通過前此產品交付仍 PARTIAL。

## 2026-10-20｜Gmail 手機 UI 精簡：Production 正式發布 DONE

- **已結案範圍：** 快掃 + 更多選單、統計預設收合、待處理優先、已完成／已忽略狀態選單、郵件詳情收合、歷史八筆分頁，未更動 Gmail 個人資料或事項狀態。來源 SHA `64cfecaec5e62fe4d77f5f94250ad154c4c7a0a5`；[四項 CI #39418261130](https://github.com/tommylin15/life_assistant/actions/runs/39418261130) PASS；[ONNX Staging-only #39418591499](https://github.com/tommylin15/life_assistant/actions/runs/39418591499) PASS；使用者 2026-10-20 回覆「驗收完成」，人工手機 UI 驗收 PASS。
- **Production 正式發布 DONE：** 發布 SHA `555313e49517ae46976b6aaee0a489dc95b2a605`；四項 CI [#39436008511](https://github.com/tommylin15/life_assistant/actions/runs/39436008511) PASS，單次批准發布橋接 [#39436008563](https://github.com/tommylin15/life_assistant/actions/runs/39436008563) PASS，V3 Cloud Run 正式切流／健康與授權／rollback [#39436374275](https://github.com/tommylin15/life_assistant/actions/runs/39436374275) PASS，同 SHA Firebase Hosting 正式發布／readback／Task 與 Project UI [#39437588640](https://github.com/tommylin15/life_assistant/actions/runs/39437588640) PASS。URL：https://gen-lang-client-0593591102.web.app/ 。
- **範圍界線：** UI 精簡已上線；Production 仍採 rules-only（`enable_gmail_onnx=false`），未發布 ONNX。真實 Gmail 漏判／誤判、跨帳號 Gmail-to-Inbox 與 ONNX p95/RSS/正式切流均依下節 Gmail V2 既有 P0/P1 收尾，無新增排程或外部 AI。

## 2026-10-20｜Gmail V2：ONNX 已接完整 Life Staging；產品仍 PARTIAL

- **決策不變：** Gmail 雷達採規則＋Life 本地多語言 ONNX＋本地欄位抽取，原信不外送 Gemini／omniAgent；僅手動掃描、七天補檢、郵件去重、本人確認，無背景掃描與自動寫入。正式 [Gmail V2 規格及證據](gmail_local_v2_delivery.md)。
- **ONNX 獨立候選＝DONE：** [同 SHA CI #39349455453](https://github.com/tommylin15/life_assistant/actions/runs/39349455453) 四項 PASS；[GCP 模型候選＋Job #39349455587](https://github.com/tommylin15/life_assistant/actions/runs/39349455587) PASS；[IAM/Ingress readback #39350332042](https://github.com/tommylin15/life_assistant/actions/runs/39350332042) PASS。服務 life-assistant-gmail-onnx-candidate：2Gi RAM／2 vCPU／並行 1／實例 0–1／internal ingress，不接受任意郵件、不連 Gmail、DB 或 Gemini。Cloud Run 同映像 digest 執行合成模型 Job PASS；正式 Life API 的非零加權流量前後一致。
- **P0｜完整 Life Staging 部署 PASS（工程子項 DONE）：** [CI #39353419852](https://github.com/tommylin15/life_assistant/actions/runs/39353419852) 四項 PASS，SHA `faa8f5b80e8c5724d8b9759cc71d794d73e75082`；[V3 #39353638014](https://github.com/tommylin15/life_assistant/actions/runs/39353638014) 完整 ONNX FastAPI 0% 候選 + `/ready` 顯示 `local_semantic_ready`、DB／OAuth／Gmail 401、Alembic 0022、Firebase Preview、固定 Staging Hosting 同 SHA 全 PASS，production 流量不變；正式切流、真人 Google session、完整 FastAPI p95/RSS、rollback drill 仍 NOT VERIFIED。測試站：https://life-assistant-v3-stage-tl15.web.app/ 。
- **P0｜真實 Gmail E2E（未完成）：** Staging 的 Owner／一般帳號實際授權、七天補檢、漏判帳單重新辨識、已繳清／促銷排除、時間與繳費額證據、Gmail → Inbox **本地**轉存、跨帳號隔離和正式資料庫回執；不得將真實 Gmail 內容寫入公開 CI 日誌。
- **P1｜正式上線（未完成）：** 完整 Staging 真實 E2E 後，正式 Cloud Run／Hosting 同 SHA、安全切流與 rollback rehearsal、一般使用者畫面讀回。
- **治理分案：** 舊公開 Git commit 歷史疑含真實帳單片段；工作樹測試已換虛構資料，歷史重寫／force push 需使用者**明確核准**，本輪不執行。原已通過 Alembic 0022 readback、V2 1.0 規則版 Staging Release，不重複當作 ONNX 真實 Gmail 驗收。

## 2026-10-19｜版本公告接續驗證
- GitHub main `6f3ddba` 的 CI 四項 [#39128817868](https://github.com/tommylin15/life_assistant/actions/runs/39128817868) PASS；同版 V3 [#39129015414](https://github.com/tommylin15/life_assistant/actions/runs/39129015414) 固定 staging PASS，但 production promotion 與 Hosting 步驟 skipped；不宣稱 0.2.0 已對一般使用者上線。
- P0/P1 續作：新版 0.3.0+3 加入功能 rollout 公告隔離、已讀即時更新、Web 版本檢查提示、Backend-only 維護公告唯讀 API；目前無可發布的 Backend-only 實際修正，回傳空列表。
- 本次需新 SHA Flutter/Backend/Deployment/Postgres CI、staging、正式 V3 promotion、Hosting same-SHA readback、手機與一般帳號 E2E；缺證據維持 PARTIAL／NOT VERIFIED。不自動跳過正式 promotion。

## 2026-10-18｜使用者版本更新中心

- `v0.2.0+2` 為**下一個候選發布版本**，不是目前 production 已驗證版本。前端新增「最新消息」入口、輕量更新紀錄、每帳號每瀏覽器未讀標記；候選環境另顯示診斷用 SHA，正式介面不顯示。
- CI 的候選與 Hosting build 從 `pubspec.yaml` 帶入語意版本及原有 Git SHA；只有通過既有 V3 promotion／正式 Hosting readback，才視為使用者可見的正式版。發布、回滾會連帶更新公告。
- **驗證待辦（NOT VERIFIED）**：Flutter tests／四項 CI、staging 帳號與手機導覽、production same-SHA Hosting、不同帳號與瀏覽器未讀狀態、rollback。未達 gates 不可稱已上線。
- 交付規則詳見 [版本更新公告政策](product_release_notes_policy.md)。

## 2026-10-18｜台灣活動探索接續／唯一活躍缺口（15:54 更新）

| 優先序 | 項目 | 最新狀態／退出條件 |
| --- | --- | --- |
| P0（關閉） | Life importer／交接 Sheet／PG 同版本 | **PASS／DONE（技術資料鏈）**：正式 Job 真實成功 [#39101120210](https://github.com/tommylin15/life_assistant/actions/runs/39101120210)；15:54 Sheet **65 ACKED、0 ERROR／READY**，3 筆新 BeClass 同鍵 CREATED；[只讀 PG 逐鍵版本＋核證狀態比對 #39110194986](https://github.com/tommylin15/life_assistant/actions/runs/39110194986) PASS。嚴禁為重複驗收再跑 importer。 |
| P1 | Life 活動探索前台新版顯示／分類 | **PARTIAL**：`pending_review` 與 verified／unknown、來源與報名兩網址及搜尋功能 source/CI 已具備；但當前並行 Flutter UI commits 的同 SHA Staging／Production Hosting、登入後一般帳號可見新三筆、標籤與雙連結真實 E2E **NOT VERIFIED**。合併當輪 UI 工作一次驗收。 |
| P1 | 人工 15:07 新版來源探索品質 | **PARTIAL**：A7＝7 已實查、B11＝11 distinct 實查／9 usable、快照 PASS、精選池 78→81、四視圖／交接讀回 PASS，唯一 10/18 Log PASS；B 月曆／Yii 新鮮度、原主辦額外證據及本輪跨日逐 ID 變更 **NOT VERIFIED**。不要把來源閱讀備援視作繞 403／429。 |
| P2 | 次日自然排程／發布 | **NOT VERIFIED**：現有 06:00 探索排程保留唯一執行者，Life GAS 約 07:30 Trigger ID 與自然執行待次日真實證據；無新增 cron/Queue/第二寫入者。正常 UI 發布另依完整 V3/Hosting/rollback gate。 |


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