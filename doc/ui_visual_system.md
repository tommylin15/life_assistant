# Life Assistant — 可實作的三風格 UI 系統（2026-10-11）

本文件是「六功能 × 三風格」概念海報轉成 **Flutter Web 可維護實作**的規則；**海報不代表已完成的 runtime 畫面**。功能狀態仍以 GitHub main、CI、staging、production 各自的證據為準。

## 主題與共用規範

- 三種視覺風格：`warm` 暖心日常、`fresh` 清新活力、`focus` 知性專注。
- 三種亮暗模式：`system`／`light`／`dark`，與視覺風格獨立；共 9 組實際可配置的外觀。
- 只維護 **一套 Flutter Material 3 元件樹**。透過 ThemeData、功能語意、間距和尺寸變化實現差異，不建立三份頁面，不以整張概念圖作為背景。
- 導覽與首頁卡片偏好繼續使用既有 API。現行外觀設定先採帳號隔離的 **瀏覽器 localStorage**，所以僅本瀏覽器保存；**跨裝置同步 NOT IMPLEMENTED**。後續若擴充後端偏好須獨立設計 additive migration／相容預設，並提供真實整合驗收，不能以 UI 切換冒充同步。
- 只用真實 API 資料顯示日期、名額、報名狀態、任務數、進度與封面；缺值明示未知或不顯示，不渲染海報中的虛構數據。
- 不從未授權網站複製圖片。活動無適用封面時，以色塊、功能圖示與來源摘要回退。
- 手機採底部／抽屜、桌面採側欄；保留現有 responsive breakpoints、鍵盤、焦點、文字放大及最小觸控面積。
- 互動動畫需遵循 reduced-motion；不能擾亂待辦完成、日曆日期標記、活動來源 URL 等既有語意。

## 六功能的可落地視覺

| 功能 | 設計情緒 | 現行第一階段 | 後續細化（不屬已交付） |
|---|---|---|---|
| 待辦 | 有條理、易開始、完成感 | 任務色與專屬 header | 精簡 progress overview／完成動效，所有百分比基於實際 tasks |
| 活動探索 | 心情愉快、想出門 | 探索色與專屬 header | 授權封面、地點／日期圖示、分組卡片 |
| 限時機會 | 想參與、開報易辨識 | 報名色與專屬 header | 開報時間區塊、來源 CTA、收藏／加入待辦 |
| 日曆 | 溫馨、秩序、安全 | 日曆色與專屬 header | 事件色點與全天 transparent 活動標記，不占忙碌時間 |
| 專案 | 專業、掌控感 | 專案色與專屬 header | 真實任務進度與關聯面板，不虛構人數／百分比 |
| 筆記 | 想隨手記錄 | 筆記色與專屬 header | 快速輸入、可讀的摘要卡片、經授權的封面 |

限時機會的 CTA 只能清楚連至原站報名／資訊，不代表 Life 已替使用者報名；不得使用無據的倒數、名額或「已完成報名」。活動 V3 只保留兩個入口，不能因視覺樣稿把第三個「精選池」導覽恢復。

## 本批 source 實作範圍

- `lib/web/visual_system.dart`：風格、亮暗、Material Theme 與六個功能的共用 header。
- `lib/web/appearance_storage*.dart`：瀏覽器 localStorage 實作與非 Web 測試 fallback。
- `lib/web/web_app.dart`：將所選外觀套用至 MaterialApp；不改路由或資料操作。
- `lib/web/personalize_page.dart`：立即切換三風格／亮暗模式，註明僅本瀏覽器保存。
- `lib/web/tasks_page.dart`、`projects_page.dart`、`notes_page.dart`、`calendar_page.dart`、`curated_events_page.dart`：同一套共用 header／色彩系統。
- `test/visual_system_test.dart`：測試三種 palette、帳號狀態分離與六個 Flutter Widget header。

上述描述為 source change，**不表示 flutter analyze、widget tests、CI、staging、runtime 已 PASS**。

## 實際驗收條件

1. `flutter analyze`、`flutter test`、Flutter Web production build 都通過，保留既有 API/backend 測試。
2. 以 320 / 375 / 768 / 1440 CSS px 實測三風格、淺／深色的六個功能；沒有溢位、不可見按鈕、文字被圖蓋住。
3. 三個主題在切換時立即反映，重新整理仍是原值，同一瀏覽器換帳號不洩露彼此設定；儲存停用可正常降級。
4. 所有六個功能仍可透過原本 API 操作，不因 UI 變更影響任務、日曆、專案、筆記或活動來源連結。
5. 鍵盤操作、對比度、reduced motion、文字縮放、亮暗及 loading / empty / error 狀態檢查。
6. GitHub CI、staging Hosting release SHA、API rewrite、實際登入和可操作畫面各自驗證。**未取得真實畫面證據不得宣稱與海報相同。**

本批定位：**implementation PARTIAL，runtime NOT VERIFIED**。待功能與視覺驗收後，再決定是否加強素材資產、卡片版式與跨裝置偏好同步。


## 2026-10-11 聯合交付：視覺系統 + 活動 UX V3

同一批 source 修改包括：
- Material 三風格／亮暗模式、六功能專屬 accent/header、首頁卡片、待辦／專案／筆記細節。
- 新版活動「限時機會／活動探索」兩個入口，舊 /more/curated 和 /more/events 相容轉向 /more/explore；舊 events 導覽偏好映射至 explore，保留首頁 events 卡片資料。
- API: 主活動群組 server-side 5+10 查詢、時間／最新速查、標題／主辦／地點／摘要中文包含搜尋、地區／縣市／類別／費用、共享已收藏模式。星等保留 DB，不再做 UI 篩選及預設排序。
- 收藏主活動、Task 顯式日期選擇、Google Calendar 全天透明日期標記。活動專屬 HTTPS 網址在 Task 和 Life Calendar 可直接開啟；不臆造已報名、時段或名額。
- 保留舊個人 action 資料和 API；V3 UI 只顯示收藏／建立待辦／日曆日期標記。
- \`backend/tests/test_curated_v3_query.py\` 與 \`test/activity_link_test.dart\` 追蹤重要查詢、連結與日期規則。

**驗收不得跳級**：
- Flutter / backend 測試、CI、release、runtime 和整合各自列出 PASS / FAIL / NOT VERIFIED。
- 真實使用者的 OAuth／Calendar readback、Task DB readback、群組分頁讀回與手機／桌面對照畫面須待 staging 驗證。
- 現有 preference 外觀儲存仍為本機／帳號隔離，跨裝置雲同步仍未實作。
- 部分 UX 例如所有行政區選單、跨查詢穩定 snapshot cursor、高密度海報插畫還需根據真實資料與視覺檢測調整，不宣稱已完成。

本批 source 為 PARTIAL，只有全部 CI + staging + 實際操作均核實後才可能標 DONE。


## 2026-10-11 UX V3 後續一致性修正（本次合併驗收）

- 主活動收藏保存為依 `handoff:event_key` 推導的帳號私有穩定動作鍵，不依網址 identity；既有子場次收藏仍可查詢、在下次切換時合併，不需要 destructive migration。
- 限時機會排序只採未過期且有據的報名開放／截止時間；無據的時間不得取活動日來偽裝開報。
- 活動卡片的待辦、Google 全天日期標記可明確取消／移除；對人工更改過的 Google 事件做基準比較，資訊不符拒絕自動刪除。沒有歷史基準的舊事件也不盲目刪除。
- 新增 PostgreSQL 帳號隔離／父活動 identity 變更收藏測試與 Calendar 人工編輯保護測試。

**未決驗收：** 本次修正後的新 SHA 需完整 CI、固定 staging SHA、owner Google callback+session、PostgreSQL／Task／Calendar 實際讀回、320–1440px 及三風格實際 UI；未具備時維持 PARTIAL。若 staging 因 owner OAuth 沒有在單次 canary 期間內完成，嚴格標 FAIL，不能繞過當作 PASS。
