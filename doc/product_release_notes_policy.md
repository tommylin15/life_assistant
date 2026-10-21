# Life Assistant｜版本與使用者更新公告（2026-10-18）

## 目標與唯一來源
- 版本記錄使用 Flutter `pubspec.yaml` 的 `MAJOR.MINOR.PATCH+build`；正式身份仍為 Git SHA（現有 `release.txt`）。
- 首版候選 `0.2.0+2` 已完成 CI 與 staging；尚無已核證 production Hosting。當前下一候選版本為 `0.3.0+3`。舊 `0.1.0+1` 只是既有 source 值，不代表已查證正式版顯示該號；禁止倒填歷史上線版本。
- 兩條 Web build（V3 staging/Preview 與 Production Hosting）從同一份 pubspec 注入 `LIFE_APP_VERSION` 和 `LIFE_RELEASE_SHA`；版本文字僅作友善顯示，安全與發布驗證仍以同 SHA／digest／正式 readback 為準。

## 使用者體驗
- 在左側選單底部的「個人化」旁保留「最新消息」；手機抽屜、桌面側欄一致；不新增首頁常駐卡、不強制彈窗、無 Email 或推播。
- 公告僅寫使用者實際能感受的功能、操作方式、穩定性修復。每條一小句，原則上一版最多三條；不顯示 API、migration、CI、執行批次、診斷或未驗證項目。
- 版本資訊同頁顯示。候選環境可見 SHA 識別碼；正式環境只有友善版本及公告。
- 小圓點僅表示有未讀更新。首次進入該頁才記已讀；目前為同帳號、同瀏覽器、同環境本地記錄，跨裝置已讀同步不保證，無個資內容入 LocalStorage。

## 版號與發布規則
- MAJOR：需使用者重新適應的重大不相容變更；MINOR：新增使用者可見功能／較大 UX 改善；PATCH：小修正。build 整數在每次正式候選版更換時遞增，不為每筆 commit 新增公告。
- 新版說明先由開發端整理並人工核對，不直接把 Git commit 訊息或驗收狀態露出給使用者。
- **候選 CI PASS 不等於已發布**。只有既有 V3 promotion、正式 Hosting 及相同 SHA／runtime gates PASS 後，才可將該版視為正式上線；公告隨該版前端一起交付，若回滾則跟著回滾。
- 功能未對所有人開啟時，不得對所有使用者宣稱可用；只能在可見範圍一致時公告，或以對應 feature flag 控制公告。現行公告只描述全站的「最新消息」本身。
- 絕不為補上版本號而大幅改寫現有 Cloud Run／Firebase 部署方式、授權或資料庫。

## 2026-10-19 補強契約
- P0：每則公告可指定 `featureKey`；未拿到該帳號 `effectiveFeatures` 或沒有開放時一律不顯示。未讀依可見公告 ID 集合計算，功能之後開放可再提示，同帳號同瀏覽器環境隔離，閱讀完成應即時消除小圓點。
- P1：每十五分鐘、前端恢復前景時，GET 同站 `/release.txt`（no-cache，帶 query）；僅收到完整 40 位 SHA 且不同於內建 SHA 才顯示非阻擋重新整理提示，不能將 HTML fallback / API revision 或網路失敗當作更新。後台不啟動另一支 worker。
- P1：只有 Backend 發布的使用者可感知修復由後端輕量唯讀 `GET /api/v1/release-notes` 提供，資料是 source-owned 的 `PUBLISHED_NOTES`，預設空列表，無新資料表、不需要定時任務。不為尚未經證據核實的修正事先填入公告。後端獨立部署不更改前端友善版本號，顯示為「維護更新」。
- 高風險需強制重新登入或相容升級仍走獨立重要服務提示流程，不能讓一般更新卡取代。
- `0.3.0+3` 新候選僅列這次功能，不能由 staging 的成功宣稱 production 已發布。

## 驗證與之後可補強
- Flutter 測試：版本比較、舊版本不顯示未發布公告、不同帳號／候選正式標記隔離、桌面／手機有入口。
- 發布驗證：候選讀到新版本與 SHA、正式成功才可見相同版本、rollback 能恢復舊頁面與公告；無證據則標記 NOT VERIFIED。
- 之後若需要跨裝置同步已讀狀態，再以現有個人偏好 API 後端保存，不另起獨立通知 DB／服務。
- 大範圍相容性問題（需要立即重新整理、版本不相容）應獨立實作更新提示；不要拿一般更新公告冒充強制更新機制。

## 2026-10-21｜開發與發布時自動判定的正式門檻

- **主動判斷、不等使用者提醒：** 每項工作先核對實際 GitHub 差異，標註 `USER_VISIBLE`（新增功能、操作調整、可感知 bug）或 `INTERNAL_ONLY`（測試、CI、治理、不可見維護）；沒有公開效果的改動不寫公告。
- **版號以「正式發布候選」為單位，絕非每個 commit 一次：** `0.4.0+4` 彙整已正式發布但遺漏公告的 Gmail 雷達精簡，以及已通過 Staging 驗收的快速新增多事項拆解。未來遵循 MAJOR/MINOR/PATCH＋build 遞增，合併同批次的使用者可見變更。
- **候選與正式分開：** 將公告寫進 `lib/web/release_info.dart` 和版本寫進 `pubspec.yaml` 只產生候選；Staging 顯示候選。只有 Production V3 + Firebase Hosting 相同 SHA 的 live readback PASS，才可標示對外上線。公告依 `featureKey` 限制可見帳號。
- **正式發布必須檢查：** `scripts/check_user_release_metadata.py` 比較目前 Production `/release.txt` 的 SHA 與候選 SHA 之間的 Git diff。含使用者可見的 Flutter 檔案就必須有遞增 semver/build 與新版簡短公告；Gmail 雷達和生活快速新增額外檢查 featureKey。未達標擋下 Production promotion 和獨立 Firebase Hosting，不阻礙開發中 CI／Staging。正式版來源不可查或 SHA 不正確即 FAIL closed。
- **Backend-only：** 依 `backend/app/api/release_notes.py` 與人工 code review 判斷使用者可感知變更，正式驗證後才能更新 source-owned `PUBLISHED_NOTES`；不強制每個 backend commit 升 Flutter 版號。機械檢查無法取代所有語意判讀。
- 以上只重用現有 V3 發布門檻，不新增外部 AI、DB、排程或額外 GCP 服務。
