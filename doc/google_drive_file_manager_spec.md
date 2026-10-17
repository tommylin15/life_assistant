# Google Drive 檔案總管｜Life Assistant（唯一現行規格）

更新：2026-10-17（Asia/Taipei）

## 產品決策

- **取消「Google Drive 智能整理／AI 標籤／AI 文件管理」的使用者功能與操作入口。** 左側導覽／個人化統一顯示「Google Drive 檔案總管」。
- 唯一入口 `/more/drive` → Flutter `DriveExplorerPage`；舊網址 `/more/drive/files`、`/more/drive/settings` 轉址至此，不能跳回原智能管理。
- **原 Drive 檔案與既有 Life 筆記／專案關聯不可刪除。** 舊 AI 相關儲存資料、資料表與後端相容 API 先保持不變但不在新檔案總管觸發，避免破壞歷史資料與其他功能；待依相依證據評估移除。這不表示 AI 功能仍被產品保留。
- 不額外使用 Gemini、不自動分析全文、不建立夜間同步，也不主動擴張 Google OAuth 權限。

## 目前連線為何只看得到部分檔案

1. 登入 Life 的使用者在「個人化 → Google 服務連結」授權自己的 Google 帳號；Drive scope 維持 `https://www.googleapis.com/auth/drive.file`，是**逐檔授權**，並非全帳號唯讀或全帳號修改。
2. 從檔案總管「選取更多檔案」開啟 **Google Picker**。Google Picker 可在本人 Google Drive 中挑選，但只有被 Picker 選取／Life 建立的檔案才進入 Life 可讀取範圍。選取某資料夾**不保證自動授權其所有已存在／未來新增的子檔案**；要在 Life 看子檔，仍須逐檔選取。
3. Life 前端 `GET /api/v1/drive/manager/files` 使用本人受保護的 Google OAuth token，透過 Google Drive `files.list` 列出**該應用程式可見**的檔案，50 筆一頁，有更多資料時用 pageToken 接續；搜尋只涵蓋此可見範圍。
4. 使用「在 Google Drive 查看全部檔案」會跳至官方 Drive 網頁，能看 Google 帳號本身允許的全部檔案。這**不會自動擴大 Life 存取權**。
5. 若要 Life 內直接**原生瀏覽整個 Google Drive**（包含從未由 Picker 選取的檔案），須另行評估 Google `drive.metadata.readonly`／`drive.readonly`／`drive` 等較廣（可能 restricted）的 scopes、驗證及安全成本；在使用者選擇前不得逕行變更正式 Google OAuth scope。

## 現有檔案總管動作

- 目前已授權清單、麵包屑資料夾導航、搜尋與分頁。
- Picker 逐檔選取／選取資料夾、Life 建立新資料夾、開啟 Google 原始檔案、重新命名及移動（受授權及來源版本驗證限制）。
- TXT／Markdown／CSV／JSON 的小型文字預覽與明確儲存（64KiB 限制，版本／內容比較及讀回），Google Docs／Sheets／Slides 仍以官方編輯器處理。
- 上傳／複製／完整 Drive 全資料夾瀏覽／完整單筆深連結未宣稱已完成；不可把已選取文件等同整個 Drive。

## 驗收門檻

- 同一 main SHA 完成 4 CI；確認舊「智能整理」不再出現在導航及新版檔案總管 UI，不觸發 AI。
- 確認 Picker 選取檔案與資料夾後由 Google 授權與本人的 API 讀回；選取資料夾不誤顯示未授權子檔案。
- 使用者 A/B Google scope、資料隔離、原檔修改與衝突防護、手機端選取與讀回、舊筆記／專案關聯不變。
- 固定 Staging 與正式發布須各有真實 CI/GitHub release/runtime 證據；尚未驗證為 NOT VERIFIED，整體 PARTIAL。

唯一工作追蹤：`doc/todo.md` P1-G2。
