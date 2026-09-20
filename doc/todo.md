# 生活助理 App v0.1 — TODO

> 進度快照與待驗證項目見 [`progress.md`](progress.md)。此清單的 `[x]` 只代表已有實作；Release Gate 必須實測後才能勾選。

## P0 — 開工前

- [x] 建立 Flutter repository
- [x] 決定 state management
- [x] 決定 SQLite 套件
- [x] 決定 routing
- [x] 建立 Theme Token
- [x] 建立 domain folder structure
- [x] 建立 migration strategy

## P0 — 第一個可用版本

- [x] SQLite schema
- [x] Item CRUD
- [x] Project CRUD
- [x] Dashboard
- [x] Quick input
- [x] Local notification
- [x] Activity log
- [x] Light / Dark / Warm theme
- [x] Search
- [x] Basic backup

## P0 — Google

- [x] Google Sign-In adapter（待 OAuth 設定／實機驗收）
- [x] Calendar read
- [x] Calendar create
- [x] Calendar update
- [x] Calendar delete
- [x] Gmail metadata
- [x] Gmail → task
- [x] Gmail → calendar
- [x] Error handling（功能頁錯誤與本機快取 fallback）

## P1 — 生活模組

- [x] Notes
- [x] FTS5
- [x] Habits
- [x] Shopping
- [x] Templates（Task／Project 另存入口待補）
- [x] Attachments
- [x] Camera scan
- [x] Voice input

## P1 — ChatGPT Bridge

- [x] Bridge JSON schema validator
- [x] request_id + action_id idempotency
- [x] action_results export
- [x] Bridge schema version compatibility（v1 major）

- [x] Share Bridge
- [x] Drive Bridge folder setup
- [x] Manifest
- [x] App state export
- [x] Proposed actions import
- [x] Schema validation
- [x] Review UI
- [x] Accept / reject
- [x] Bridge onboarding
- [x] ChatGPT connection tutorial
- [x] Bridge ID verification

## P1 — Security

- [x] Biometric
- [x] PIN
- [x] Secure token storage（平台 Google Sign-In / secure storage）
- [x] Sensitive log filtering

## P2 — Polish

- [x] Daily summary
- [x] Daily review
- [x] Custom homepage sections
- [x] Custom quick actions
- [x] Month view（簡化範圍）
- [x] Week view（簡化範圍）
- [ ] Empty states
- [ ] Accessibility
- [x] Export JSON
- [x] Export CSV
- [x] Restore flow

## Release Gate

- [ ] 核心功能離線可用
- [ ] Google 服務失敗不破壞本機資料
- [ ] Calendar 雙向操作穩定
- [ ] Gmail 轉待辦 / 行程成功
- [ ] Drive Bridge 有確認機制
- [ ] 備份還原成功
- [ ] OAuth token 不進 SQLite / export
- [ ] App Lock 正常
- [ ] Android release build
- [ ] iOS release build
- [x] 建立 project_structure.md 對應的實際 folder skeleton
- [x] 建立 DB migration runner
- [x] 建立統一 error model
- [ ] 建立 permissions status service
- [ ] 建立 test baseline / CI（測試案例已建立；CI 尚未建立、測試尚未執行）
