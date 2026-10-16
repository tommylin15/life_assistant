# Google Drive 檔案總管 V1｜Life Assistant
日期：2026-10-16（Asia/Taipei）
狀態：APPROVED DIRECTION / IMPLEMENTATION NOT VERIFIED。正式實作與驗收以 GitHub main 和 runtime 為準。

## 產品定位
重整現有 Google Drive 智能整理成真正的檔案總管：可在 Life 以手機/桌面瀏覽資料夾、搜尋、預覽、開啟、修改與移動檔案。Google Drive 仍是原檔 source of truth；Life PostgreSQL 只保存授權、明確關聯的最小 metadata、設定和必要稽核。不可建立另一套完整文件副本或全文索引。

## 既有實作（盤點基準，未驗證 live）
- Flutter `lib/web/drive_page.dart`：Google Picker 明確選取、登錄文件、筆記關聯、AI 標籤/相關筆記建議。
- API `backend/app/api/drive.py`：workspaces、picker-config、documents、project link、enrichment/refresh。
- OAuth `backend/app/services/google_oauth.py` 使用 `drive.file`；不能假設能直接瀏覽使用者雲端硬碟的所有既有檔案。
- 既有 Drive→Notes 一次性匯入、Project 關聯、AI 同意／快取要保留，不要重建。
- Drive 2026-09-30 舊討論偏「逐檔 Picker」。本輪新需求明確要求檔案總管；舊文件仍為歷史設計、**不再單獨代表全檔案總管的核准功能範圍**。

## V1 預期操作
1. 左側／手機抽屜：我的雲端硬碟、最近使用、已加星號、資料夾樹或麵包屑；列表／網格切換、排序與分頁。
2. 搜尋：檔名、檔案類型、日期、目前位置；內容搜尋僅在 scope 與來源正式支援時啟用。
3. 預覽與開啟：圖片、PDF、TXT/Markdown 安全可讀預覽；Docs/Sheets/Slides 使用 Google 官方編輯器、保留來源連結。不能假稱 Life 已有 Google Docs 全格式編輯器。
4. 編輯：V1 可在 Life 直接編輯安全的純文字類型並寫回；Google 原生文件優先從 Life 開啟原生編輯器。進階原生內容修改應另走 Google Docs/Sheets/Slides API、檢查 revision/ETag 與寫入權限。
5. 檔案管理：新建資料夾、上傳、重新命名、複製、移動、移至垃圾桶、下載；每個操作需使用者明確觸發，與讀取/寫入 scope 適配，批次危險操作需確認與部分失敗回報。第一階段不做永久刪除。
6. 與原有專案、筆記、AI 標籤共存；移動或重新命名原檔時，用 Google File ID 保持關聯穩定。

## 關鍵風險及選擇
- **OAuth：** `drive.file` 是以使用者選擇的檔案為基礎。若要原生全 Drive 階層管理，須先確認 `drive.metadata.readonly` / `drive.readonly` / `drive` 等 scope 能力與 Google restricted scope 審查／安全成本；不應為了做 UI 就自動擴大正式 OAuth scopes。
- 建議兩階段：A 保留目前 `drive.file`＋Picker，在已明確授權的範圍做可用檔案管理；B 若真的要「整個 Drive」檔案總管，先完成合規方案和全帳號權限測試才引入更廣 scope。 UI 應誠實顯示「已選取文件」與「完整雲端硬碟」模式差異。
- **讀寫安全：** 使用者 Google ID/Scopes 與 Life Session 對應；Cross-tenant 401/403、Google revoke 與刷新失效測試；寫入前比對修改版本、衝突提示，不默默覆蓋外部修改。
- **檔案安全：** 防止無限制大檔預覽、惡意內容/XSS、意外敏感外洩；來源原文不預設送 Gemini，需個人 consent。
- **效能：** Google server-side pageToken 搜尋/分頁、依需預覽、短期快取；不做夜間全 Drive 同步或無限制掃描。

## 單一工程工項與驗收
工作追蹤位於 `doc/todo.md` P1-G2，不另外建立重複 active TODO。
完成要分開驗證：Backend/Flutter implementation；權限與檔案操作 tests；四項 CI；Staging；真實授權帳號的「瀏覽→預覽→開啟→修改→原 Drive 讀回→移動→再讀回」；原有 Picker／AI／筆記／專案回歸；正式部署與 runtime。
全程 PASS / FAIL / NOT VERIFIED，未完成不可標 DONE。
