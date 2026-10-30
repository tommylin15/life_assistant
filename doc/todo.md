## 2026-10-30｜Life 官方觀光署來源 TLS：私有代理保護性阻擋｜PARTIAL

- 0% 候選 [#41012831462](https://github.com/tommylin15/life_assistant/actions/runs/41012831462) 確認 Cloud Run 到 `media.taiwan.net.tw` 為 `tls_certificate` 類別；GitHub runner 官方端 TLS [#41012955722](https://github.com/tommylin15/life_assistant/actions/runs/41012955722) PASS。改用系統 CA context 仍保有憑證與 hostname 驗證，[#41013128130](https://github.com/tommylin15/life_assistant/actions/runs/41013128130) Life ZIP 502、MIS PASS，沒有切流。現役 `tw-activity-proxy-00006-dep` 保持安全私有狀態。
- 下一項：有界比較 TLS 鏈／IP 對照，找可信官方來源或受控 CA 修正；不得 `verify=False`。在 Life VM／來源 ZIP 正向驗收前維持 BLOCKED。規格：[共用台灣出口](shared-taiwan-egress-janus-life.md)。

## 2026-10-30｜Life／Janus 共用台灣出口安全發布與來源整合｜PARTIAL

- **安全發布已驗證**：沿用台灣既有 `tw-activity-proxy`，不新建 Cloud Run 或額外付費服務；[#41010462296](https://github.com/tommylin15/life_assistant/actions/runs/41010462296) 正式 100% `tw-activity-proxy-00006-dep`、未授權拒絕、私有 IAM、SSRF 拒絕、官方 MIS `rtcode=0000` PASS；Janus API 服務身分已授予 scoped Invoker。
- **來源負面證據**：Life 觀光署 `Event-json.zip` 經私有代理為 `502 ConnectError`；新 IPv4／TLS 候選 [#41011718029](https://github.com/tommylin15/life_assistant/actions/runs/41011718029) 因官方來源正向失敗而未切流；保留現役安全 revision，不能把 MIS PASS 當作 Life 所有來源 PASS。
- **開發**：`services/tw_activity_proxy/main.py` 停用靜態秘密、限來源主機／GET／HTTPS／TLS、無任意 redirect、封鎖私有 IP，並新增有界 IPv4 與安全錯誤分類；`backend/app/services/tw_request_router.py` 改走 Service Identity ID Token。回歸 [#41012113664](https://github.com/tommylin15/life_assistant/actions/runs/41012113664) PASS。新一次來源連線分類仍依新候選實際讀回。
- **待辦**：查官方來源 TLS/DNS/TCP 正向連線或合格官方替代來源，執行 Life VM 真實活動抓取／既有來源回歸（不允許 `verify=False`），再更新 Live readback 與本 TODO。詳細規格及證據：[共用台灣出口](shared-taiwan-egress-janus-life.md)。Janus API 已獨立完成 Release/Dev promotion；其 Owner 7 檔行情／當日損益是 Janus 獨立驗收，不由 Life 代判成功。

## 2026-10-30｜Hosting #40988859804 Playwright／Ubuntu 26.04 衝突修復（最新）

- **已驗證根因：** [Firebase Hosting #40988859804](https://github.com/tommylin15/life_assistant/actions/runs/40988859804)，`Install production UI acceptance tooling` 與 `Run Project UI production acceptance` FAIL。官方錯誤：`Playwright does not support chromium on ubuntu26.04-x64`；`playwright@1.55.0` 的 Chromium 未安裝成功，後續 Project UI 缺 `chromium_headless_shell-1187`。本輪既有版本／OAuth／圖示／manifest 等靜態 Hosting readback PASS，**不得因此把 UI E2E 說成 PASS**。
- **實際修復：** `.github/workflows/deploy-firebase-hosting.yml` 將 production Hosting `runs-on: ubuntu-latest` 改為**固定 `ubuntu-24.04`**，避免 runner 自動升級至 Playwright 1.55 不支援的 Ubuntu 26.04；保留安裝重試與 Task/Project UI 及失敗 rollback gate，不跳過或降低驗收。 `tests/test_v3_auto_production_hosting_workflow.py` 新增 runner／Chromium／UI 驗收／rollback 不變的 contract test，已提交 `main`。
- **獨立驗收：** 原 Run 的 `Restore previous production Hosting on failed readback` 步驟為 **success**，但生產站最後可用版與 App 真人操作需以最新 release 與 live 讀回另判。新 SHA 的 CI、同 SHA V3 Backend Promotion、Production Firebase Hosting、真正 Chromium Task/Project UI E2E，仍須有各自 run 收據；不可重跑舊 SHA 取代新 release。
- **下一入口：** 最新 `main` 五項 CI PASS → 依原 V3 Release gate 同 SHA 執行受控發布（需要時）→ 由官方 `Deploy Firebase Hosting` 執行新 SHA，要求 `install_playwright=PASS`、Task/Project UI acceptance、Hosting readback、rollback 狀態的實際證據。**LINE V2-02 並未因本項修復而完成上架**，仍需獨立恢復 `enable_line=true` Staging、Colab `LINE_BACKEND_READY=PASS`、OA API readback 和手機驗收。
- **狀態：** 原因 PASS；Source／contract TEST 已提交；完整 CI、同 SHA Release、Hosting Production runtime **待當輪讀回（NOT VERIFIED）**，整體 PARTIAL。

## 2026-10-30｜LINE Staging 503／自動 CI 關閉 LINE｜雙層保護修復（最新）

- **根因（證據 PASS）：** Owner Colab `LINE_OA_AUTH=PASS` 但 `/api/v1/line/config` 為 503，沒有更換 OA 預設八格。原 LINE-enabled [V3 #40857785208](https://github.com/tommylin15/life_assistant/actions/runs/40857785208) 是 `LINE_ENABLED=true`，後續自動 [#40981334221](https://github.com/tommylin15/life_assistant/actions/runs/40981334221) 和 [#40982431521](https://github.com/tommylin15/life_assistant/actions/runs/40982431521) `LINE_ENABLED=false`，覆蓋固定 Staging，故後端 configuration() 503。非 LINE token/圖片/Secret IAM 問題。
- **修復程式：** `scripts/line_staging_guard.py` 只讀固定 Stage；僅 **連續兩次**讀回確切應用層 `503 {"detail":"LINE integration is not configured"}` 才允許一般自動發布，200／網路失敗／未知 503 均 `HOLD`。在 `v3-auto-staging-after-ci.yml` dispatch 前，以及 `v3-release-ghcr.yml` 的 `auto_staging=true` 且 `enable_line=false` 部署前**雙層保護**。一般用戶手動 V3 Release 功能不受此 gate 擅自變更；沒有 GCP IAM/Secret 變更、沒有清除 v1 資料。
- **測試與 WI：** `tests/test_line_staging_guard.py` 覆蓋各種 HTTP/error、競態與 workflow 契約；[WI-05I](line_integration_b_wi.md) 記載完整證據與回復程序。**GitHub Source 已提交**；CI、實際 auto-skip、Staging 再啟用與 OA Menu 仍須依最新 main 實際讀回判定。
- **唯一下一操作：** 最新 main 全 CI PASS 且舊 V3 執行停止 → 人工 V3 `promote=false,publish_staging=true,enable_line=true,auto_staging=false`，保留原 `enable_gmail_onnx` 設定 → Staging `line_candidate_config`、Preview、`staging_live` PASS → Owner Colab 第三格 `LINE_BACKEND_READY=PASS`，確認 LINE Console Webhook 相同環境後再套用第 4 格八格選單；讀回 `richMenuId` 與手機實測。LINE enabled 時未來一般 auto Staging 預期 `HOLD`；新的 App 改動改走明確手動 Staging。
- **狀態：** root cause=PASS；code submitted=PASS；CI/Staging runtime/LINE OA default/readback/mobile **NOT VERIFIED**，LINE-V2-02 **PARTIAL**。勿跳過安全門檻或假稱已上架。

## 2026-10-29｜LINE-V2-02 八格 Rich Menu 正式素材與上架工具（最新，PARTIAL）

- **SOURCE PASS：** 2×4 八格（2500×1686，前七 Postback／右下 Life Omni Web `/today`）正式圖與紅框定位圖完成；Drive `life_assistantGPT/LINE_U16_六格選單` metadata 讀回 **PASS**，正式圖 [ID 1mB_15NAsxDyj3ZGikP4x7FT30Mf4gx2O](https://drive.google.com/file/d/1mB_15NAsxDyj3ZGikP4x7FT30Mf4gx2O/view)／289918 bytes／SHA256 `33b2460021d41c71ba56cbd90830361205f01c46d30623f60d4e413e4c794f86`；定位圖 [ID 1yxrBJBiroarM0yXJE01Eg8Qr2cjAscdU](https://drive.google.com/file/d/1yxrBJBiroarM0yXJE01Eg8Qr2cjAscdU/view) 不可上傳 LINE。
- **程式與 WI：** `scripts/line_rich_menu_v2.py`、`scripts/build_line_rich_menu_v2.py`、`tests/test_line_rich_menu_v2.py`；Colab Notebook `Life_Omni_LINE_V2_02_Eight_Grid_Apply.ipynb` 以私人 Drive File ID 讀圖、SHA 與規格檢查、Token getpass、LINE API 建圖／全好友預設覆蓋／讀回。指引 [V2-02 Asset WI](../assets/line/README_V2.md) 與 [WI-05H](line_integration_b_wi.md)；Owner 已允許直接覆蓋舊預設選單，不需要額外備份舊選單。
- **安全門檻與差異：** V2-01 後端已提供活動 Carousel，但前六格 Postback 仍是 LIFF fallback（待 V2-03），不得宣稱已完成 LINE 內對話卡片。已核對成功的 V3 [#40852323202](https://github.com/tommylin15/life_assistant/actions/runs/40852323202) `LINE_ENABLED=false`，**不能當作 LINE 可回覆八格 Postback 的部署驗收**。未取得 Token／真實 LINE default `richMenuId` 讀回與手機操作收據前，**OA 上架／Staging/Production／iOS/Android = NOT VERIFIED**；不假稱已上線。
- **另補既有 V2-01 CI 缺口：** 原 backend `test_tampered_and_expired_tokens_rejected` 因 Base64 非 canonical 尾位可改寫而 FAIL；修正 `backend/app/services/line_v2.py` 以 canonical signature 檢查，不放寬測試，最新 CI 另讀回。
- **下一工程行動：** 最新 main 全 CI PASS → LINE-enabled Staging `enable_line=true` 同 SHA → Owner Colab 執行，回報 `LINE_V2_DEFAULT_MENU_API=PASS`／`richMenuId` 並完成手機八格、活動 Flex 收藏、Life Web 登入回讀。V2-02 全部實測 PASS 再進 V2-03 快速記錄／今日總覽／搜尋／待辦／購物／日曆對話卡片。v1 六格及歷史資料保留；v1 U17 仍待故障驗收。**整體 PARTIAL。**

## 2026-10-29｜LINE-V2-01 對話核心＋活動 Carousel：Source 已提交；Staging／真人驗收待辦（最新）

- **GitHub 實作：** [LINE v2 工程規格](line_v2_conversation_refactor_spec.md#0-v2-01-工程收據2026-10-29source-已提交發布獨立驗收)、`backend/app/services/line_v2.py`、既有 `backend/app/api/line.py`；LINE HMAC＋Binding＋FeatureRollout＋事件去重保留，新增 Postback 白名單、7 日簽名 user/namespace 動作 token、活動 Flex（6 張／最新 Life created_at 排序）、真實分類 Tag、已收藏／下一批及明確 active 收藏。與原 Explore Domain Service 共用資料，不新增 DB/migration。
- **不換選單即可測：** 在原有 LINE OA 直接送出「活動」「最新活動」「活動分類」「已收藏活動」，不會當成草稿。後續八格 Rich Menu 的活動格對應 `v=2&cmd=events.latest`；本輪不更換 v1 六格、不直接改 Life App 登入。
- **測試：** `backend/tests/test_line_v2.py` 新增簽名、跨帳號、逾期、Flex、Tag、分類、收藏及分組測試；`backend/tests/test_line_channel.py` 新增真 Webhook Postback 去重與文字指令不誤存。**本輪最新 main SHA 的 CI、LINE-enabled staging、實機 Flex/Tag/收藏均須獨立驗收**，不能將前輪 CI PASS 延伸至最新 SHA。
- **唯一下一操作：** 最新 main CI PASS → 手動 V3 `promote=false / publish_staging=true / enable_line=true` 的同 SHA Staging（一般 Auto Staging 預設 LINE 關閉，不可作 LINE 實機證據）→ Owner 依 [WI-05G](line_integration_b_wi.md#wi-05gline-v2-01-活動-flex-真人驗收2026-10-29) 完成 LINE Flex 橫移、Tag 分類、收藏／取消且 Life 讀回、跨帳號及回覆異常。全部 PASS 才能 V2-01 DONE，然後唯一下一工程入口 V2-02 八格 Rich Menu 圖面與上架。
- **驗收判定：** Source=PASS（GitHub 寫入）；完整 CI=依新 SHA；staging/runtime=NOT VERIFIED；Owner v2 integration=NOT VERIFIED；總體=PARTIAL。v1 六格真人 PASS、U17 NOT VERIFIED 保留，Production 不切流。

## 2026-10-29｜LINE v2 八格選單＋對話式 Flex Carousel｜DESIGN APPROVED，待工程實作（最新）

- **正式規格：** [LINE v2 重構規格（GitHub）](line_v2_conversation_refactor_spec.md) 與 [Google Drive 正式文件](https://docs.google.com/document/d/1bwKQZC8Bh9cZS5vbIlrv8toI7qY5mjlieVPG22mvIa8/edit) 已建立並讀回；Drive 位於授權根資料夾 `life_assistantGPT`，這是 **v2 產品方向與執行卡的文件成果**，非 v2 已部署。保留 v1 [LINE B](line_integration_b.md) 及 [WI](line_integration_b_wi.md) 的實際測試／歷史狀態。
- **八格**（2500×1686，2×4）：快速記錄、今日總覽、查我的資料、待辦、購物、日曆、活動、Life Omni。前七格是 LINE Postback／Flex／Quick Reply 對話操作；最後一格直接到完整 Life Web。新圖需要製作、八格 bounds 校驗及手機驗收；舊六格實機 PASS 不可沿用到 v2。
- **活動優先：** `entry=explore&quick=latest` 的 Life `created_at` 倒序分組去重，Flex Carousel 橫移，顯示日期／城市／真實類別與缺值、可收藏；「依 Tag 看」在活動內做第二層選單，首版用現有 `category` 真值，沒有證據支持任意多值 Tag。下一批分頁，進階篩選引導 Life；不新增爬蟲。
- **唯一下一工程入口：** `LINE-V2-01｜對話命令核心＋活動 Flex Carousel／Tag／收藏`；按正式規格差異檢查→程式→離線／PostgreSQL 測試→main CI→Staging 真 LINE 驗收，**本輪不啟動 v2 code、deployment 或 OA 選單替換**。後續依序 V2-02 八格圖面／Rich Menu、V2-03 待辦購物／摘要／分類、V2-04 Life Web 手機首頁、V2-05 U17／Production 整合驗收。
- **狀態：** 設計／文件交付可各自 PASS（依 GitHub／Drive 讀回）；v2 implementation/tests/CI/deploy/runtime/integration **NOT VERIFIED**；v1 U17 未驗證且完整 LINE **PARTIAL**。不將文件完成宣稱功能 DONE。

## 2026-10-29｜LINE U16 六格操作 Owner 驗收 PASS（最新）；完整 LINE 仍 PARTIAL

- **已證實：** Owner 2026-10-29 明確回報「六格操作驗收完成」，官方帳號六格 Rich Menu 真人操作子項 **PASS／Owner reported**；無逐項截圖、API `richMenuId`／default 讀回、iOS／Android 雙平台分項及登入返回紀錄。因此按完整 U16 原案，未核證平台子項保持 **NOT VERIFIED**，不得將六格通過包裝成完整矩陣或 Production DONE。正式圖片與位置已在 [LINE WI-05E/05F](line_integration_b_wi.md)。
- **前次 CI FAIL 根因已處理：** [CI #40841479917](https://github.com/tommylin15/life_assistant/actions/runs/40841479917) 的 backend 測試失敗，是 `.github/workflows/line-u16-apply-once.yml` push 觸發不符舊 CI 契約；早前 Actions 套用亦因缺少 `secretmanager.versions.access` [#40838851219](https://github.com/tommylin15/life_assistant/actions/runs/40838851219) FAIL。改採 Owner Colab 完成後，已**移除該多餘 workflow**，不擴 IAM、不接觸生產 Secret；修正後同 SHA CI 需依當次結果判定。
- **唯一下一入口：** U17 Reply API 故障、網路中斷、UNKNOWN 回執且不可重複建立；之後補 U01–U07 例外路徑及 U16 未提供證據的 iOS/Android／登入返回細項。核心成功路徑及 U08–U15 PASS 回報保持原樣。**整體 PARTIAL／Production NOT VERIFIED**。

## 2026-10-29｜LINE U16 六格選單素材已產出，OA 尚未套用（PARTIAL）

- **SOURCE PASS：** `assets/line/rich_menu_v1.svg`、`scripts/build_line_rich_menu.py`、`tests/test_line_rich_menu_art.py`、`assets/line/README.md` 已建立；維持現有 `scripts/line_rich_menu.py` 的六個 deep-link action 與 2500×1686 全覆蓋 bounds。生成的本地 PNG 為 2500×1686、198056 bytes（未加入 GitHub 二進位檔；可由 renderer 重產）。圖片僅在本地生成與驗證，產圖依賴 CairoSVG 僅為設計工具，不新增 Cloud Run 依賴。
- **CI / OA / 實機：** 新 SHA CI 需獨立核對；OA 預設 richMenuId、真實 LIFF ID、`--apply`、iOS／Android 六格驗收均 **NOT VERIFIED**。本次沒有改 LINE Console、Webhook、Secret、DB、production traffic 或 OA 預設選單。
- **下一工程入口：** 先依 [U16 安全套用 WI](../assets/line/README.md) 唯讀核對真實 OA channel、LIFF ID、舊選單及恢復方案，再有界套用六格選單、行動裝置逐格驗收；其後是 U17 Reply／UNKNOWN 異常恢復及 U01–U07 未覆蓋邊界。不能以圖片完成推定 U16 PASS 或 LINE 整體 DONE。
- **人工回報保留：** U08–U15 Staging PASS（Owner 回報）；原六項核心成功路徑 PASS。**整體 PARTIAL，Production NOT VERIFIED**。後續 production promotion 需最新 main 同 SHA 成功 LINE-enabled Staging proof。

## 2026-10-29｜LINE 第三輪 Staging 驗收 U12–U15 PASS；U16 六格選單尚未做／U17 未驗證（最新）

- **Owner 確認：** U12 跨帳號隔離、U13 群組防洩漏、U14 解除綁定／封鎖、U15 功能權限共四項 Staging 真人 **PASS**。僅為 Owner 回報，未附逐案 trace／截圖；先前 U08–U11 四項 PASS 及六項核心成功路徑 PASS 保留。
- **U16 非「已做待測」，而是「LINE OA 聊天室六格 Rich Menu 尚未製作／套用」：** `scripts/line_rich_menu.py` 可產生六格 actions JSON 並在明確加 `--image … --apply` 後套用，但主倉庫沒有六格圖檔；LIFF 內部八個 tab 不是 OA Rich Menu。**驗收 NOT VERIFIED，實作／套用尚未完成。** `--apply` 影響 OA 所有好友，應先做圖片、預覽六個 LIFF 頁面與還原方案、核對唯一 OA 的 Staging/Production 對應，不能未核對就改預設選單。
- **U17：NOT VERIFIED**，需驗證 Reply 失敗後草稿保留及 UNKNOWN receipt 不重複寫入；已有單元測試不代替受控真實故障驗收。U01–U07 具體例外邊界仍需補驗。
- **唯一下一工程入口：** U16 先製作六格圖像／JSON／預覽／safe-apply WI（不直接套用官方帳號），再做 U17 有界故障測試與未覆蓋例外；完成後重新跑當時最新 SHA 的 LINE-enabled Staging → 確保同 SHA proof → 才評估 Production promotion 及 OA Webhook／LIFF／Rich Menu 切換。**整體 PARTIAL；Production NOT VERIFIED**。詳細：[LINE WI-05C](line_integration_b_wi.md#wi-05c2026-10-29-第三輪-owner-回報與六格選單現況更正)。

## 2026-10-29｜LINE B Staging 六項真人功能 PASS；正式發布仍 PARTIAL

- 已核對同一 `main` SHA `31326e856ffddd8504ae39260cf7c5facb7a2826` 的 [V3 Staging #40827872508](https://github.com/tommylin15/life_assistant/actions/runs/40827872508) SUCCESS，候選 LINE 設定、固定 staging、DB revision 0024 readback job 與 staging bundle proof artifact SUCCESS；**該 run 未 promote，不能標 Production PASS**。
- Owner 在 2026-10-29 回報 LINE Staging：身分綁定、快速記錄、解析、正式新增、Life 查詢、重複新增防護，六項 **PASS**。僅作成功路徑回報，不自動等同 [WI U01–U17](line_integration_b_wi.md) 每個例外案例 PASS。
- **唯一下一入口：** 依 [WI-05A](line_integration_b_wi.md#wi-05a2026-10-29-staging-實機回報依-owner-明確確認) 完成 U01–U17 尚未覆蓋的真人案例（重點：U08–U11 實際資料讀回、U12–U15 權限／撤銷、U16–U17 手機／失敗恢復）；完成且證據充分後，再依 V3 gate 執行正式 promotion、Production Hosting 與 LINE Console webhook／LIFF／選單切換驗收。Production **NOT VERIFIED**，不得單憑 staging 成功宣稱 DONE。

## 2026-10-29｜LINE 第二輪 Staging Owner 驗收 U08–U11 PASS；下一入口 U12–U17

- Owner 明確回報 `U08–U11 PASS`：U08 筆記／待辦／購物修改與 Life 讀回、U09 Google 日曆真實查詢／新增讀回、U10 日曆撤銷授權後正確報錯、U11 活動搜尋／收藏／分頁。已於 [LINE WI-05／05B](line_integration_b_wi.md) 逐項登錄；這是 Owner 實機報告，沒有新增逐案截圖、trace 或 Production 收據。
- 原有六項核心成功路徑 PASS 保留；原本 [Staging #40827872508](https://github.com/tommylin15/life_assistant/actions/runs/40827872508) 對應 SHA `31326e8`，不能當作更新文件後的最新 main SHA production proof。前輪文件 commit `c44bb6c` 的 [CI #40832037200](https://github.com/tommylin15/life_assistant/actions/runs/40832037200) 為 SUCCESS；此行不推定本次新 commit 的 CI 已通過。
- **唯一下一入口：** U12–U15（另一帳號草稿／私人資訊隔離、群組忽略、解除綁定或封鎖後存取失效、hidden／目的功能關閉拒絕）；U16–U17（六格選單 iOS／Android、Reply／網路故障後草稿與回執），並補 U01–U07 尚未涵蓋的邊界。完成前 Production `NOT VERIFIED`，所有 LINE 正式 OA webhook、LIFF 與 rich menu 不切換；正式 promotion 需重新以當時最新 main SHA 跑 Staging 取得同 SHA bundle proof 並完成發布 gate。

## 2026-10-28｜原版 LINE 方案 B 已恢復為優先基線

依 Owner 最新指示，以本對話工作副本的 `api/line.py` 與 `web/line/` 為準。原版 manifest、patch 與 153/15 測試收據已保存於 doc/evidence、doc/archive。保留舊 0023 資料表，以 0024 向前遷移；舊 bridge router 不註冊。現行規格：[LINE B](line_integration_b.md)，設定與真人驗收：[WI](line_integration_b_wi.md)。下方舊「原版未找到／停止線」是歷史查核，已由本次找回證據及 Owner 指示取代。CI／部署／真人整合依當次證據分別判定。

# Life — Active engineering TODO

## 2026-10-28｜LINE 原版復原優先（BLOCKED／NOT VERIFIED）

- **使用者最新決策：** 前次「LINE整合方案評估」已開發與自述測試 153 項／LINE 15 項的版本，才是希望恢復的基準；後次 GitHub LINE 重寫不列入正式成果，不以此繼續開發。
- **復原查核：** [line_recovery_audit_20261028.md](line_recovery_audit_20261028.md)。前次原始碼、git SHA 或可恢復檔案 **NOT VERIFIED**；前次開發前 main `56275487` 和其他已知分支沒有 LINE 版本。不得捏造「原版已找回」。
- **目前新版本：** 保持 source 可供比對、功能開關預設關閉；同 SHA [CI #40616784019](https://github.com/tommylin15/life_assistant/actions/runs/40616784019) 為 **FAIL（Backend 1 項 migration 版號契約測試）**，不是 CI NOT VERIFIED；Staging/LINE 真人／Runtime 均 NOT VERIFIED。
- **停止線：** 原版的可讀原始碼 + 確切檔案/SHA、15 項測試的可重跑指令與結果、逐檔差異均有證據後，才能以正常 commit 做有界回退與替換；禁止整棵 main reset/force push，不碰同期間非 LINE 的探索匯入程式。未達上述條件時暫停 LINE 功能開發及發布。

## 2026-10-28｜LINE 整合方案 B：Source 已提交，人工驗收與正式功能仍 PARTIAL

- **唯一規格與可執行 WI：** [LINE 整合方案 B](line_integration_b.md)。本次新增 `backend/app/api/line_bridge.py`、`backend/app/models/line_bridge.py`、非破壞性 Alembic `20261028_0023`、`web/line.html`、簽章／重送／隔離測試；所有 LINE secrets 均須透過 Secret Manager 注入，`LINE_BRIDGE_ENABLED` 預設關閉。
- **現有 source 能力：** Webhook HMAC、LINE ID Token 驗證、Life Google 登入雙身分綁定／撤銷、私聊純文字草稿去重、LIFF 的最近 20 筆草稿／五筆待辦與五個購物清單名稱。不得把草稿視為已正式新增 Task／Calendar。
- **產品差距：** LIFF 草稿尚需複製到既有 Life 快速新增並由本人確認；查資料、筆記、活動、日曆皆尚未完整 LINE 原生查詢／深連結。原先「完整方案 B」不能標記 DONE。
- **驗收狀態：** implementation/source PASS；單元測試執行／四項同 SHA CI／Staging PG migration／LIFF 真正登入／LINE OA webhook／Rich Menu／Production runtime 全部 **NOT VERIFIED**，直到當輪 Actions、runtime 與使用者本人 WI 實際驗收。既有成功的 Gmail 與 Life CI 不得沿用。
- **下一工程入口：** LINE 草稿→Life Inbox 的安全預填／逐筆人工確認；接續 LIFF 個人筆記、活動與 Calendar 查詢。由使用者依 [WI-LINE-00～05](line_integration_b.md) 操作外部整合驗收。正式 OA 選單與 Production 改動保留到驗收合格後。

Updated 2026-10-26. **One active backlog only.** Prior 01–07 execution plan has been completed at source/release-gate level where cited, but unverified integration outcomes remain open. [Current evidence](CURRENT_STATE.md) · [Risk register](RISK_REGISTER.md).

## 2026-10-26｜Gmail V2 P0/P1：Production 已於 2026-10-23 完成發布；Staging 真人快掃已驗收

- **P1 正式上線已於 2026-10-23 發布完成（DONE，同 main SHA `2e2bbb50d7166fe49b9130594af3fe952dbf6334`）：**
  - 四項 CI [#39887105661](https://github.com/tommylin15/life_assistant/actions/runs/39887105661) PASS。
  - V3 Production 切流 [#39888978522](https://github.com/tommylin15/life_assistant/actions/runs/39888978522)（輸入 `promote=true`、`enable_gmail_onnx=true`、`publish_staging=true`）PASS：100% 正式切流、Post-promotion live health / PG access、rollback drill rehearsal、Revision 清理維持最新 10 個、定時 Job digest 對齊均通過。
  - Firebase Hosting [#39889756103](https://github.com/tommylin15/life_assistant/actions/runs/39889756103) PASS：同 SHA `2e2bbb5`、GHCR ONNX 映像 digest 對齊，正式站 live readback 與 Task/Project UI 驗收 PASS。正式站 `https://gen-lang-client-0593591102.web.app/release.txt` 讀回 `2e2bbb50d7166fe49b9130594af3fe952dbf6334`，未授權 API 401 正常。
- **P0 真實 Gmail Staging 驗收（使用者結案，2026-10-26）：**
  - 使用者於 2026-10-25 21:08 手機截圖確認：Owner 重新授權 Google 後，「立即快掃」正常執行，近三天 19 封「重新判讀」`失敗 0 封、未檢查 0 封`，掃描狀態更新為 2026/10/25 21:08。此前失敗屬 Google OAuth 憑證過期（409），重新授權後排除。
  - 使用者於 2026-10-26 明確確認目前操作與結果符合預期，P0 正式結案。
- **仍屬 NOT VERIFIED（不因發布與結案而推定 PASS）：**
  - 正式 Production 環境真實 Gmail 真人操作（目前真人回報僅限於 Staging 站；正式站僅通過自動化 401 / redirect / digest 驗收）。
  - 實際帳單命中與時間/金額抽取、促銷排除、7 天 40 封補檢、Gmail → Inbox 本地轉存寫入 PG、一般帳號跨帳號隔離、完整 FastAPI ONNX p95/RSS。上述項目需在日常營運中持續觀測。

## 2026-10-21｜快速新增 P0–P1：Production DONE（ONNX P2 取消）

- **P0／P1 已實作並發布：** 規則快速解析多件明確事項、擴充繁體中文購物分隔詞；Gemini 逐項拆解並補足可驗證遺漏；每個候選獨立日期依據，未提供的結束時間／日期不臆測；Flutter 顯示多項且分別勾選後才提交。完整規格見 [快速新增](life_inbox_quick_capture_spec.md)。
- **P2 ONNX 試點：CANCELLED**（使用者決策）。本功能不載入 Gmail ONNX 模型，不新增 Cloud Run 推論服務。
- **工程子項 DONE／PASS（2026-10-21）：** 同 SHA `5f41a86b0a210971d73467f409fb654746f13630`，Backend／Flutter／PostgreSQL／Deploy 四 CI [#39515249836](https://github.com/tommylin15/life_assistant/actions/runs/39515249836) PASS；V3 候選、固定 Staging、API/DB/OAuth 及 Flutter Preview [#39515593787](https://github.com/tommylin15/life_assistant/actions/runs/39515593787) PASS。該輪僅 Staging；後續 v0.4.0+4 Production 已於本節完成發佈。
- **Staging 人工驗收：PASS（使用者已於 2026-10-21 確認）。Production 正式發布：PASS／DONE（v0.4.0+4，SHA `cadf61168c87731b00a240def5da579e7f931a6e`）：** [CI #39583599134](https://github.com/tommylin15/life_assistant/actions/runs/39583599134) 四項 PASS、[V3 #39584025660](https://github.com/tommylin15/life_assistant/actions/runs/39584025660) 100% 切流及 rollback PASS、[Firebase Hosting #39585004848](https://github.com/tommylin15/life_assistant/actions/runs/39585004848) 同 SHA 正式讀回及 UI 自動驗收 PASS。版本號與最新消息自動 gate 已驗證。生產實際不同帳號 Gemini 自由輸入辨識率仍需獨立測量（NOT VERIFIED），但不重開已完成的發布工項。

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
| P2 | 次日自然排程／發布 | **SCHEDULED**：已設定 Linux 系統級排程 `tw-activity-discovery.timer`（台灣時間每日 04:00，即 UTC 20:00，調用 agy 搭載 Gemini 3.8 Flash Medium）作為唯一正式啟動者，串行完成探索與 Life 入庫，獨立於任何對話視窗；2026-10-26 使用者確認舊 06:00 外部排程與 GAS 07:30 觸發器已正式停用。次日自然執行待真實日誌證據。 |


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
