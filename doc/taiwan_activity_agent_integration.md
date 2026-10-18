# 台灣活動探索｜omniAgent 自主 Agent 對接與 Life 發布邊界

> 日期：2026-10-18（Asia/Taipei） · 狀態：**APPROVED DESIGN / IMPLEMENTATION NOT VERIFIED**。
> 本文件僅是 Life 一側的工程交接及發布治理，**不直接修改 Drive 六份正式探索文件、不代表切換排程或完成部署**。
> 對應 Agent 設計：[omniAgent Taiwan Activity Autonomous Agent](https://github.com/tommylin15/omniAgent/blob/main/docs/taiwan-activity-autonomous-agent.md)。

## 1. 決策：AI Agent 在 omniAgent，不在 Life 再造

- **omniAgent**：`TaiwanActivityAgent` 的 LangGraph/Agent Worker、網站下探、主辦核證推理、來源診斷修復、文檔差異建議、重試與 checkpoint、受控 Gemini/MCP tools。Agent 不得直接讀寫 Life PostgreSQL，亦不得代替 Life 決定正式發布。
- **life_assistant**：Data + UI + API + Execution + Integration；活動欄位與版本 schema、來源/精選池/交接寫入驗證、Drive 對接、權限/稽核、現有 07:30 Sheet importer → PostgreSQL → Flutter。只新增**domain capability / adapter**，不建第二個 Agent runtime、LangGraph loop、全域 Tool Registry 或爬蟲工作流程。
- **Drive 內 `life_assistantGPT`**：唯一有效「台灣活動探索」README + 01～05、官方 GAS 快照、核准來源表、精選池與四衍生視圖、固定 30 欄交接資料、逐站執行表及唯一日誌。**本文不能覆蓋 Drive 正式規格**；有衝突先指出，再依核准修訂程序變更。
- 目前 ChatGPT Work/Chat 探索與 GCP AI Agent 是**替代架構切換**，不是預設兩個正式並行寫入者。只有 Shadow 為純讀/提出候選，不碰正式精選池或交接。

## 2. 保留的正式業務資料流

```text
[上游 GAS 文化部/觀光署快照]       [合法公開活動/主辦網站]
                \                 /
                 omniAgent Agent Worker (PROPOSED)
                         |
                 Life-scoped capability + validation gate
                         |
     Drive「台灣活動｜精選池」唯一原表 + 四衍生視圖
                         |
     Drive「台灣活動｜交接資料」固定 30 欄 outbox
             READY / ERROR / ACKED  (content_hash)
                         |
  Life 現有每日約 07:30 GAS -> Cloud Run import_curated_from_sheet
                         |
     PostgreSQL CuratedActivity -> Flutter「活動探索」
```

既有規則維持：
- `event_key` + `parent_event_key` 穩定；`record_type=main|offer|session`；`content_hash` 由完整規格化業務欄位 SHA256 計算；來源歸因只在精選原表專用欄，不准放入交接 business payload/hash。
- 交接表既有 ID `1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4` / `交接資料`；只可使用既有表頭 30 欄，不得新增 AI trace/model/scoring debug 欄。
- 有據來源、具名活動、穩定 ID 及可證活動日/開報節點可先提出提前預警候選；1/3/5 星是價值不是核證級別；未知費用、即時名額、開報時間和 `verified_at_tpe` 留空或標待核，不能造假填 0 / midnight / executed-at。
- Life `import_curated_from_sheet.py` 進行 Pydantic 驗證、DB upsert、**commit 後**同版本 readback 才 ACKED；單筆資料錯誤用 ERROR 並保留補跑，整體技術 status 與 data_status 分開。只有 ACKED 且可靠回執超過 30 天的列由**探索端**按既有規格清理，READY/ERROR/無版本證據不能刪。
- 保留 Firebase Hosting/Flutter Web、Cloud Run FastAPI、PostgreSQL 原來架構。UI 僅「活動探索」一個入口／限時視角／收藏，這次不修改 UI 或私人待辦／日曆。
- **2026-10-16 既有入庫鏈有真實批次技術 PASS 證據**：[Cloud Run/PostgreSQL 讀回 #38825509671](https://github.com/tommylin15/life_assistant/actions/runs/38825509671)；這僅支持當次 07:30 時段 Job 和部分資料 ACK，**不代表新 Agent 已接上或今天每日排程實跑 PASS**，來源 ERROR 繼續視為探索資料品質問題。

## 3. Life 要提供的最小能力（全為 Proposed API/MCP，尚未存在）

所有介面都先走合法 caller 服務身分驗證、來源白名單、schema/version/權限與 evidence gate。**不得將 Life DB connection、任意 Drive 全帳號權限、Google 使用者 OAuth token 或任意 URL 寫入權交給 omniAgent。**

| 建議 capability | Life 最終責任 | 回應/readback |
| --- | --- | --- |
| `activity.sources.list` | 讀唯一核准來源清單、作用中/停用與策略版本 | `registry_version`、來源 ID、准入/禁用 |
| `activity.snapshots.inspect` | 只讀 GAS 快照/manifest，驗 bytes/SHA/UID/EventID，含 stale | 原始證據/日期/狀態，不代替 GAS HTTP |
| `activity.public_page.fetch` | 依核准來源/合法公開頁提供最小讀頁能力；實際工具可由 omniAgent 受控調用 | URL、HTTP/讀取時間、來源/內容指紋、限制狀態 |
| `activity.source_repair.propose` | 保留舊 URL、失敗分類、官方 fallback 證據與計畫 | `proposal_id`, `requires_approval` |
| `activity.source_repair.apply` | 僅有權的操作性來源變更，CAS/回滾/讀回；違反禁用策略拒絕 | `before/after`, `recheck_status`, `receipt` |
| `activity.curated.propose` | schema/活動身份/原始證據檢查、不公開發布 | `accepted/rejected` 候選原因 |
| `activity.curated.publish` | 單一發布者鎖，upsert 唯一精選池及衍生視圖，寫後讀回 | `created/updated/unchanged` / keys |
| `activity.handoff.publish` | 只從合格精選池輸出舊 30 欄 READY，不偽造 Life ACK | `event_key/content_hash/status` |
| `activity.document.propose_patch` | 提供文件證據、變更差異，判斷是否屬正式政策 | `diff`, `risk_class` |
| `activity.document.apply_approved_patch` | 僅預先核准文件/操作備註更新，版本 fencing 與 readback | `file_id`, `revision`, `receipt` |

上表是介面方向，最終以新增測試中的 OpenAPI/MCP schema 為準；**目前 Life 無上述正式 Agent capabilities**。既有 `/api/v1/ai/text` 是受限的 Life → omniAgent 文字推論，不可假設已支援 Tool Calling 或自動瀏覽。盡可能重用現有服務身分與 `curated_handoff` validation，而不是為此新增平行活動資料庫。

建議通用請求含 `schema_version`、`run_id`、`action_id`、`source_key`、`expected_revision`、`evidence_refs`；同 `action_id` 重送要冪等，改版需新明確業務 `content_hash`，不可依執行時間換版。成功回應必須有可讀回的版本／寫入收據。Sheets 本身沒有條件原子交易，遇競態須 readback 判 PARTIAL 並在下一輪修復；不虛稱全域 ACID。

## 4. 自動修復與文件權限分級

- **Level 0 自動觀察**：來源讀取、快照/Manifest 二次驗證、異常類別、候選與健康紀錄、唯一 `YYYY-MM-DD.log` 依不同 run_id 追加；每輪先查同日完成項目避免重做。
- **Level 1 有證據的自動修復**：官方網站搬家、可追溯同主辦替代入口、來源表操作性網址修訂或已授權的非程式碼解析設定修正；程式碼層解析器修復只能產生提案交由 CI 與正常部署流程處理；必須原 URL/新 URL/主辦身份一致、原頁與備援 readback、修改前版本、diff/回滾及 audit。403/429 不代表可以繞過；來源失效不能充作零新增。
- **Level 2 文件維護**：若只是操作記錄或明確錯誤連結，可經既有授權工具自動讀寫/讀回；但正式探索 README、01～05 的**來源准入、A/B 覆蓋、1/3/5 星、去重、交接、安全與保存期限等政策**只由 Agent 建立 proposed_diff，經專案核准後才由文件發布器套用；不能在每日 06:00 直接讓 LLM 改規格並自我宣告 PASS。
- **Level 3 高風險禁止自動執行**：大規模刪資料、destructive migration、production IAM/Service Account 重大擴權、secret rotation、解除被停用來源政策、改寫 GitHub main 歷史或未核准的正式流量切換；另外需要使用者明確確認。

本專案**已有** Drive 正式 README/01～05 與來源表。2026-10-14 README/02 曾列出 EventGo、小藝為當日 A 來源，但近期討論又提及停用；**先輸出 SOURCE_POLICY_CONFLICT，核對現行正式來源表及批准決策，切勿默默採用任一版本**。Citytalk/TDX 已停用的規則維持。此設計不自行變動來源名單與 GAS 抓取責任。

## 5. 正式切換條件與分工

| ID | Life 工作 | 驗收出口 |
| --- | --- | --- |
| LA-TA01 | 對照 Drive 01～05、來源表與工作排程，釐清來源准入/停用衝突；定義 schema 與授權圖 | 契約 fixture、來源與權限 readback |
| LA-TA02 | 最小 Life adapter (sources, snapshots, curation, document proposal/approved apply)、來源/交接 fencing、audit | Pydantic/schema、錯誤分類、去重與負向權限 tests |
| LA-TA03 | Shadow Read-only 比較：同日證據、A/B 覆蓋、候選查全率、子優惠、星等/假資料、舊活動重複及成本 | 不觸碰正式池；結果差異與模型量測 |
| LA-TA04 | 正式唯一 writer gate、Drive 精選池/四視圖、交接 READY/ACK、Life PG/UI 端到端驗收 | CI + 同 SHA 候選/部署 + Sheets/PG readback + 復原演練 |

先完成 omniAgent 對應 `OA-TA01~05` 的 Worker 與上述 LA-TA 最小 interface；正式切換時確認**上游 GAS 快照、建議 06:00 Agent 以及現有 07:30 importer**各自可實際執行。不得只因 Scheduler 成功觸發、Gemini 回了一段文字或文件更新就標示端到端成功。若 Agent 趕不上匯入時窗，本輪明確延遲，不為達時間而輸出未核對資料；下一輪可按既有 READY/ERROR 補處理。

交付矩陣分開寫 `implementation/tests/CI/deployment/runtime/integration` 的 `PASS / FAIL / NOT VERIFIED`，只有全部必要 gate 有證據才 `DONE`，否則 `PARTIAL`。正式切換前不得同時讓 ChatGPT Work 與 GCP Agent 都寫同一精選池；已存在的 Work 排程狀態需要重新確認，**本次沒有啟用、停用或改動任何排程**。

## 6. 原有規格及文件優先序

- 正式 source of truth：GitHub `main` + runtime 對 Life 實作；Drive `life_assistantGPT` **最新核准 README + 01～05/原表**對探索政策；差異必須明列，未經核准不自行覆寫。
- 原有 [交接契約](curated_sheet_job_ingestion.md)、[活動 UX](curated_activity_user_features.md)、[探索入口](taiwan_free_events_discovery_plan.md) 繼續有效。這份文件是**將來 Agent 來源替換的擴充設計**，不是將目前的 ChatGPT 上游描述改寫為已啟用 Gemini。
- 本文件只記錄 LA-TA 交付分工；正式實作開始時須併入唯一 [Active TODO](todo.md)，不要平行養第二份完成率清單。任何正式資料、App 與文件改動須留原版與 rollback path。
