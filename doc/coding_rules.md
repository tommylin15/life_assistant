# 生活助理 App v0.1 — Coding Rules for Codex

## 1. 目的

提供 Codex / 開發者一致的實作約束。

## 2. 規則

- 不新增未在 spec / decisions 中定義的大功能
- 若規格衝突，以 decisions.md + spec.md + 對應專項 spec 為準
- UI 不直接操作 DB / API
- 新 schema 變更必須有 migration
- 所有 destructive operation 必須符合 security / sync / bridge 規格
- 所有 Google integration 透過 adapter
- 所有 Bridge JSON 必須 validator 驗證
- 所有可追蹤的重要動作寫 Activity Log
- 不將 secret 寫入 log
- 不為方便開發而清空使用者 DB

## 3. Definition of Done

一個 feature 完成至少包含：

- implementation
- basic tests
- error state
- empty state
- activity log（若適用）
- documentation update（若改變 contract）
