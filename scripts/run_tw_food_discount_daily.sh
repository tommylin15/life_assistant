#!/usr/bin/env bash
set -Eeuo pipefail
export PATH="/mnt/stateful_partition/antigravity/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export HOME="/home/tommylin15_gmail_com"

PROMPT="執行 @life-project 的 life_assistantGPT 唯一正式「雙北41區美食優惠探索與效期總排程」每日批次（台灣時間每日 04:45，Asia/Taipei，緊接於台灣活動探索批次之後）：
依據 doc/food_discounts_spec.md 與 Drive『美食優惠探索｜雙北41區單一總排程操作手冊 V1.3.2』第十章及第十二章循序執行：
一、環境與批次鍵初始化：讀取最新手冊 V1.3.2、草稿 V0.5.2 與美食 Google Sheets（1qwzG8P6wDLtPINoUf-N670TeHVSC6m7jlihDeBjb13U），建立當日唯一批次鍵 FOOD-UNIFIED-YYYYMMDD（若當日已 PASS 則避免重複寫入）。
二、每日效期維護與七日續期補正：檢查 AB 領券期、AC 兌換期、AD 活動終日；對 AG<=今日、AD 空白且 R=COLLECTED_SOURCE_CLAIM 之無明確終日活動，查核原公開來源 N，若有持續有效正面證據則更新 AE/AF/AH/AK 並記錄於『效期追蹤』，否則維持 HIDDEN_REFRESH_DUE 或滿 30 日 ARCHIVED_STALE。
三、週一／三／五分區動態搜尋：若當日為週一（14區，28組）、週三（14區，28組）或週五（13區，26組），依『探索輪替計畫』對指定行政區執行 P0 一般手搖飲與台灣國民美食動態網頁搜尋；只收公開來源明示買一送一或折幅>=20%之情報（免逐店核實，保留來源 URL 與未核實揭露）。新增候選嚴守 V1.3.2 第十二章契約，僅寫入 A:AF、AH、AJ:AL，絕不覆寫 AG2/AI2 ARRAYFORMULA 錨點。
四、試算表與試行紀錄讀回：更新搜尋紀錄、雙北41區覆蓋、批次紀錄與試行紀錄 Doc，讀回驗證『總排程測試』C10=0。
五、同步匯入 Life PostgreSQL：執行 python3 scripts/run_tw_food_discount_batch.py --sync-db 將最新美食優惠候選同步至 Life 獨立資料表 food_discounts 並驗證讀回。"

cd "/home/tommylin15_gmail_com/.gemini/antigravity-cli/scratch/life_assistant"
exec /mnt/stateful_partition/antigravity/.local/bin/agy \
  --model "Gemini 3.8 Flash (Medium)" \
  --dangerously-skip-permissions \
  --print="${PROMPT}"
