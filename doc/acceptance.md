# 生活助理 App v0.1 — Acceptance Criteria

## 核心

- [ ] App 可離線啟動
- [ ] SQLite 可建立並持久保存資料
- [ ] 使用者可新增 / 修改 / 完成待辦
- [ ] 待辦可設定日期、優先度、提醒、標籤、專案
- [ ] Checklist 可使用
- [ ] 首頁能顯示今日摘要

## Calendar

- [ ] Google 登入
- [ ] 可讀取 Calendar
- [ ] 可新增
- [ ] 可修改
- [ ] 可刪除
- [ ] Calendar 失敗不影響本機功能

## Gmail

- [ ] 可讀必要 metadata
- [ ] 可轉待辦
- [ ] 可轉行程
- [ ] 可掛到專案

## 專案 / 筆記 / 習慣 / 採買

- [ ] 專案可管理相關資料
- [ ] 筆記可全文搜尋
- [ ] 習慣可重複與記錄完成
- [ ] 採買可快速新增與勾選

## 附件

- [ ] 圖片
- [ ] PDF
- [ ] 一般文件
- [ ] 相機拍照 / 掃描存檔

## 通知

- [ ] 本機通知
- [ ] 每日摘要
- [ ] 每日收尾

## ChatGPT Bridge

- [ ] Share Bridge 可用
- [ ] Drive Bridge 可建立
- [ ] Bridge ID 可驗證
- [ ] ChatGPT 未連 Drive 時有教學
- [ ] proposed actions 必須確認後才寫入 SQLite

## 安全

- [ ] 生物辨識
- [ ] PIN fallback
- [ ] token 不存 SQLite
- [ ] 敏感資訊不進一般 log

## 匯出

- [ ] SQLite 備份
- [ ] JSON
- [ ] CSV
- [ ] 可還原備份
