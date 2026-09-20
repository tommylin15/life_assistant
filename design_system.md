# 生活助理 App v0.1 — Design System

## 1. 設計定位

預設主風格：

> **Warm Knowledge — Obsidian 的資料感 × 日系溫暖手帳**

目的不是仿製 Obsidian，而是融合：

- Obsidian：文件優先、資訊層級清楚、長時間閱讀舒適
- 日系手帳：溫暖、生活感、低壓、柔和留白
- Material：一致的元件行為、可存取性與跨平台穩定性

---

## 2. Design Principles

### 2.1 Calm First

畫面先讓人知道「現在要注意什麼」，不要讓資訊本身製造焦慮。

### 2.2 Content First

文件、待辦、行程是主角；裝飾不能搶走注意力。

### 2.3 Local Clarity

重要狀態在原地顯示，例如：

- 到期
- 同步
- 優先度
- 等待中
- 衝突

不要要求使用者切到另一頁才知道。

### 2.4 Progressive Detail

首頁簡潔，細節逐層展開。

### 2.5 Theme-independent Components

所有元件只使用 Token，不直接寫死顏色。

---

## 3. Color Tokens

以下為初始建議值，可在實作時做對比度微調。

### 3.1 Warm Knowledge / Light

| Token | Hex | 用途 |
|---|---|---|
| `surface.canvas` | `#F7F3EA` | App 主背景 |
| `surface.paper` | `#FFFCF6` | 文件 / 編輯器背景 |
| `surface.card` | `#FFF9F0` | Dashboard 卡片 |
| `surface.elevated` | `#FFFFFF` | Dialog / Sheet |
| `surface.muted` | `#EFE9DE` | 次要區塊 |
| `text.primary` | `#322F2A` | 主要文字 |
| `text.secondary` | `#6F695F` | 次要文字 |
| `text.tertiary` | `#9A9287` | 輔助文字 |
| `border.soft` | `#E4DDD1` | 柔和分隔線 |
| `accent.sage` | `#7F9278` | 主 Accent |
| `accent.sageSoft` | `#DDE6D8` | Accent 背景 |
| `accent.apricot` | `#D99A67` | 行動 / 提醒 |
| `accent.apricotSoft` | `#F4DFCE` | 行動背景 |
| `accent.blueMuted` | `#7B92A8` | Calendar / 資訊 |
| `status.success` | `#6F8D68` | 成功 |
| `status.warning` | `#B98445` | 警告 |
| `status.danger` | `#B7655F` | 錯誤 / 逾期 |
| `status.info` | `#728CA4` | 資訊 |

### 3.2 Dark

| Token | Hex |
|---|---|
| `surface.canvas` | `#181A18` |
| `surface.paper` | `#1F211F` |
| `surface.card` | `#252824` |
| `surface.elevated` | `#2B2E2A` |
| `surface.muted` | `#30332F` |
| `text.primary` | `#F1EEE7` |
| `text.secondary` | `#C4BEB4` |
| `text.tertiary` | `#918B82` |
| `border.soft` | `#3B3E39` |
| `accent.sage` | `#A4B49C` |
| `accent.apricot` | `#E3AE80` |

狀態色在深色模式需另外調整對比度。

---

## 4. Typography

優先使用系統字體，避免第一版增加字型資產管理負擔。

### 4.1 Type Scale

| Style | Size | Weight | 用途 |
|---|---:|---:|---|
| `display` | 32 | 600 | 特殊首頁標題 |
| `h1` | 28 | 600 | 頁面主標題 |
| `h2` | 22 | 600 | 區塊標題 |
| `h3` | 18 | 600 | 卡片 / 文件子標 |
| `bodyLarge` | 17 | 400 | Markdown 主要閱讀 |
| `body` | 15 | 400 | 一般 UI |
| `bodySmall` | 13 | 400 | 次要說明 |
| `label` | 13 | 500 | Chip / Button |
| `caption` | 12 | 400 | 時間 / Metadata |

Markdown 正文建議行高：

- `bodyLarge`: 1.55–1.7
- 一般 UI: 1.35–1.5

---

## 5. Spacing

以 4pt grid 為基礎。

| Token | Value |
|---|---:|
| `space.xs` | 4 |
| `space.sm` | 8 |
| `space.md` | 12 |
| `space.lg` | 16 |
| `space.xl` | 24 |
| `space.2xl` | 32 |
| `space.3xl` | 48 |

頁面左右安全留白：

- Phone：16–20
- Tablet：24–32

---

## 6. Radius

| Token | Value |
|---|---:|
| `radius.sm` | 8 |
| `radius.md` | 12 |
| `radius.lg` | 16 |
| `radius.xl` | 20 |
| `radius.pill` | 999 |

建議：

- 小按鈕 / Chip：`sm` / `pill`
- 一般 Card：`lg`
- Hero / Summary Card：`xl`

---

## 7. Elevation / Shadow

整體採低陰影。

### Level 0

- 文件區
- List
- Flat Card

### Level 1

- Dashboard Card
- Floating shortcut

### Level 2

- Bottom Sheet
- Modal

避免多層重陰影。

---

## 8. Cards

### 8.1 Summary Card

首頁智慧摘要。

- `surface.card`
- Radius 20
- Padding 16–20
- 可使用非常淡的 Accent background
- 最多一個主動作

### 8.2 Section Card

- Radius 16
- Padding 12–16
- 支援標題 + 次要 Metadata
- 不要每張卡都加 Border + Shadow 雙重裝飾

### 8.3 Task Card

最少顯示：

- Title
- Due / reminder
- Priority
- Project / tag（必要時）

完成狀態應降低視覺權重，不直接消失。

---

## 9. Buttons

### Primary

- Accent sage 或主題主要 Accent
- 重要確認行動

### Secondary

- Soft surface
- 次要行動

### Destructive

- Danger 色
- 只用於刪除 / 明確破壞性操作

### Icon Button

- 最小 touch target 44×44
- Icon 不小於 20

---

## 10. Tags / Chips

- 小面積
- 低飽和背景
- 文字顏色需具可讀性
- 不依賴不同鮮豔顏色區分類型

預設標籤：

- 家庭
- 帳單
- 居家
- 健康
- 採買
- 行政

---

## 11. Markdown Workspace

### 11.1 Workspace Browser

布局：

- 上方：目前資料夾路徑 + 搜尋 + 同步
- 中間：資料夾 / Markdown 檔案
- 每筆顯示：
  - icon
  - filename
  - modified time
  - sync status

資料夾與檔案應有明確差異，但不採傳統工程 IDE 樣式。

### 11.2 Markdown Editor

頂部：

- Back
- File title
- Save state
- Sync state
- More

正文：

- `surface.paper`
- 長時間閱讀優先
- 左右 padding 18–22
- Body 17
- Line height 1.6

底部或鍵盤上方工具列：

- H1/H2
- Bold
- Italic
- Bullet
- Numbered
- Checklist
- Quote
- Link
- Image

不要塞入過多 Markdown 語法。

### 11.3 Preview

Headings：

- H1 28 / semibold
- H2 22 / semibold
- H3 18 / semibold

Blockquote：

- 左側 3px sage line
- muted surface
- 12–16 padding

Checklist：

- 使用平台一致的 check affordance
- completed text 降低 opacity

Code block：

- 獨立 muted surface
- Radius 8
- 等寬字體

Link：

- 使用 `accent.blueMuted`
- 不使用高飽和純藍

### 11.4 Edit / Preview Interaction

v0.1 建議：

- 預設 Edit
- Toolbar 可切換 Preview
- 不做手機 split view
- Tablet 未來可考慮左右分割

---

## 12. Sync UI

### 12.1 Status

支援：

- Synced
- Local changes
- Remote changes
- Syncing
- Conflict
- Error

每個狀態需：

- Icon
- 短文字
- 必要時時間

### 12.2 Manual Sync

Workspace 與 Settings 都要有「立即同步」。

同步按鈕：

- 同步中不可重複觸發
- 顯示 progress
- 完成後顯示結果摘要

### 12.3 Conflict

衝突頁：

- File name
- Local modified time
- Drive modified time
- Diff（文字檔可用）
- Keep Local
- Keep Drive
- Keep Both

破壞性選項不得設為預設。

---

## 13. Navigation

Bottom Navigation：

1. 首頁
2. 待辦
3. 日曆
4. 專案
5. 更多

Markdown / Notes 可從「更多」進入，也可在首頁設快捷。

若未來 Markdown Workspace 成為高頻功能，可升級為主 Navigation；v0.1 先保留彈性。

---

## 14. Motion

動畫原則：

- 150–250ms
- 只用於狀態理解
- 避免娛樂性過強動畫

可用：

- Card expand
- Checkbox completion
- Sync indicator
- Bottom sheet

---

## 15. Accessibility

- Touch target ≥ 44×44
- 支援 Dynamic Type / 系統字體縮放
- 不只靠顏色表示狀態
- Light / Dark 均需符合可讀性
- 長文字不可被固定高度截斷
- Dialog / Sheet 支援螢幕閱讀器語意

---

## 16. Template Strategy

v0.1 不直接套第三方整套 UI Template。

允許參考：

- Markdown editor interaction
- File browser layout
- Dashboard card composition
- Theme token architecture
- Navigation pattern

但最終 UI 必須由本 Design System 控制。

這能避免：

- License / 套件綁定
- 視覺不一致
- 模板更新後破版
- 未來多 Theme 困難
