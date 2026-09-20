# 生活助理 App v0.1 — TODO

## P0 — 開工前

- [ ] 建立 Flutter repository
- [ ] 決定 state management
- [ ] 決定 SQLite 套件
- [ ] 決定 routing
- [ ] 建立 Theme Token
- [ ] 建立 domain folder structure
- [ ] 建立 migration strategy

## P0 — 第一個可用版本

- [ ] SQLite schema
- [ ] Item CRUD
- [ ] Project CRUD
- [ ] Dashboard
- [ ] Quick input
- [ ] Local notification
- [ ] Activity log
- [ ] Light / Dark / Warm theme
- [ ] Search
- [ ] Basic backup

## P0 — Google

- [ ] Google Sign-In
- [ ] Calendar read
- [ ] Calendar create
- [ ] Calendar update
- [ ] Calendar delete
- [ ] Gmail metadata
- [ ] Gmail → task
- [ ] Gmail → calendar
- [ ] Error handling

## P1 — 生活模組

- [ ] Notes
- [ ] FTS5
- [ ] Habits
- [ ] Shopping
- [ ] Templates
- [ ] Attachments
- [ ] Camera scan
- [ ] Voice input

## P1 — ChatGPT Bridge

- [ ] Bridge JSON schema validator
- [ ] request_id + action_id idempotency
- [ ] action_results export
- [ ] Bridge schema version compatibility

- [ ] Share Bridge
- [ ] Drive Bridge folder setup
- [ ] Manifest
- [ ] App state export
- [ ] Proposed actions import
- [ ] Schema validation
- [ ] Review UI
- [ ] Accept / reject
- [ ] Bridge onboarding
- [ ] ChatGPT connection tutorial
- [ ] Bridge ID verification

## P1 — Security

- [ ] Biometric
- [ ] PIN
- [ ] Secure token storage
- [ ] Sensitive log filtering

## P2 — Polish

- [ ] Daily summary
- [ ] Daily review
- [ ] Custom homepage sections
- [ ] Custom quick actions
- [ ] Month view
- [ ] Week view
- [ ] Empty states
- [ ] Accessibility
- [ ] Export JSON
- [ ] Export CSV
- [ ] Restore flow

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
- [ ] 建立 project_structure.md 對應的實際 folder skeleton
- [ ] 建立 DB migration runner
- [ ] 建立統一 error model
- [ ] 建立 permissions status service
- [ ] 建立 test baseline / CI
