# 生活助理 App v0.1 — Integrations

## 1. Google Sign-In

用途：

- 身分識別
- Gmail 授權
- Calendar 授權
- Drive Bridge 授權

要求：

- 採最小權限原則
- scope 分項請求
- 清楚顯示使用目的
- 支援重新授權
- 支援斷線 / revoke 後的降級模式

---

## 2. Gmail

### v0.1

- 取得郵件必要 metadata
- 顯示摘要
- 一鍵轉待辦
- 一鍵轉行程
- 掛到專案

### 不做

- App 內寄信
- App 內回信
- 自建 Mail Client
- Gmail 全文長期鏡像

---

## 3. Google Calendar

### v0.1

- 讀取
- 建立
- 修改
- 刪除
- 本機快取
- 手動 / 啟動時同步
- Gmail / Item 轉行程

### 衝突策略

- 遠端修改與本機修改同時存在時，應提示使用者確認
- 不應靜默覆蓋
- 刪除動作需確認

---

## 4. Google Drive Bridge

### 4.1 目的

讓 App 與 ChatGPT 在沒有 OpenAI API 的前提下交換結構化資料。

### 4.2 預設路徑

```text
生活助理/
└── ChatGPT_Bridge/
    ├── README.md
    ├── bridge_manifest.json
    ├── current_state.json
    ├── inbox.json
    ├── projects.json
    ├── pending_actions.json
    └── history/
```

### 4.3 bridge_manifest.json

至少包含：

- bridge_id
- schema_version
- app_version
- exported_at

### 4.4 App → Drive

輸出：

- 今日狀態
- 近期待辦
- 近期行程
- 等待中事項
- 進行中專案
- 使用者指定上下文

### 4.5 ChatGPT → Drive

寫入：

- proposed_actions
- summaries
- recommendations

### 4.6 App 匯入

所有 proposed actions 必須：

1. schema 驗證
2. 顯示預覽
3. 使用者確認
4. 寫入 SQLite
5. 寫入 Activity Log

不得直接無條件執行。

---

## 5. ChatGPT Onboarding

App 需提供「ChatGPT Bridge 設定」頁。

狀態：

- App Google Drive：Connected / Not connected
- Bridge Folder：Ready / Missing
- ChatGPT：Not verified / Verified

### 測試流程

App 產生測試指令，要求 ChatGPT：

1. 讀取指定 Google Drive Bridge manifest
2. 回報 bridge_id
3. 回報 schema_version

使用者將回覆填回 App 或手動確認。

### ChatGPT 未連 Google Drive 時

顯示教學：

1. 打開 ChatGPT
2. 進入 Settings
3. 進入 Plugins / Apps / Connectors
4. 連接 Google Drive
5. 使用可存取 Bridge 資料夾的 Google 帳號
6. 回到 ChatGPT 對話
7. 貼上 App 產生的測試指令
8. 驗證 Bridge ID

App 內教學文字需避免依賴固定 UI 名稱，因 ChatGPT UI 可能變動；可保留可更新教學版本。

---

## 6. Share Bridge

提供：

- 複製文字
- 複製 JSON
- 系統分享

用途：

- Google Drive Bridge 未設定時
- 緊急 fallback
- 使用者只想分享單一事項時

---

## 7. Local Folder ↔ Google Drive Folder Sync

v0.1 支援手動觸發的雙向 Folder Sync。

核心規則：

- 首次同步以 Google Drive 為主
- Local 必須是乾淨空資料夾
- 首次同步完成後才啟用雙向同步
- 刪除正常雙向同步
- 雙方同時修改時進入 Conflict，不靜默覆蓋
- SQLite 與 `ChatGPT_Bridge/` 排除一般 Folder Sync

完整規格見 `sync_spec.md`。

---

## 8. ChatGPT Bridge JSON Contract

ChatGPT ↔ Drive ↔ App 的正式 JSON schema、action registry、版本相容與驗證規則，見：

`bridge_schema.md`

實作時不得以 README prose 取代 schema 驗證。
