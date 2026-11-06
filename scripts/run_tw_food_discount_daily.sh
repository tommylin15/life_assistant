#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/mnt/stateful_partition/antigravity/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export LD_LIBRARY_PATH="/mnt/stateful_partition/antigravity/.local/lib:${LD_LIBRARY_PATH:-}"
export HOME="/home/tommylin15_gmail_com"

PROMPT="執行 @life-project 的 life_assistantGPT 唯一正式「雙北41區美食優惠探索與效期總排程」每日批次（台灣時間每日 04:45，Asia/Taipei，緊接於台灣活動探索批次之後）：
依據 doc/food_discounts_spec.md 與 Drive『美食優惠探索｜雙北41區單一總排程操作手冊 V1.3.2』第十章及第十二章循序執行：
一、環境與批次鍵初始化：讀取最新手冊 V1.3.2、草稿 V0.5.2、美食母表（1qwzG8P6wDLtPINoUf-N670TeHVSC6m7jlihDeBjb13U）與交換池『美食優惠｜交接資料.xlsx』，建立當日唯一批次鍵 FOOD-UNIFIED-YYYYMMDD（若當日已 PASS 則避免重複寫入）。
二、每日效期維護與七日續期補正：檢查 AB 領券期、AC 兌換期、AD 活動終日；對 AG<=今日、AD 空白且 R=COLLECTED_SOURCE_CLAIM 之無明確終日活動，查核原公開來源 N，若有持續有效正面證據則更新 AE/AF/AH/AK 並記錄於『效期追蹤』，否則維持 HIDDEN_REFRESH_DUE 或滿 30 日 ARCHIVED_STALE。
三、週一／三／五分區動態搜尋：若當日為週一（14區，28組）、週三（14區，28組）或週五（13區，26組），依『探索輪替計畫』對指定行政區執行 P0 一般手搖飲與台灣國民美食動態網頁搜尋；只收公開來源明示買一送一或折幅>=20%之情報（免逐店核實，保留來源 URL 與未核實揭露）。新增候選嚴守 V1.3.2 第十二章契約，僅寫入 A:AF、AH、AJ:AL，絕不覆寫 AG2/AI2 ARRAYFORMULA 錨點。
四、母表公式驗證與交換池（交接資料）READY 寫入：更新搜尋紀錄、雙北41區覆蓋、批次紀錄與試行紀錄 Doc，讀回驗證『總排程測試』C10=0；依固定 25 個業務欄位計算 Canonical SHA-256 content_hash，保護既有未變動 ACKED 列，將新增或狀態變更列標記 READY 寫入『美食優惠｜交接資料.xlsx』。
五、串接 Life 入庫與回寫 ACK：執行 .venv/bin/python scripts/run_tw_food_discount_batch.py --stage-handoff --sync-db --upload-gdrive 完成 PostgreSQL food_discounts 入庫，將交換池 READY 更新回寫為 ACKED（CREATED/UPDATED/UNCHANGED）與 life_ack_at_tpe 並同步回 Google Drive，逐鍵讀回驗證 READY=0、ERROR=0。"

cd "/home/tommylin15_gmail_com/.gemini/antigravity-cli/scratch/life_assistant"
exec /mnt/stateful_partition/antigravity/.local/bin/agy \
  --model "Gemini 3.8 Flash (Medium)" \
  --dangerously-skip-permissions \
  --print="${PROMPT}"
