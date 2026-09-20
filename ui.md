# 生活助理 App v0.1 — UI / UX Spec

## 1. 視覺方向

### 預設主風格

**Obsidian 的資料感 × 日系溫暖手帳**

核心原則：

- 首頁像生活手帳：溫暖、低壓、留白充足。
- 文件與 Markdown Workspace 像 Obsidian：資料密度較高、層級清楚、適合長時間閱讀與編輯。
- 不直接仿製 Obsidian UI，而是吸收其「文件優先、資料結構清楚」的設計語言。
- Dashboard 與生活模組使用柔和卡片；文件頁減少卡片感，讓內容成為主角。

關鍵字：

- 溫暖
- 日常
- 低壓
- 手帳感
- 文件感
- 清楚的資訊層級
- 現代
- 不像企業 Dashboard

避免：

- 過多紅色警示
- 過密資料表
- 過度陰影
- 高飽和配色
- 大量 KPI 圖表

## 2. Theme

### Template A — Warm Knowledge / 預設

預設主題。融合 Obsidian 的資料感與日系溫暖手帳。

- 奶油紙張背景
- 暖灰主要文字
- 鼠尾草綠為主要 Accent
- 杏橘作為提醒與行動 Accent
- 卡片大圓角、低陰影
- Markdown / 文件頁使用較平坦版面與細分隔線
- 強調長時間閱讀舒適度

### Template B — 極簡清爽

- 白 / 淺灰
- 冷灰字
- 藍綠點綴
- 高留白
- 降低裝飾性

### Template C — 深色夜間

- 深灰黑背景
- 柔和高對比
- 降低純白亮度
- 保留鼠尾草綠 / 杏橘語意色

所有模板使用同一套 Theme Token 與元件，不為不同模板重做頁面。

完整 Token、字體、間距、圓角、卡片與 Markdown 規格見 `design_system.md`。

## 3. Bottom Navigation

建議 5 個主入口：

1. 首頁
2. 待辦
3. 日曆
4. 專案
5. 更多

「更多」包含：

- 筆記
- 習慣
- 採買
- Log
- 設定

## 4. 首頁

由上到下：

1. 日期 / 問候
2. 智慧摘要卡
3. 可自訂快捷
4. 待辦區塊
5. 行程區塊
6. 提醒區塊
7. 等待中區塊
8. 可選延伸區塊

每區只顯示前幾筆，提供「查看全部」。

## 5. 待辦頁

支援：

- 今日
- 即將到期
- 等待中
- 全部
- 已完成

卡片顯示：

- 標題
- due
- priority
- project
- checklist progress
- tags

## 6. Item Detail

區塊：

- 標題
- 狀態
- 優先度
- 日期 / 提醒
- Checklist
- 備註
- 專案
- 標籤
- 附件
- 來源
- Activity

## 7. Calendar

提供：

- 月視圖
- 週視圖
- 日期詳情列表

不做複雜拖曳。

## 8. Project Home

- 專案摘要
- 待辦
- 行程
- 筆記
- 附件
- 最近活動

## 9. Notes / Markdown Workspace

### 9.1 Workspace

App 可指定手機端資料夾作為 Markdown Workspace。

支援：

- 資料夾瀏覽
- Markdown 檔案列表
- 新增 / 開啟 / 編輯 / 重新命名 / 刪除 `.md`
- 搜尋
- 標籤
- 相關筆記
- 轉待辦 / 行程
- 附件連結

### 9.2 Markdown Editor

提供：

- 編輯模式
- 預覽模式
- 可選分頁切換 Edit / Preview
- Markdown 常用工具列
- 自動儲存到本機
- 顯示「尚未同步」狀態

支援基本語法：

- Heading
- Bold / Italic
- Bullet / Numbered List
- Checklist
- Quote
- Code / Inline Code
- Link
- Image reference
- Horizontal rule

第一版不做：

- Canvas
- Graph View
- 複雜 Plugin System
- Obsidian 完整語法相容保證

### 9.3 文件視覺

- 文件背景接近紙張感，但不使用擬真材質
- 正文區減少 Card 邊框與陰影
- 標題、列表、引用需有明確層級
- 程式碼區使用獨立 Surface
- 行寬以手機長時間閱讀舒適為優先

## 10. Settings

包含：

- Google 帳號
- Gmail
- Calendar
- Drive Bridge
- Markdown Workspace
- 本機資料夾 ↔ Google Drive 同步
- 通知
- App Lock
- Theme
- 首頁區塊
- 快捷設定
- 備份 / 匯出
- About / Version

### 10.1 Folder Sync 設定

可指定：

- 手機端來源資料夾
- Google Drive 目標資料夾
- 同步檔案類型
- 是否包含子資料夾

提供：

- 立即同步
- 最後同步時間
- 待同步檔案數
- 同步結果
- 衝突列表

v0.1 採**使用者手動觸發同步**，不依賴背景常駐同步。

### 10.2 同步衝突

若本機與 Drive 同一檔案都在上次同步後被修改，不可靜默覆蓋。

顯示：

- 本機修改時間
- Drive 修改時間
- 查看差異（文字檔可支援）
- 保留本機
- 保留 Drive
- 兩份都保留

第一版不要求自動 merge。

## 11. 空狀態

使用溫暖文案，不做錯誤感。

例如：

- 今天目前沒有待處理事項
- 這個專案還沒有待辦
- 尚未建立任何筆記

## 12. 錯誤狀態

Google 服務失敗：

- 清楚顯示哪個服務失敗
- 本機資料照常可用
- 提供重試
- 不阻塞整個 App

## 13. Accessibility

- 字體支援系統縮放
- 點擊區域足夠
- 不只靠顏色表達狀態
- 深色模式具足夠對比


## 14. 同步狀態 UI

所有 Workspace 文件應能呈現簡單同步狀態：

- 已同步
- 本機有變更
- Drive 有更新
- 同步中
- 衝突
- 同步失敗

狀態需搭配 icon / 文字，不只靠顏色。

Toolbar 或 Workspace 首頁提供明確的 **「立即同步」** 操作。

同步不應阻塞本機編輯。

## 15. UI 參考策略

網路模板僅作為：

- Layout 參考
- Markdown editor 互動參考
- Navigation 參考
- Design token / Component system 參考

不直接整套套用第三方模板。

原則：

1. 先建立自己的 `design_system.md`
2. 共用 Flutter 元件
3. Theme 可替換
4. 避免被單一模板綁死
