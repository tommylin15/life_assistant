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
| U16 | 官方帳號六格 Rich Menu（完成製圖／套用）及 iOS/Android 開啟與登入返回 | 應先有 OA 六格選單、六個 LIFF deep links；頁面可操作、無溢出 | NOT VERIFIED（SVG／產圖程式 source PASS；本地 PNG 尺寸／大小 PASS；OA 未套用、手機未驗證） |
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

## WI-06：停用與復原
先在後台將 line 設為 hidden，或正常 V3 部署 enable_line=false。LINE session 每次請求會重查綁定與 rollout。保留 0023/0024 資料表；不執行 downgrade、不清空 Life。正式發版仍依既有 V3 gates，CI 綠燈不代表真人 LINE 整合完成。
