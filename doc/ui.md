# life_assistant — UI / UX Spec

最後更新：2026-09-22

## 1. UI 定位

life_assistant UI 是個人生活執行介面，不是通用 AI Chat 或 Agent Console。

Phase 1 主要交付為 Flutter Web / PWA，需同時適用手機與桌面瀏覽器。

視覺方向維持：

> **Warm Knowledge — Obsidian 的資料感 × 日系溫暖手帳**

## 2. Primary Navigation

建議主導覽：

1. Dashboard
2. Tasks
3. Calendar
4. Projects
5. More

More 可包含：

- Notes
- Habits
- Shopping
- Activity / Execution Log
- Integrations
- ChatGPT Bridge / MCP
- Settings

桌面版可使用 NavigationRail / sidebar；手機版使用 Bottom Navigation。

## 3. Dashboard

### 3.1 Summary

顯示：

- overdue count
- due today
- next calendar event
- waiting items

摘要第一階段以規則生成，不依賴 AI。

### 3.2 Sections

可顯示／隱藏：

- Tasks
- Calendar
- Reminders
- Waiting
- Shopping
- Habits
- Projects
- Important dates

### 3.3 Quick Actions

- Create task
- Create event
- Create note
- Add shopping item
- Create project

## 4. Tasks

列表支援：

- status
- priority
- due/reminder
- project
- tag
- checklist progress

編輯頁需適用 phone / desktop responsive layout。

所有 mutation 透過 Backend API，不在 UI 直接操作 DB。

## 5. Calendar

支援：

- agenda / simplified week / month
- create/edit/delete
- conflict/error state
- source / sync status

Google integration failure 要顯示可理解的錯誤，不將遠端失敗偽裝成成功。

## 6. Projects

專案頁聚合：

- summary
- open tasks
- calendar items
- notes
- Gmail refs
- attachments
- recent activity

## 7. Notes

- Markdown edit / preview
- search
- tags
- project relation
- links
- attachments

Web desktop 可有較寬 editor；手機保持單欄，不強制 split view。

既有 Local Markdown Workspace / Folder Sync UI 可保留為 legacy / optional capability，但新的中央模型以 Backend / PostgreSQL 為準。

## 8. Habits / Shopping

Habits：週期與完成操作優先，避免過度統計化。

Shopping：快速新增與勾選優先。

## 9. Activity / Execution Log

至少呈現：

- time
- source/actor
- action
- status
- affected entity

狀態需區分：

- success
- partial success
- failed
- pending / awaiting confirmation（適用時）

## 10. Integrations / Connections

集中顯示：

- Google account
- Gmail
- Calendar
- Drive
- ChatGPT Bridge
- MCP / Integration API status

每個 integration 顯示：

- Connected / Not connected / Error
- permission summary
- last sync / last check（適用時）
- reconnect / disconnect / test action

## 11. ChatGPT Bridge / MCP UI

此頁屬於 life_assistant，需保留。

### 11.1 Bridge Status

顯示：

- Backend Bridge status
- schema / contract version
- Drive Bridge legacy/fallback status
- last proposed action import / request
- last execution result

### 11.2 Proposed Action Review

每個 action 顯示：

- action type
- reason（若有）
- source
- affected data
- risk / confirmation requirement
- proposed payload summary

操作：

- Accept
- Edit then accept（若 action type 支援）
- Reject

破壞性 action 不得預設選取。

### 11.3 MCP Capability Status

可顯示 life_assistant 自己的 Capability Catalog：

- capability name
- version
- enabled/disabled
- permission requirement
- risk level

此頁**不顯示 omniAgent 的 Global Tool Registry / Workflow Registry**。

## 12. Background Job UI

只顯示與 life_assistant 自身有關的 job：

- sync
- backup/export
- migration
- notifications
- maintenance

不要建立 LangGraph / Agent Worker 管理 console。

## 13. Loading / Empty / Error / Data

所有主要頁面需要一致四態：

- loading
- empty
- error
- data

mutation 另需：

- submitting
- success
- partial success
- failed

## 14. Responsive Rules

### Phone
- 單欄
- Bottom Navigation
- dialog 視內容使用 full-screen / bottom sheet

### Tablet
- 可採 NavigationRail
- master/detail 視功能需要

### Desktop
- sidebar / NavigationRail
- 內容最大寬度控制
- 可同時顯示列表與 detail，但不強制所有頁面 split view

## 15. Settings

至少包含：

- Google account
- Gmail / Calendar / Drive
- ChatGPT Bridge / MCP
- notification
- theme
- homepage sections / quick actions
- backup / export
- security / session
- About / Version

原生 App 專用 App Lock / biometric 等設定可保留為後續 platform-specific UI，不作為 Web Phase 1 核心完成條件。

## 16. Accessibility

- touch target ≥ 44×44
- keyboard navigation on Web
- semantic labels
- focus states
- system text scaling
- 不只用顏色表示狀態
- error message 可被 screen reader 理解

## 17. 不屬於 life_assistant UI

以下 UI 不在本專案實作：

- LangGraph graph editor
- Global Tool Registry 管理頁
- Workflow Registry editor
- Agent Runtime console
- Agent Worker monitor
- multi-agent orchestration dashboard

這些屬於 omniAgent。

## 18. 視覺規範

顏色、字級、spacing、radius、card、button、motion 等視覺規範以 `design_system.md` 為準。
