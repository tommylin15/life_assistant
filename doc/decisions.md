# life_assistant — Current Confirmed Decisions (2026-10-10)

本文件只保留**現行**決策；歷史 Queue、文化部/TDX、來源掃描、舊 CI/CD、未採納的活動流程和當時的狀態完整留在 [歷史決策快照](archive/decisions_through_2026-10-10.md)。目前 code/runtime 優先於文件聲稱的完成度，治理優先於此文件見 [PROJECT_RULES](PROJECT_RULES.md)。

## 平台與責任

- Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL；Flutter Web 是主要交付面，SQLite 是既有資料和遷移來源；不得破壞性清空。
- Life 負責 Data + UI + API + Execution + Integration、自己的 ChatGPT Bridge／MCP、權限與 audit；通用 Agent reasoning/orchestration 屬 omniAgent。詳見 [project boundary](project_boundary.md)。
- Google 整合採帳號獨立授權、最小權限、可驗證寫入與失敗處理。個人隱私資料不得在全站管理員功能中暴露。
- CI/CD 使用 V3 GitHub Actions → public GHCR digest → Cloud Run candidate → gated Firebase Hosting；詳見 [唯一 V3 policy](ci_cd_ghcr_release_policy.md)。Production release 需獨立驗收，預設保留最近十個受保護條件約束的 revisions。

## 精選池與使用者功能

- 最新活動入口：ChatGPT 探索／核證 → Drive 精選池 → **[獨立交接資料 Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit)** → Life 每日 GCP Job（永久 event_key/content_hash 去重、PostgreSQL upsert、版本一致 ACKED/ERROR）→ Flutter。交接資料僅滾動保留 ACK 後30天，不以 Excel 永久保留歷史。原 direct API 僅作相容，Life 來源 crawler／舊 Queue/lease/claim／第二次 AI 持續取消。新 Job 和 ACK 實作 **NOT VERIFIED**。詳見 [現行流程](taiwan_free_events_discovery_plan.md) 和 [交接契約](curated_sheet_job_ingestion.md)。
- **兩個使用者功能入口**：「限時機會」（報名／限量／預警／待辦）與「活動探索」（活動日期標記／收藏／旅遊候選）；同一活動可同時屬於兩者，沒有兩份資料庫。
- 使用者自行選擇個人追蹤、提醒、待辦、行事曆與未來行程；價值星等、急迫度、是否要報名、旅遊用途相互獨立。所有行事曆資訊標記、報名時間提醒、確定行程有不同語意。唯一詳細規格：[精選池使用者功能](curated_activity_user_features.md)。
- 此產品決策為 **APPROVED DESIGN**；當前 UI/API 只有單一精選池 baseline，兩入口與個人整合不可標示實作或部署完成。

## 管理、個人化與 AI

- 管理員僅管理共用精選資料、功能 rollout、Life 內部 Drive AI Provider policy；ChatGPT 探索和平台 AI Provider 是不同系統。
- 使用者依自己帳號設定手機底部/桌面側邊導覽排序、首頁卡片、Google consent；後台不可代替個人同意。參照 [CURRENT_PRODUCT_ARCHITECTURE](CURRENT_PRODUCT_ARCHITECTURE.md) 和 [AI policy](ai_provider_policy.md)。
- 未來旅遊行程編排只保留可擴充介面；未核准完整旅遊系統、未授權自動報名或付款。

## 追蹤與現況

交付順序看 [phase1_delivery_order](phase1_delivery_order.md)、[TODO](todo.md)；實作與驗收看 [CURRENT_STATE](CURRENT_STATE.md)。過時決策不因 archive 保留就恢復效力。
