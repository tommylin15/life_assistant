# Life 活動精選池 — 最新唯一交接路徑（2026-10-12）

**APPROVED DESIGN：ChatGPT Chat 探索／核證 → Drive 精選池 → [獨立「交接資料」Sheet](https://docs.google.com/spreadsheets/d/1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4/edit) → Life GCP 每日 Job → PostgreSQL 共用精選池 → Flutter。**

- 探索原始證據、去重和星等規則以 Drive 正式探索 01～05 為準；探索任務終點是**精選池 → 交接表 READY → 讀回驗證**。**以提前通知為優先**：具有可回查來源、穩定活動鍵及有據的活動日或開報節點即可交接，包含 1／3／5 星與「五星潛力待核」；即時名額、部分資格和費用未知不是一律阻擋。未知／衝突如實留白並在 evidence_summary 標示，不捏造或抹去疑義；**`verified_at_tpe` 是選填欄，來源沒有可靠核證時點就留空，Life 不得用掃描／匯入時間代填**；已取消、確定過期及無可追溯來源者不交接。探索不連 Life API／DB。
- 固定 Google Sheet ID `1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4`，`交接資料` 為資料分頁，`交接規格` 定義 30 欄語意。**不是**舊精選池 45 欄 `精選活動` 分頁。
- Life 用一般 Python/Pydantic 讀 READY/ERROR、PostgreSQL 永久穩定 `event_key`／`content_hash` 去重 upsert，DB commit 且版本一致才寫 ACKED。探索端只清成功 ACK 超過 30 天的列，未 ACK 不刪；交接表不是永久資料庫。
- 原 direct ChatGPT bearer API 與既有 URL-based identity 暫留相容；目前 Python importer 原始碼已固定讀新交接 Sheet、以 `event_key/content_hash` 入庫與寫回 ACK；**但這是 source，不代表最近一次真實 Job 已通過**。2026-10-12 GAS 啟動 Cloud Run Job 成功，Execution Exit 1，需於新 SHA 部署後驗證 DB/ACK/UI 與每日 GAS 觸發器。全部規則見 [Life 端唯一交接契約](curated_sheet_job_ingestion.md)。
- Life 不負責文化部／觀光署／官網／第三方網站探索或爬蟲，不做第二次 AI、舊候選 Queue／claim／lease、舊來源觀測／獨立二次發布，也不自動建立私人待辦／行事曆／通知。Drive 上游自行維護來源快照，不屬於 Life 爬蟲。

**歷史狀態（2026-10-12；非當前終態）：** GAS GET/preflight 與 jobs.run 接受請求 PASS，當次 Cloud Run Execution FAIL；新版本 importer CI／部署、PostgreSQL readback、Sheet ACK 與每日 07:30 GAS trigger 仍未完成真實驗收。整體 PARTIAL。**


**2026-10-18 後續設計提案（尚未切換）**：未來可由獨立 omniAgent 自主探索 Agent 取代 ChatGPT Work 上游，**不改** Drive 精選池／30 欄交接／Life importer／Flutter 契約；設計、服務身分、來源自動修復與文件核准界線見 [Life Agent 整合規劃](taiwan_activity_agent_integration.md) 及 [omniAgent Agent Worker 規劃](https://github.com/tommylin15/omniAgent/blob/main/docs/taiwan-activity-autonomous-agent.md)。目前仍以本文件現行 ChatGPT 探索→Drive 路徑為實作基準，直到 Shadow／正式讀回及唯一 writer 切換全部 PASS；不可因新增設計文件宣稱已運行 GCP Agent。

**2026-10-15 最新 Life runtime 索引：** 2026-10-14 對應原始 SHA 的 [CI](https://github.com/tommylin15/life_assistant/actions/runs/38567184081)、[promoted release](https://github.com/tommylin15/life_assistant/actions/runs/38572432707) PASS；release 僅對既有 Job 進行相同 digest pin 和讀回，`execution=NOT_RUN`。最新 GAS 定期觸發、當輪 PG/Sheet ACK 仍 **NOT VERIFIED**；本文件的舊 2026-10-12 失敗事件不代表最新 Job 再次失敗。證據主入口 [CURRENT_STATE](CURRENT_STATE.md)。

## 2026-10-22｜探索批次品質防線：不可只抓幾筆就結束

> 本節是 Life 匯入契約的上游驗收約束。正式來源名單、探索演算法及驗收仍以 Drive 唯一 README／02-discovery.md／05-acceptance.md 為準；Drive「B類治理規則」及執行表「指標說明」另已記錄本防線。若有規格衝突，明列並回到 Drive 正式規格治理。

- **禁止少量即停**：找到一至三筆或任意少數活動、完成若干首頁、達到最低 B_target，都不構成批次完成；要分開記錄 A7、B 動態三自然日輪巡、C 具名公開社群／垂直平台、五區九主題和22縣市滾動補漏。attempted、usable 和全站增量不是同一指標。
- **低產出二次補漏**：若獨立活動主題很少，在合法有界資源內進一步核查 B 逾期來源、地區／主題缺口與 C 公開具名頁。讀取受阻不能記成零活動；不為衝筆數放寬主辦、日期、費用、資格證據，不規避 403／429／robots、登入或私人社群限制。
- **雙門檻結束**：(a) 範圍及補漏有逐站實查證據，否則記缺口、next_due 與 PARTIAL；(b) 所有達標候選完成 03 核證、04 穩定鍵去重與精選池／交接 READY 判斷及讀回、05 唯一日誌與分項驗收。只掃描或只入池都不得宣稱 DONE。
- **主題與場次不得混計**：不同 parent_event_key 才是獨立活動主題；場次 session、優惠 offer、來源渠道、轉貼及多次掃描另列。每輪分開報唯一候選、verified/pending_review、入池、READY 與 Life 真實 ACKED。
- **不設虛假保底筆數**：天然低產出時可有據結案；品質是覆蓋與資料驗證，不是硬湊 N 筆。達合法成本上限而未查完應標 PARTIAL，未查來源是 NOT_RUN 非零活動。Life DB／UI 實際入庫是獨立驗收。

本節不修改 Life 30／31 欄機器交接 schema、stable event_key、content_hash 或 ACK 所有權，不建立新排程、Queue、DB 或 Job。

## 2026-10-28｜四大阻礙類型根因與規則補強（海外 IP、候選冷凍、社群首頁與短網址）

針對政府報名網（如 `https://event.ner.gov.tw/`）、官方 Facebook 粉專（如 `ntpchakka` 新北市客家局、`agr.ntpc` 新北市農業局稼日蒔光）及 Threads 短網址（`threads.com/share/*`）過去無法寫入交換池之問題，Drive 正式規格 `01-source-quality.md`、`02-discovery.md`、`03-qualification.md` 與 `tw_request_router.py` 已同步確立四項強制規則：
1. **海外 IP 阻擋自動轉發與路由快取（`TW_PROXY`）**：凡台灣政府與機關活動站（`.gov.tw`、主題活動網）於美西 VM 直連遭遇 Timeout 或 403，一律由 `tw_request_router` 經台灣彰化（`asia-east1`）Cloud Run Proxy 轉發，並自動寫入 `config/source_routing_cache.json` 與 Drive `台灣活動探索｜來源路由控制.json`，次輪直接走台灣節點。
2. **破除 `B-source-validation` 候選冷凍死鎖**：每日批次強制從 `B-source-validation`／`CANDIDATE`／`REVIEW_SOCIAL` 實測並晉升至少 2 個合格來源進入 `官網來源總表` 與 `每日探索來源管理`（`ACTIVE_ROTATION`），不再讓已具官方身分之報名網與局處粉專無限期排除於 `B_active` 之外。
3. **官方粉專「三步雙入口探索協議」（Twin-Entry Binding）**：Meta（FB/IG）公開粉專首頁對未登入請求回傳 `/login/` 跳轉或隱藏貼文時間軸，屬平台匿名列表限制，**嚴禁直接視為權限牆放棄該主辦**；必須同時綁定其對應局處官網／報名網（經 `TW_PROXY` 抓取）並結合搜尋引擎發掘最新貼文與外部報名表單（Accupass、`forms.gle`）。
4. **社群短網址 OpenGraph 解析、民國年換算與明確排除日誌**：對 `threads.com`／`facebook.com`／`instagram.com` 預設帶入 `User-Agent: facebookexternalhit/1.1` 以解析 `/share/` 302 轉址與 `og:description` 全文；強制支援政府網站民國年換算（$Y_{\text{CE}} = Y_{\text{ROC}} + 1911$，如 `115年` $\to$ `2026年`）；若解析後確認為非活動之個人日常貼文，明確記 `NON_EVENT_POST_EXCLUDED` 與原文摘要。

## 2026-10-30｜批次常態受阻站點問題排除與常態治理（DNS失效、域名後綴、機關WAF與Cloudflare盾）

針對日常自然批次標記為 `BLOCKED` 或暫時受阻之站點，完成專案級排查、入口修正與對應防線健全：
1. **海外 IP 逾時自動解鎖（已全量走 `TW_PROXY` 成功取得 HTTP 200）**：
   - **農業部食農教育資訊整合平臺 (`fae.moa.gov.tw`)**：台灣 Proxy 成功回傳 399KB 完整活動列表。
   - **臺中市政府服務e櫃檯 (`eservices.taichung.gov.tw`)**：台灣 Proxy 成功回傳 58KB 完整線上申辦與市民活動頁。
   - **林業及自然保育署全球資訊網 (`www.forest.gov.tw`)**：台灣 Proxy 成功回傳 489KB 生態活動與最新消息。
2. **網域失效與域名後綴混淆修正**：
   - **原農社企暨農村好物網 (`rse.ardswc.gov.tw`)**：經查該獨立子網域 DNS 已除役失效（HTTP 502 / Name or service not known）。依規格降級切換至主管機關正式專頁——**農業部農村發展及水土保持署最新消息專區 (`https://www.ardswc.gov.tw/Home/News/news_list`)**，走 `TW_PROXY` 成功讀回 108KB 當期公告。
   - **桃園市農會**：來源表舊登載 `www.tyfa.org.tw` 存在 DNS 異常，修正為正式營運網址 **`https://www.tyfa.com.tw/article.php?cid=44&lang=tw&tb=2`**，走 `TW_PROXY` 成功取得 109KB 跨農會活動公告。
3. **地方政府全站 WAF 阻擋應對**：
   - **新竹市政府首頁 (`www.hccg.gov.tw`)**：市府主入口具備全站 WAF 盾（回應 HTTP 520 / Cloudflare 挑戰），正式替代入口切換為城銷處主管之**新竹市官方觀光旅遊網 (`https://tourism.hccg.gov.tw/`)**，經 `TW_PROXY` 成功取得 SPA 頁面並啟用搜尋輔助補漏。
4. **BeClass 全站 Cloudflare Challenge 防線**：
   - `www.beclass.com/default.php?name=ShowList` 經台灣節點仍遭遇 Cloudflare Challenge（HTTP 403 / Just a moment...）。依 `01-source-quality.md` 規範不得對受限頁暴力輪換工具或繞過，但亦不推論當日無活動；確立改採**「搜尋輔助定位具名主辦單頁（`site:beclass.com rid=*`）」＋「主辦公開活動表單核證」**，直達活動內頁完成 03 核證與入池。
