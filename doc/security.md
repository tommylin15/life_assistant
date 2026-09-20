# 生活助理 App v0.1 — Security & Privacy

## 1. 原則

- Local-first
- 最小權限
- 使用者可理解
- 敏感資料不明文保存
- 外部整合失敗不可破壞本機主資料

## 2. App Lock

可選擇啟用：

- 生物辨識
- PIN fallback

PIN：

- 不得以明文存 SQLite
- 使用安全儲存
- 避免寫入 log

## 3. Token

Google OAuth token：

- 使用平台安全儲存
- 不寫入一般 log
- 不匯出到 CSV / JSON
- 不放入 Drive Bridge

## 4. SQLite

- App 私有目錄
- 不允許其他 App 直接存取
- 若未來支援 DB encryption，可列 v0.2

## 5. 附件

- 存 App 私有目錄
- 匯出時需使用者明確操作
- 不自動上傳 Drive

## 6. Gmail

只保存必要 metadata。

不建議長期保存：

- 完整郵件正文
- 敏感附件
- OAuth token

## 7. Google Drive Bridge

Bridge 只允許 App 指定資料夾。

原則：

- 不把整個 Drive 當 App 資料來源
- Bridge 檔案不得包含 OAuth token
- proposed actions 匯入前必須驗證
- Schema 不符合則拒絕匯入

## 8. 刪除與破壞性操作

以下應要求確認：

- Calendar 刪除
- Project 刪除
- 批次刪除
- 還原備份覆蓋目前資料
- 匯入 ChatGPT proposed actions 中的 delete action
