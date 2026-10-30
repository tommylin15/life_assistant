## WI-05J｜2026-10-30 智慧即時記錄＋Life 直接導覽一輪驗收（ACTIVE）

1. 核對 GitHub main 同 SHA 五項 CI PASS，backend migration head 為 0025；確認無其他 V3 部署競逐。
2. 同 SHA 手動 V3 Staging：`promote=false,publish_staging=true,enable_line=true,auto_staging=false`，保留既有 Gmail ONNX；核對 `line_candidate_config=PASS`、`preview=PASS`、`staging_live=PASS` 與 Stage /api/v1/line/config 200。
3. 手機 LINE 測試：八格原選單不重建；「牛奶」→ 四類分類 → 購物 → 選真實本人購物清單 → 確認 → Life PG 購物清單讀回；另測待辦標題及截止、筆記標題/內容、行程開始/結束時間與 Google 授權；所有新增須有明確確認。點「完整」應直達同環境 Flutter Life，不進 LIFF。
4. 測試跨帳號、取消、不完整日曆、過期舊卡片、Webhook 重送、同操作重點、Reply 異常與 UNKNOWN 收據。UNKNOWN 不換 action ID 自動重建。活動「最近三天／七大類／已收錄／已收藏」按收錄時間排序仍須回歸。
5. Staging 真實讀寫與手機皆符合才進入同 SHA Production promotion；確認 Production Domain、Google OAuth、LINE Console Webhook / LIFF id 與 OA 八格，並再次實測正式資料。正式版成功前不得將本 WI 標 DONE。
6. 每項登錄 PASS/FAIL/NOT VERIFIED，遮蔽 token/私人內容與綁定碼。出現 FAIL 即停止 Production 切流，保留舊線上版本。

# LINE 方案 B｜設定與人工驗收 WI

本版使用 `/line/index.html`，API 為 `app.api.line`。舊 `LINE_BRIDGE_*` 設定不適用。先完成 GitHub CI；真實 LINE 驗收由 Owner 執行，各案例初始皆 NOT VERIFIED。

## WI-01：LINE Console
1. 在既有官方帳號啟用 Messaging API。建立同一 Provider 下的 LINE Login channel，新增 LIFF，scope 勾選 openid、profile。
2. LIFF endpoint 設為測試站 `https://life-assistant-v3-stage-tl15.web.app/line/index.html`。
3. Webhook 設為同環境 `/api/v1/line/webhook`，開啟 webhook 與 redelivery。避免預設自動回覆與程式重複回覆。
4. Channel secret 與 Messaging API access token 置於**現有 Secret Manager `life-assistant-bundle` JSON 物件**，分別為 `LIFE_LINE_CHANNEL_SECRET`、`LIFE_LINE_ACCESS_TOKEN`。本次已建立並讀回第 9 版；日後若輪替，以實際有效版本為準。保留原有所有 bundle keys，不另外建立兩個 LINE Secret。不得把憑證內容貼在聊天、原始碼或一般 variables。沿用既有 Cloud Run runtime identity 的 bundle 讀取權限，先核對是否足夠，不擴大 IAM。

## WI-02：GitHub Variables 與候選部署
在既有 dev-test environment 設下列 variables；STAGE 與 PROD 各一組：

| Variable 後綴（前綴 LINE_STAGE_ 或 LINE_PROD_） | 值 |
|---|---|
| NAMESPACE | stage 或 production（各環境不同） |
| ORIGIN | 該環境 Hosting HTTPS origin，無尾斜線 |
| LIFF_ID | Console 顯示的 LIFF ID |
| LOGIN_CHANNEL_ID | LINE Login channel 數字 ID |
（無需 BUNDLE_REF）部署流程自動解析 Secret Manager 的版本，不需在 GitHub 設任何版本號。

執行 V3 Release workflow：先選 promote=false、publish_staging=true、enable_line=true；Gmail ONNX 選項維持目前正式需求。流程自動選取**最新 ENABLED 數字版本**，且在同一輪固定注入 `LIFE_ASSISTANT_BUNDLE`，候選 revision 讀回版本並透過 `/api/v1/line/config` 驗證啟用值。成功的 Staging Run 儲存 30 天非機密的 SHA／版本證明（Actions Artifact）；正式 `promote=true` 只能取用同 SHA、已成功 Staging Run 的版本，無法取得證明即停止。正式發布前仍需 Owner 完成 U01–U17。確認 CI、真實 DB migration 0024、candidate、Hosting staging gates PASS。GitHub Variables 不保存 Secret 版本或內容。

後台將 line、life_inbox 與需要的目的功能對 Owner 開放。預設 line 為 beta/owner。一般使用者需另行開放；不可只開 LINE 而忽略目的功能權限。

每次部署要啟用 LINE 都必須選 enable_line=true；預設 false。自動 staging 會建立 LINE 關閉的候選，測試時需手動部署啟用候選。

正式發布另用 promote=true、publish_staging=true、enable_line=true，採 PROD 非機密 variables，bundle 自動沿用成功 Staging Run 的版本（不得自動抓更新的 Key）。只有一個 OA 時，驗收後須同步將 webhook、LIFF endpoint、選單改成正式環境；同一 webhook 不同時服務兩個環境。Production candidate 同時供 staging 發布 gate 使用時，staging 的 LINE 頁可能因 PROD origin 不符而拒絕，不能把它當成獨立啟用的 stage LINE。

**診斷權限**：自動解析時，GitHub Actions 的 `GCP_DEPLOY_SERVICE_ACCOUNT` 需要對 `life-assistant-bundle` 具有 `secretmanager.versions.list` 中繼資料權限。原有 Cloud Run Runtime 的 Secret Accessor 權限並不等於 GitHub 部署者可查版本。若 CI 顯示 `bundle_resolution=FAIL operation=versions_list category=PERMISSION_DENIED`，請先確認部署者身分，再於**單一 Secret** 層級授予必要版本中繼資料讀取權限（例如 `roles/secretmanager.viewer`），不得授予專案級廣泛權限，也不得因排錯而在 CI 輸出 Secret 值。此權限變更需由有權管理 IAM 者核准並執行；未確認前保持 fail-closed。

**共用 bundle 輪替**：在 Secret Manager 將新增版本設為 ENABLED 即可，不必修改 GitHub Variable；執行新 Staging V3 Release 讓新版本被解析並鎖定。正式發版採同 SHA 的 Staging Artifact 版本，若最新版本已變更不會偷換。既有一般 `Deploy Cloud Run` Workflow 保留正式服務目前使用的數字版，不會藉部署意外切換到新 Key。若正式服務仍是歷史 `:latest`，第一次轉換會解析為當下最新 ENABLED 版；此轉換需人工核對服務。需要更新的 Key 仍需透過 Staging 驗收後發布才能在正式環境生效。原 `LINE_STAGE_BUNDLE_REF`、`LINE_PROD_BUNDLE_REF` 可刪除，其他四個 STAGE／PROD 設定保留。此版本證明只有 30 天保存期，過期需重新發布 Staging。

**GHCR 映像 digest 驗證**：GitHub 發布使用固定 GHCR index digest（`IMAGE_REF`）；Cloud Run 公開映像快取有可能把 Revision 的 `spec.image`／`status.imageDigest` 表示為 index 內的 `linux/amd64` child digest。V3 workflow 必須從該固定 GHCR digest 取得上游 manifest，驗證 Cloud Run 的 digest 僅能是 index 本身或其中唯一合法 `linux/amd64` 子映像，且 Revision `Ready=True`。無法核對則 FAIL，不得只移除 digest gate。若部署發生 `deployed container image is not the pinned GHCR index or linux/amd64 child`，請比對該次 GHCR manifest 與 Candidate metadata，不要自行將任意 digest 加入白名單。

## WI-03：綁定
1. 用外部 Chrome/Safari 開 `/line/link.html`，登入原有 Google Life 帳號；登入後重新開此頁。
2. 核對顯示 email，產生綁定碼，將完整「綁定 …」文字傳到自己的官方帳號私聊。
3. 回到 Life 點檢查，核對 LINE 回覆的尾碼，再點確認。
4. 回 LINE 開 LIFF，應顯示自己的名稱；綁定碼十分鐘到期，不能重用。

## WI-04：六格選單
圖像為 2500×1686 PNG/JPEG，最多 1 MB。上下各三格：快速記錄／今日總覽／查我的資料；待辦・購物／日曆・活動／我的 Life。

**2026-10-29 U16 Source 進度：** 六格 SVG 圖面已加入 `assets/line/rich_menu_v1.svg`，使用 `scripts/build_line_rich_menu.py` 可重產 2500×1686 PNG（本輪本地實測約 198 KB，符合 1 MB 規範），新增 `tests/test_line_rich_menu_art.py` 驗證 SVG、六格點擊 bounds 及圖片規格。完整步驟見 [六格素材與套用安全 WI](../assets/line/README.md)。**目前只完成圖片與程式準備，未使用任何真實 LINE channel token 執行 `--apply`，未設成 OA 預設選單，iOS/Android 實機 NOT VERIFIED。** OA Rich Menu 不等於 LIFF 內部八個分頁。套用會影響所有好友；必須先核對 OA 正在服務的 Staging/Production、真實 LIFF ID、原有 richMenuId 與恢復方案。

先執行 `python scripts/line_rich_menu.py --liff-id <ID>` 檢查 JSON。要套用時，在安全終端以環境變數提供 LIFE_LINE_ACCESS_TOKEN，再加 `--image <圖片> --apply`。工具會建立、上傳並套用預設選單；記下回傳 menu ID，舊選單不自動刪除。既有 per-user menu 可能優先，需另行核對。

## WI-05：人工驗收表

| ID | 操作 | 預期結果 | 結果／證據 |
|---|---|---|---|
| U01 | 未綁定帳號傳文字 | 只引導綁定，不建立私人資料 | NOT VERIFIED |
| U02 | 完成雙端綁定、重用同碼 | 首次成功，重用拒絕 | NOT VERIFIED |
| U03 | 傳「買牛奶、雞蛋」 | 保留草稿，確認清單後才新增 | NOT VERIFIED |
| U04 | 傳「明天下午三點去看牙醫」，隔天開啟 | 日期依傳送日；結束時間需補齊 | NOT VERIFIED |
| U05 | 同草稿重複確認、重新開頁 | 回執或已套用，不重複新增 | NOT VERIFIED |
| U06 | 傳網址 | 可存筆記，不自動擷取網頁 | NOT VERIFIED |
| U07 | 查 筆記 水電／查 待辦 繳費／購物 | 只回本人結果；可開原文 | NOT VERIFIED |
| U08 | 編輯筆記、完成待辦、勾選購物 | 完整 Life 讀回一致 | PASS（Owner 2026-10-29 Staging 實機回報；未附逐案截圖） |
| U09 | 查 Google 行程並新增行程 | 真實 Google 日曆可讀回 | PASS（Owner 2026-10-29 Staging 實機回報；未附逐案截圖） |
| U10 | Google 授權撤銷後查日曆 | 顯示需授權或錯誤，不假報空清單 | PASS（Owner 2026-10-29 Staging 實機回報；未附逐案截圖） |
| U11 | 搜尋活動、收藏／取消、分頁 | 與 Life 一致，保留待核／費用未知標示 | PASS（Owner 2026-10-29 Staging 實機回報；未附逐案截圖） |
| U12 | 另一帳號查草稿 ID／個人資料 | 404／拒絕，不洩漏他人內容 | PASS（Owner 2026-10-29 Staging 回報；無附逐案截圖） |
| U13 | 群組傳訊息 | 不保存、不回覆私人資訊 | PASS（Owner 2026-10-29 Staging 回報；無附逐案截圖） |
| U14 | 解除綁定／封鎖後，用舊頁查資料 | 舊登入失效；Life 原資料保留 | PASS（Owner 2026-10-29 Staging 回報；無附逐案截圖） |
| U15 | LINE 功能 hidden，或目的功能關閉 | API 拒絕，不僅隱藏按鈕 | PASS（Owner 2026-10-29 Staging 回報；無附逐案截圖） |
| U16 | 官方帳號六格 Rich Menu（完成製圖／套用）及 iOS/Android 開啟與登入返回 | 應先有 OA 六格選單、六個 LIFF deep links；頁面可操作、無溢出 | NOT VERIFIED（**六格操作=PASS，Owner 2026-10-29 確認驗收完成**；iOS／Android 各自覆蓋與登入返回未逐項回報，完整 U16 尚未獨立核證） |
| U17 | Reply 失敗／連線中斷後查看草稿與回執 | 草稿保留，結果不明不重複建立 | NOT VERIFIED |

每項記錄：環境、Git SHA、台北時間、案例 ID、PASS/FAIL、實際結果與截圖（遮蔽 token/碼/個資）。遇 UNKNOWN 先查看回執和 Life／Google 原資料，不換 action ID 盲目重建。

## WI-05A：2026-10-29 Staging 實機回報（依 Owner 明確確認）

- **版本／環境：** `main` SHA `31326e856ffddd8504ae39260cf7c5facb7a2826`；[V3 Staging Run #40827872508](https://github.com/tommylin15/life_assistant/actions/runs/40827872508) conclusion=success，`promote=false`，Production 切流未執行。
- **機器證據：** Candidate LINE config、migration job、DB schema readback job、固定 Staging Preview／發布與 LINE staging bundle proof artifact 均為 Actions 成功；artifact 名稱 `line-stage-31326e856ffddd8504ae39260cf7c5facb7a2826`，有效期限依 Actions 為 2026-11-28 06:23 UTC。這不是 Production runtime 或 LINE Console 的驗證。
- **真人功能回報（6/6 PASS；非 U01–U17 全案）：** 身分綁定、LINE 快速記錄、內容解析、經確認正式新增 Life 資料、Life 個人查詢、重複新增防護。上述結果依 Owner 在 2026-10-29 的 Staging 實機回報登錄；未附逐項時間戳及遮蔽截圖，不推定所有例外路徑完成。
- **驗收映射：** 以上功能橫跨 U02／U03／U05／U07 的*一般成功路徑*，但不等於 U02 的「重用綁定碼」、U03 的「草稿先保存」、U05 的「重新開頁與回執」、U07 的「各類查詢與跨帳號隔離」等完整測試已 PASS。因此上表 U01–U17 的特定案例仍保持 `NOT VERIFIED`，待逐案實測後再更新。
- **下一階段唯一入口（2026-10-29 更新）：** U08–U11 已依 Owner Staging 實機回報 PASS，不重做成功路徑。優先補驗 U12–U15（另一帳號隔離／群組忽略／撤銷／功能關閉），以及 U16–U17（六格選單、iOS／Android、Reply/UNKNOWN 恢復）；U01–U07 尚未涵蓋的特定例外情境仍需補驗。Production 切流與 LINE Console 切換須另取證據。
- **發布停止線：** 正式 LINE OA webhook／LIFF endpoint／rich menu 切到 Production 前，須先完成 WI-05 發布所需案例、確認同 SHA staging proof、`LINE_PROD_*` 配置、共享 Secret 版本與 Production 發布 gate。只有一個官方帳號時，切換 endpoint 時 staging 不再假設與正式同時可收訊；Production 正式切流、Hosting、LINE Console 與真人驗收目前全部 `NOT VERIFIED`。不刪舊資料、不重建 LINE 綁定或重新旋轉憑證。

## WI-05B：2026-10-29 第二輪 Owner Staging 實機驗收

- **Owner 明確回報：** `U08–U11 PASS`。本 WI-05 表已分別更新 U08（筆記、待辦、購物）、U09（Google 日曆真實查詢與新增）、U10（Google 日曆授權撤銷的錯誤提示）、U11（活動搜尋、收藏切換與分頁）為 **PASS／Owner reported**。
- **證據界線：** 人工驗收依 Owner 回報成立；沒有新增個別截圖、HTTP trace 或測試執行時間，故不將其冒充自動化測試或 Production 驗證。前輪 Staging release [#40827872508](https://github.com/tommylin15/life_assistant/actions/runs/40827872508) 僅證明當時的 SHA `31326e856ffddd8504ae39260cf7c5facb7a2826`，不能拿來證明後續文件 commit 的新 SHA 已完成 LINE staging release。
- **下一工程入口：** U12 身分／草稿隔離、U13 群組防洩漏、U14 unlink／unfollow 失效、U15 hidden／目的功能權限強制；接續 U16 全選單與行動裝置、U17 Reply 故障與 UNKNOWN 收據恢復。對 U01–U07 尚未測到的重用綁定碼、日期跨日、重開頁、網址及錯誤路徑進行有界補驗。
- **正式上線條件仍未達成：** 尚無完整 U12–U17、必要 U01–U07 邊界及 Production Hosting／Cloud Run／LINE Console 實機讀回收據；維持 `PARTIAL`，不提前變更 OA Webhook 或正式導流。正式發布須符合最新 main SHA 與成功 Staging bundle proof 的同 SHA gate。

## WI-05C：2026-10-29 第三輪 Owner 回報與六格選單現況更正

- **Owner Staging 回報：** U12 跨帳號隔離、U13 群組防洩漏、U14 解除綁定／封鎖、U15 功能權限，分別 **PASS（Owner reported）**。此證據來自 Owner 實機回報，沒有逐案 HTTP trace／遮蔽截圖；不當成新的自動化或正式環境 PASS。
- **U16：NOT VERIFIED（此為製作前紀錄）。** Owner 指出當時六格 Rich Menu 尚未做；本輪新增圖面與可重產程式（見下方 WI-05D），但 OA 實際套用、手機驗收仍未完成。LIFF 八個 tab 不是 OA 六格選單。`--apply` 會影響所有好友，不可在缺乏環境核對與恢復方案時直接執行。
- **U17：NOT VERIFIED。** 行動網路斷線後草稿讀回、Reply API 失敗與 UNKNOWN receipt，需分辨人工作業和受控注入測試。已有單元測試不等於真實 LINE Reply 故障路徑全部通過。
- **唯一下一工程入口：** 六格 Rich Menu 視覺素材／配置／驗證（U16，先安全製作不套用）＋ U17 有界故障驗收；同時補驗 WI U01–U07 尚未涵蓋的特定邊界。正式發布仍是 `PARTIAL`，Production Cloud Run／Hosting／LINE Console 全部 `NOT VERIFIED`。原成功 Staging #40827872508 僅適用 SHA `31326e8`，之後新的 `main` 必須重新取得同 SHA staging bundle proof 才能正式 promotion。

## WI-05D：U16 六格 Rich Menu 素材與程式交付（2026-10-29）

| 層面 | 收據與結論 |
|---|---|
| 可編輯 SVG | `assets/line/rich_menu_v1.svg` 已提交 main，六格與 LIFF action 的 labels/bounds 對齊：SOURCE PASS |
| PNG 產圖 | `scripts/build_line_rich_menu.py` 已提交 main；本地 PNG 2500×1686、198056 bytes，尺寸及 1 MB 限制 PASS（非 OA 實際上傳） |
| 測試 | `tests/test_line_rich_menu_art.py` 驗證 SVG/renderer 一致、格線、文字及 PNG；新 SHA GitHub CI 結果需另查，不因本地測試推定 PASS |
| LINE OA | 真實 LIFF ID、原預設 richMenuId、頻道環境、實際套用與手機實測均 NOT VERIFIED |

**安全執行：** 先看 [素材與安全套用 WI](../assets/line/README.md)，驗證 `python scripts/line_rich_menu.py --liff-id <REAL_LIFF_ID>` 的六個連結再決定是否套用。此輪沒有讀取／旋轉憑證、沒有呼叫 LINE 修改 OA。**U16 仍 NOT VERIFIED；LINE 整體維持 PARTIAL**。U17 及 U01–U07 邊界仍列待辦。

## WI-05E：U16 最終薄荷綠 Life Omni 六格圖片與 Colab 手動套用（2026-10-29）

- **Owner 最新要求優先：** 六格背景維持薄荷綠；右下「Life Omni」使用 Owner 提供的金白與深藍雙生獸意象圖。Owner 已明確選擇**直接覆蓋 LINE 官方帳號預設選單**，不要求舊選單備份／回復方案；不可將本節誤認為已完成套用。
- **正式圖面已上傳 Google Drive，且 metadata 讀回 PASS：** 位於唯一授權根 `life_assistantGPT/LINE_U16_六格選單`（folder ID `13hiG7BMsBiQuOyYygPdqIKF3mztJjPJN`）。LINE 用圖 `Life_Omni_LINE_RichMenu_U16.jpg`：`https://drive.google.com/file/d/1mLdH02yUSubIW_Gha9IzcU5Cbb0nLYEd/view`，2500×1686、447069 bytes、SHA256 `40025281328ae35cb905a40a6bad0ab9982e70995816673032a149d4bc608097`；有紅框的按鈕位置對照圖 `https://drive.google.com/file/d/1VCn88sMjAsd5LLLCFQmbuPghp6EzCY-X/view`，**僅供預覽，絕不能上傳此標註版到 LINE**。Drive 兩個檔案皆讀回 parent folder ID 與 image/jpeg MIME，非公開分享。
- **六格實際按鈕（2500×1686 canvas，格式 x,y,width,height）：** 快速記錄 `163,239,716,563`；今日總覽 `915,239,675,563`；查我的資料 `1626,239,716,563`；待辦・購物 `163,848,716,563`；日曆・活動 `915,848,675,563`；Life Omni `1626,848,716,563`。LIFF pages 分別 `capture/today/search/tasks/calendar/home`。本版是實際卡片對應熱區，不沿用先前的整頁三等分 bounds。
- **LINE 上架方式改為 Owner 直接執行 Google Colab：** Colab 以 Google Drive OAuth 唯讀和上述 image file ID 取得私人圖片，驗證 JPEG、尺寸、大小與 SHA256；Messaging API token 由 Colab `getpass()` 臨時輸入，不存 Drive/GitHub。已知 GitHub Actions 直接套用 run [#40838851219](https://github.com/tommylin15/life_assistant/actions/runs/40838851219) **FAIL**：部署身分缺 `secretmanager.versions.access`，流程在呼叫 LINE API 以前停止。不可因 GitHub CI 或上傳 Drive 成功聲稱 LINE OA 已套用。
- **驗收：** `IMAGE IN DRIVE=PASS`；`COLAB API 實際套用=NOT VERIFIED`；`LINE 手機六格操作／LIFF 返回=NOT VERIFIED`；**U16 維持 NOT VERIFIED，整體 PARTIAL**。待 Owner 回報 Colab 所印的新 `richMenuId` 和 LINE default readback PASS，再進行行動裝置測試。
  
## WI-05F：2026-10-29 Owner 六格操作驗收完成回報

- **真人實測：** Owner 明確回報「六格操作驗收完成」，登錄 **LINE 官方帳號 Rich Menu 六格操作 = PASS（Owner reported）**，不重新要求重做六個按鈕；未附圖或逐格時間戳，不冒充自動測試或 LINE API 回執。
- **圖像版本：** [正式薄荷綠 Life Omni 圖](https://drive.google.com/file/d/1mLdH02yUSubIW_Gha9IzcU5Cbb0nLYEd/view) 經先前 Drive metadata 讀回 PASS；右下「Life Omni」圖示採 Owner 提供的雙生獸意象，標註版僅核對熱區。
- **驗收界線：** Owner 未分別指出 iOS 與 Android 各自測試、LIFF 登入後返回結果，也未在本輪提供 Colab API `richMenuId`／預設 ID 讀回收據；故六格操作 subcase PASS，**U16 完整跨平台／登入返回矩陣仍 NOT VERIFIED**。不憑 Owner 操作回報推定 LINE Production Cloud Run/Hosting 已部署。
- **CI 問題與排除：** `main` 在本次回報前的 [CI #40841479917](https://github.com/tommylin15/life_assistant/actions/runs/40841479917) = FAIL，backend 契約測試 `test_push_does_not_enter_mutation_steps_and_legacy_is_manual` 因早前 `line-u16-apply-once.yml` 使用 push 而失敗；同檔 [套用 Run #40838851219](https://github.com/tommylin15/life_assistant/actions/runs/40838851219) = FAIL，缺少 `secretmanager.versions.access`，**它沒有成功套用選單**。既已採 Owner Colab 途徑完成真人六格操作，該舊一次性 GitHub Workflow 已從 `main` 移除；新 SHA CI 結果須另核對，不能把舊 FAIL 寫成 PASS。
- **下一唯一入口：** U17 Reply 失敗、連線中斷與 UNKNOWN 回執的有界驗收；補 U01–U07 的特定邊界路徑及 U16 尚未明確記錄的跨手機平台／登入返回子項。**整體 PARTIAL；LINE Production NOT VERIFIED，不標 DONE**。

## WI-05G｜LINE V2-01 活動 Flex 真人驗收（2026-10-29）

**目前僅建立 Source 與測試；以下是 Staging／Owner 人工驗收指示，不是已執行結果。** 正式規格：[LINE v2 重構規格](line_v2_conversation_refactor_spec.md)。

### 準備

- 先核對最新 `main` SHA 的 Backend／Flutter／PostgreSQL／部署 CI 全 PASS，確認有新版本部署到 **enable_line=true 的 Staging**，不是自動 Staging 預設 `enable_line=false` 的部署。V3 手動發布要保留 `promote=false`、`publish_staging=true`、`enable_line=true` 與同 SHA bundle proof；**本輪不切 Production、不改目前六格 OA**。
- 既有 LINE OA 若仍指向 Stage，確認其真實 Webhook／LIFF origin 與測試帳號綁定仍有效；不可因 GitHub source 已寫好就假設真 LINE 已更新。
- 此版無需替換 OA Rich Menu。從 LINE 官方帳號一對一聊天直接送出確切文字「**活動**」「**活動分類**」「**已收藏活動**」；這三個指令應直接回卡片，不應存成草稿。將來八格圖面的「活動」入口應用 `postback.data=v=2&cmd=events.latest`，目前不先套用。

### 真人操作紀錄（每項 PASS／FAIL／NOT VERIFIED）

| 驗收項 | 操作／預期 | 狀態 |
|---|---|---|
| V2-01-A 最新上架 | 發「活動」→ 回 Flex Carousel，左右滑；每批最多 6 張，依 Life **初次收錄 created_at** 近到遠，活動／官方發佈日期不可假冒 | NOT VERIFIED |
| V2-01-B 欄位與空值 | 各卡片顯示日期／地點／原始 category／費用／核證狀態；缺資料顯示未知，連結只開既有 HTTPS 來源 | NOT VERIFIED |
| V2-01-C 分類 | 發「活動分類」→ 只顯示 Life 真實 category，點選回同分類最新卡片；換分類、更多分類及零結果可操作 | NOT VERIFIED |
| V2-01-D 下一批 | Flex Quick Reply「下一批」→ 不重複同活動主群組、排序固定，結果更新能安全提示重新開始 | NOT VERIFIED |
| V2-01-E 收藏 | 卡片按「收藏」→ 再按「已收藏活動」可看到，登入 Life Explore/收藏清單核對 PG 狀態；再取消收藏讀回一致 | NOT VERIFIED |
| V2-01-F 再按與防重 | 重複點同一張舊卡片「收藏」不能反覆反轉；WebHook 重送同 event ID 在單元／整合測試僅一次 Reply，原資料不重建 | NOT VERIFIED |
| V2-01-G 權限 | 不同 Life/LINE 帳號的收藏隔離、解除綁定/封鎖、功能 hidden、過期操作按鈕應拒絕；群組不可洩漏私有內容 | NOT VERIFIED |
| V2-01-H 不破壞 v1 | 原六格 URI/LIFF、快速記錄、草稿、查詢、既有 Staging 簽章／登入運作仍正常 | NOT VERIFIED |
| V2-01-I 異常情境 | 無活動、無來源、未授權、外部來源連線問題、Reply 未送達皆不謊稱資料已寫入，結果不明不自動重建 | NOT VERIFIED |

### 故障與恢復

- Flex 只是活動資料呈現；所有資料仍在 Life PostgreSQL。LINE 卡片未到時，不代表收藏／新增失敗，先回 Life 確認。
- 只有 `source.type=user` 且已綁定、line/Explore feature 可用才執行；跨帳號 Postback 會拒絕，無權限不給資料。
- 不在 LINE Webhook 做泛用 Agent loop、任意 Google OAuth、無界重試、群組私有查詢。U17 的 UNKNOWN receipt／Reply fault-injection **另依 v1 WI 做完整驗收**。
- Owner 回報以上實機結果後再分別標記；**無收據不把 V2-01 標 DONE**。下一步才是 V2-02 八格圖片／Rich Menu 設定。

## WI-05H｜LINE-V2-02 八格 Rich Menu 製作與上架驗收（2026-10-29）

> 八格**圖面已製作、程式已提交、Drive 讀回 PASS**；這不等於已呼叫 LINE API 上架。原六格操作 Owner PASS 僅屬 v1；本版要求獨立的 OA API 與手機驗收。完整素材／點擊表見 [V2-02 Asset WI](../assets/line/README_V2.md)。

### 圖面、區域與行為

- **正式圖 Drive：** `life_assistantGPT/LINE_U16_六格選單/life_omni_v2_eight_grid.jpg`，檔案 ID `1mB_15NAsxDyj3ZGikP4x7FT30Mf4gx2O`，JPEG 2500×1686、289918 bytes、SHA256 `33b2460021d41c71ba56cbd90830361205f01c46d30623f60d4e413e4c794f86`；Drive metadata 讀回符合資料夾／MIME／檔案大小。
- **核對圖（不可上傳）：** `1yxrBJBiroarM0yXJE01Eg8Qr2cjAscdU`；紅框只供確認 8 區。
- **八格順序與座標：** 上排 (1) 快速記錄 `0,0,625,843`，(2) 今日總覽 `625,0,625,843`，(3) 查我的資料 `1250,0,625,843`，(4) 待辦 `1875,0,625,843`；下排 (5) 購物 `0,843,625,843`，(6) 日曆 `625,843,625,843`，(7) 活動 `1250,843,625,843`，(8) Life Omni `1875,843,625,843`。
- **動作：** 前七格 `postback`：`v=2&cmd=capture.start`、`today.view`、`search.start`、`tasks.list`、`shopping.list`、`calendar.today`、`events.latest`；第八格 `uri` 直接 Life Hosting `/today`。目前只有活動對話卡屬 V2-01 實作；前六格需等 V2-03，**這版先沿用 LIFF fallback**，不可誤標功能已升級。
- **GitHub：** `scripts/line_rich_menu_v2.py`、`scripts/build_line_rich_menu_v2.py`、`tests/test_line_rich_menu_v2.py`；原 v1 六格程式與表、資料保留。

### 正式上架程序（Owner Colab）

1. 先看最新 main SHA 的 GitHub CI，必要時先完成修正；確定該 SHA 已部署到 `enable_line=true` 的相符環境，且 **GET /api/v1/line/config HTTP 200 + 正確 origin／LIFF ID**。前輪 [V3 #40852323202](https://github.com/tommylin15/life_assistant/actions/runs/40852323202) 雖 `success`，讀到 `LINE_ENABLED=false`，**不能當作 LINE-enabled 證據**。
2. 開啟本輪 `Life_Omni_LINE_V2_02_Eight_Grid_Apply.ipynb` Colab Notebook（下載後用 Colab 開啟）；設定 `TARGET=stage/prod`。程式用 Google Drive 身分下載固定 ID 的私人 JPEG，驗證 **SHA256／尺寸／<=1MB**，打印八格熱區及實際 postback。
3. 在 `getpass()` 隱藏輸入框貼 LINE **Messaging API Channel Access Token**（非 Channel Secret），先透過 LINE `/v2/bot/info` 看 OA 名稱；Colab 確認同環境 Backend 200 後，輸入 OA 名稱才執行。
4. Colab 依序建新 Menu、上傳 JPEG、直接覆蓋全好友 OA 預設、GET `/v2/bot/user/all/richmenu` 讀回；Owner 已允許直接覆蓋、不要求舊選單備份。不可在登入失效或 LINE backend `503` 時強制改預設選單。
5. 只有輸出 `LINE_V2_DEFAULT_MENU_API=PASS` 和真實 `richMenuId`，才能標示 **LINE OA API 套用=PASS**；否則 **NOT VERIFIED/FAIL**。Token 不記錄到 CI、Drive、GitHub 或回報訊息。

### 手機與整合驗收矩陣

| 案例 | 預期 | 本輪證據 |
|---|---|---|
| V2-02-A 圖面／熱區 | 8 個獨立可點區，0–2500、0–1686 全涵蓋、圖文一致 | **SOURCE PASS；官方套用 NOT VERIFIED** |
| V2-02-B 後端前置條件 | LINE-enabled 同環境、OA webhook 可回 Postback，綁定/授權正常 | NOT VERIFIED |
| V2-02-C OA API | 新 `richMenuId`、圖片成功上傳、default ID 讀回相同 | NOT VERIFIED |
| V2-02-D 前六格 | 在 LINE 內按 1–6 格有正確 LIFF fallback，不誤當 v2 卡片已完成 | NOT VERIFIED |
| V2-02-E 活動 | 按 7 格真的顯示最新 Flex Carousel，分類、收藏、下一批可用 | NOT VERIFIED |
| V2-02-F Life Omni | 第 8 格直達 Life Web `/today`；有／無既有 Google Session 皆正確 | NOT VERIFIED |
| V2-02-G 手機 | iOS/Android 分別檢查圖片、八格命中、文字顯示、登入與返回 | NOT VERIFIED |
| V2-02-H 回歸 | 舊 v1 草稿／綁定／已有正式資料保留，操作新選單不刪資料 | NOT VERIFIED |

**本輪狀態：** V2-02 source／圖檔／Drive PASS；OA default API、手機、全功能整合 = NOT VERIFIED。不得因文書或 GitHub CI 就標 DONE。V2-01 的真 LINE Flex 驗收 WI-05G 與 v1 U17 異常驗收仍保留。

## WI-05I｜2026-10-30：LINE Staging 遭自動發布關閉的根因與修復

**Owner 實測：** LINE Channel Access Token 驗證 `LINE_OA_AUTH=PASS`，但 V2-02 Colab `GET https://life-assistant-v3-stage-tl15.web.app/api/v1/line/config` 為 **503**，因此 Colab 依保護門檻停止，**沒有更換 OA 預設八格選單**。

**可追溯根因：** [V3 #40857785208](https://github.com/tommylin15/life_assistant/actions/runs/40857785208) 曾以 `LINE_ENABLED=true` 通過同版 Staging；但後續 [V3 #40981334221](https://github.com/tommylin15/life_assistant/actions/runs/40981334221)、[V3 #40982431521](https://github.com/tommylin15/life_assistant/actions/runs/40982431521) 自動 Staging 以 `LINE_ENABLED=false` 發布，令原先 LINE-enabled 的固定 Staging 被覆蓋。現有 `line_channel.configuration()` 當 `LIFE_LINE_ENABLED != true` 或缺必要設定時回傳應用程式 `503 {"detail":"LINE integration is not configured"}`。這是**部署與測試環境衝突**，不是 LINE Token、Rich Menu 圖片或額外 Secret/IAM 權限問題。

**防護修復（Source 已提交、CI 依最新 main 獨立判定）：**

- `scripts/line_staging_guard.py`：只讀固定 Staging 的公開 `/api/v1/line/config`；HTTP 200、未知 HTTP、網路故障或非標準 503 → `HOLD`，**禁止一般自動部署**；只有連續兩次讀回應用程式**精確** `503 {"detail":"LINE integration is not configured"}` → `ALLOW`。
- `.github/workflows/v3-auto-staging-after-ci.yml`：原 CI/sha/GitHub Gate 通過後，先跑 LINE guard；若 `HOLD` 則不 dispatch V3。若 `ALLOW`，以 `auto_staging=true, enable_line=false, promote=false, publish_staging=true` dispatch，便於 V3 識別機器自動作業。
- `.github/workflows/v3-release-ghcr.yml`：增加僅供自動派工識別的 `auto_staging` bool；當自動 Staging 要以 `enable_line=false` 覆蓋時，在 **Cloud Run 候選建立之前** 重查相同 guard；LINE 若在派工後才變成啟用，V3 提前 FAIL 且不變更候選或流量。**人工明確選擇 `enable_line=false` 的維護作業不被偷改語意**。
- `tests/test_line_staging_guard.py`：覆蓋 LINE enabled／明確 disabled／網路與 503 誤判／派工與發版競態，以及 workflow 靜態契約。原有 `test_cloud_build_v2.py` 仍約束不自動 Production promote。
- 代價：**當 LINE 測試環境正在使用時，一般程式提交不再自動更新固定 Staging**；要在保留 LINE 的前提取得新版功能，需人工使用同 SHA `enable_line=true` 進行 Staging Release。這比暗中覆蓋 LINE 環境安全，也不擴權。

**本次回復操作（只限 Staging）：**

1. 等待最新 main 同 SHA CI（backend／flutter／deployment-scripts／free-events-postgres／gmail-onnx-image）完全 PASS，確認沒有其他更舊的 V3 自動發布正在競逐 staging。
2. GitHub → `V3 Release - GHCR to Cloud Run` → `Run workflow`：branch `main`；`promote=false`、`publish_staging=true`、`enable_line=true`，`enable_gmail_onnx` 保持原本產品需要的設定，`auto_staging=false`（預設）。
3. Release 必須有 `candidate_health/ready=PASS`、`line_candidate_config=PASS`、`preview=PASS`、`staging_live=PASS`；**成功的 Staging Hosting PASS 仍不表示 OA Console Webhook 已指向 Stage**。
4. Colab **只重跑原第 3 格**：`LINE_OA_AUTH=PASS`、`LINE_BACKEND_READY=PASS` 且 origin／LIFF ID 與 Staging 一致，並確認 LINE OA Webhook 入口也為相同環境；才可執行第 4 格套用八格並核實 `LINE_V2_DEFAULT_MENU_API=PASS`、`richMenuId` 與 LINE 手機八格實測。
5. 檢查後續任一 CI 的 `V3 Auto Staging After CI` 摘要：LINE active 應有 `line_staging_guard=HOLD` 和 `auto_staging=SKIP existing_LINE_staging_or_unknown_status`；不能把 skip 當成新功能已部署。

**狀態：** 根因（GitHub logs）PASS；guard implementation（GitHub readback）PASS；完整 CI／自動派工 guard 實際執行／LINE-enabled Staging 恢復／OA default Menu／真手機操作應各按當輪證據標 `PASS / FAIL / NOT VERIFIED`。只因文件、CI 或沒有驗證的舊 release，不得宣稱 V2-02 DONE；原 v1 草稿、綁定、資料不得清除。

## WI-06：停用與復原
先在後台將 line 設為 hidden，或正常 V3 部署 enable_line=false。LINE session 每次請求會重查綁定與 rollout。保留 0023/0024 資料表；不執行 downgrade、不清空 Life。正式發版仍依既有 V3 gates，CI 綠燈不代表真人 LINE 整合完成。
