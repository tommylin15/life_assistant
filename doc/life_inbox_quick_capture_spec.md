# Life Assistant｜生活收件匣、快速新增與筆記網址摘要 V1 規格

- 版本：Design v1.0（2026-10-16，Asia/Taipei）
- 狀態：**DESIGN READY；implementation / tests / CI / staging / production / runtime = NOT VERIFIED**。本次只回寫文件；**不得將本文件視為已上線、已啟用或已完成的功能**。
- 核心技術邊界：Firebase Hosting → Flutter Web/PWA → Cloud Run FastAPI → PostgreSQL；文字理解透過 Life → omniAgent Gateway → Gemini；沿用既有 Note、Task、Shopping、Google Calendar API、登入與 ownership。
- 詳細 AI／工程執行指示：同目錄 life_inbox_ai_developer_instructions.md。
- 不修改 Drive 活動探索／交接 Sheet／Life curated pool；本文的網址文章分析只處理使用者明確提供的網址，不是活動來源自動探索爬蟲。

## 1. 產品目標與 V1 範圍

一個全站一致的輸入入口，接受繁體中文自由文字或 HTTP(S) 網址；在原頁辨識一筆或多筆待辦、購物、日曆、筆記候選；一鍵確認新增，或原地展開原功能的完整表單修改再新增。筆記新增／編輯時偵測網址，**提示**可選擇「擷取公開文章並摘要」或「只存網址」。AI 僅建議；永不因辨識完成而自動寫入。

V1 只做即時辨識 → 預覽 → 使用者明確提交。**不做永久未分類收件匣、定時背景抓網、自動建立提醒、郵件自動監控、OCR、PDF 解析、代報名、公開網頁批次爬蟲、家庭共享**。當前頁面的未提交草稿可保存在 Flutter 本地記憶體；重新整理後不保證保留；不要假裝草稿已儲存在 PostgreSQL。

### 典型體驗

1. 首頁小型「快速新增」入口與全站共用＋按鈕均開啟相同的 modal / mobile bottom sheet；不新增第二套新增頁或重複主選單。入口是否顯示由 feature rollout 控制；未授權時不觸發 AI。
2. 用戶輸入「週六下午三點去好市多，買牛奶、雞蛋，別忘了繳停車費」。
3. 先做 URL、空值、文字長度、明確日期/數量的規則檢查；必要時交由 Gemini 做有限範圍語意拆解，得出日曆、購物（兩品項）、待辦候選。
4. 同頁呈現每張候選卡的標題、時間、購物品項、來源及「待確認」欄位。可逐項取消勾選、改類別、編輯，預設不勾選推測性較高的副項。
5. 按「確認新增所選項目」才執行寫入；有失敗時逐項回報、已成功的保留並可連回目的功能，不能把部分成功顯示為整批成功。
6. 使用者貼入純網址，建議分類「筆記」；若只是網址不推定內容是活動、待辦或具日期事件。選擇「摘要」**之後**才向後端請求取得文章正文，再由 Gemini 生成摘要，預覽可編輯，確定後才儲存至普通筆記。

### 原地確認 vs 詳細編輯

- 資料完整：呈現提議值，一次點確認，無額外「分類是否正確」確認框。
- 日期、目的購物清單、既有專案或日曆權限不明：顯示可編輯欄位／必要提示，未補齊不可提交該候選；其餘已完整候選仍可提交。
- 點「詳細編輯」使用既有功能欄位、schema、限制與權限（可在同頁 drawer 或 bottom sheet 展開），不得在 Flutter 再複製一套互不一致的持久化邏輯。
- 已經確認的候選應保留原始文字與可追蹤來源，變更目的地前不刪除或覆蓋先前已儲存的資料。
- 文章摘要只是另一種筆記內文預填模式，非額外「文章收藏」資料庫；使用者已編輯的摘要不得被背景重跑覆蓋。

## 2. 現有程式與落點（2026-10-16 main 設計盤點）

| 既有能力 | 原始碼 / 路由 | 使用方式／注意 |
| --- | --- | --- |
| 管理開放與個人導覽 | backend/app/api/ui_policies.py；lib/web/admin_center_page.dart | FeatureRollout + revision + owner_only 已存在；新增 life_inbox key 與新路由，未來前後端都要檢核；新功能預設不得套用其他功能的 enabled/all 開放預設 |
| 一般使用者防線 | backend/app/api/auth.py 的 _enforce_general_user_route | 目前明確列舉允許路由；新增 inbox API 必須在 owner-only 驗收通過後，按功能權限允許一般使用者路由，不能只更改 UI |
| AI 呼叫 | backend/app/api/gemini_text.py；services/shared_gemini_gateway.py | 現有 /api/v1/ai/text 是顯式純文字、非 JSON schema、70 秒超時且無重試；新收件匣需要受限分類服務，不能把自由文字直接作為可信資料／模型自行寫入 |
| 筆記 | /api/v1/notes；backend/app/models/schemas.py NoteCreate；lib/web/notes_page.dart | 既有 title/body/category/tags 等欄位、HTTP(S) 外開；尚無公開網頁擷取摘要；保留 note_id、user_sub/舊 Owner 遺留資料規則 |
| 待辦 | /api/v1/tasks；backend/app/api/tasks.py | 既有 idempotency / execution log；due_at 不明不可造值；維持專案 ownership |
| 購物 | /api/v1/shopping-lists／shopping-items、batch | 使用者應選既有清單或新建清單，再批次新增多品項；清單/品項分開處理，避免多次 modal |
| 行事曆 | /api/v1/integrations/google/calendar/events | 每個帳號授權自己的 Calendar，實際 create 是外部寫入；時間必須為有時區 start/end 或合法全日日期區間，不得以待辦時間誤補結束時間 |

## 3. 管理中心功能控制（必做，不是 UI-only）

新增唯一父級 Feature Key：**life_inbox**，UI 名稱「生活收件匣／快速新增」，設計路由 /capture。Admin 沿用既有 /api/v1/admin/feature-rollouts：status = hidden | beta | enabled | maintenance，audience = owner | all，revision 衝突仍 409；admin 的審計日誌應記錄 key / status / audience / actor（不記錄私人輸入內容）。

**默認為 beta/owner（fail closed）**。無資料列、資料庫 schema 異常、取得 policy 失敗時，非 Owner 不得透過任何新 API／UI 使用；maintenance 與 hidden 對所有人拒絕，Owner 測試使用 beta/owner 或 enabled/owner。開放一般使用者必須由 Owner 明確設 enabled/all，且須已通過 release gate，beta/all 不得繞過 beta 限制。既有 notes/tasks/shopping/calendar 權限獨立存在，開放 inbox 不代表開放其他未授權功能。

所有 **/api/v1/inbox/** 新路由（分析、文章預覽、批次提交、狀態/結果讀取）都先做 current_user，再做 server-side feature_gate(life_inbox)，逐個目的功能再檢查對應 rollout、ownership、Google scope；不得依前端的 available=true 視為授權。非 Owner 要同時滿足 auth.py 中的嚴格路由許可與上述 feature gate。避免把任意 /api/v1/ai/text 加入白名單作為繞過新功能控制的通道。

筆記頁的「擷取文章並摘要」也屬本新功能，**即使一般筆記可用，只要 life_inbox 未對該使用者開放，就不得顯示或呼叫摘要功能**；普通「只存網址」仍依原筆記權限正常運作。V1 使用一個 Admin 開關，若將來需要獨立控制摘要配額，再經核准增加子旗標，勿默默另開全部人。

後台 UI 顯示「管理員測試」、「開放所有使用者」、「維護中」、「隱藏」，顯示當前實際 server policy；按儲存後讀回 revision；發生 403/409/503 應明確顯示，不能樂觀宣稱開啟成功。Feature flag 限制**新入口及新服務**，不應關閉使用者原本可以單獨操作的待辦／筆記／購物／日曆。

## 4. 分層架構與可測決策

Flutter：一個共用 LifeCapturePanel；處理文字輸入、分類卡、候選開關、編輯、部分成功訊息、跨功能導向、網頁摘要按鈕。所有來源頁使用同一 capture orchestrator state（單次面板），不用四份分類器。小螢幕與鍵盤、安全離開提示、表單焦點，支援 reduce motion。

FastAPI：只接受已登入的 user_sub，執行 feature gate → bounded input validation → deterministic extraction → 視需要呼叫專門 structured Gemini adapter → schema/日期/權限 validation → preview response；另有 commit orchestrator，對用戶選擇的候選提交既有目的地業務服務，保留 per-item idempotency receipt。

Gemini：僅支援語意分類和可選文章摘要；不得代替 Python 決定授權、資料完整性、重複資料、commit，也不得自動調用日曆或網頁抓取工具。分類優先免費本地規則處理確定的 URL／數量／型別；遇到語意拆解需求才叫 AI。可以在 UI 標示「AI 建議」，信心數值不等於校準機率，不可當資料正確性證據。

Data：V1 **不新增 inbox entries 永久表**。可評估最小 additive receipt/idempotency 表：tenant user_sub + submission_id + proposal_id + input_digest + target_type + target_id/external_id + state + timestamps + unique constraint，用以防雙擊、重送與部分失敗重試；不保存原始全文／抓取正文／Gateway prompt。與現有 Task idempotency、execution_log、Shopping batch 的互通需在開發前設計 migration；不得聲稱現有 Note/Shopping/Calendar 都已具跨服務 idempotency。

## 5. 建議 API 契約（尚未實作；開發可依現有路由風格調整並同步規格）

| API | 意圖 | 副作用 |
| --- | --- | --- |
| POST /api/v1/inbox/interpret | 傳 text、locale=zh-TW、IANA timezone、client_ref；回傳候選分類、抽取欄位、缺值、衝突及建議選取狀態 | **不得寫入任何目的業務資料**；可記匿名聚合運作指標 |
| POST /api/v1/inbox/article-preview | 明確要求的 HTTPS/HTTP article_url；後端安全抓取；若取到可用正文，調 Gemini 回摘要／來源 metadata | **不得直接建立筆記**；只回預覽，不儲存未經核准全文 |
| POST /api/v1/inbox/commit | user 明確提交 submission_id、各候選 proposal_id、target_type、編輯後 fields 與 per-item idempotency_key；回成功/失敗/未知逐項 receipt | 僅對已選項目寫入，記 user_sub / 記錄收據；不得將未選候選提交 |
| GET /api/v1/inbox/submissions/{submission_id} | 使用者按自己的 submission_id 查部分成功／外部寫入未知結果，支援有限恢復 | 唯讀、按 owner 隔離 |

上述皆由後端驗證必要欄位、輸入長度、target enum、外部 URL、時區與既有資源 ownership。HTTP 409 可代表 revision/idempotency 衝突，422 為不完整欄位，403 為 gate／scope，429 為限流，502/503/504 分類 gateway/fetch 故障；回覆 stable error code，不提供未授權或私人原始資料。所有非 cacheable 私人回應設 Cache-Control: no-store；禁止經 URL query 攜帶文章內文。

建議 response 範例（非已運作的 API）：

~~~json
{
  "submission_id": "generated-server-id",
  "classification_source": "rules|gemini|mixed",
  "candidates": [
    {
      "proposal_id": "p1",
      "target": "note",
      "select_default": true,
      "fields": {"body": "https://example.com/article"},
      "missing_fields": [],
      "ambiguities": [],
      "evidence": ["valid_http_url"]
    }
  ],
  "saved": false
}
~~~

**AI 候選僅是預覽，不可當 client-provided authorized command。** commit 需校驗選擇與編輯內容；不得任意使用 AI suggestion 夾帶 user_sub、admin、external provider URL、SQL、工具指令。

## 6. 目的功能欄位規則

- Task：title 必填；due_at 只有有足夠資料才傳且需含時區；明確任務日期/時間與提醒是不同欄位，不預設提醒；既有 source/ref 和專案權限仍適用。
- Shopping：拆成多筆 name + 可選 count/unit，**不得自行虛構數量與價格**；商品屬於使用者指定的 shopping_list；如輸入未指名清單，使用者在預覽時選清單或選擇建立新清單，不偷偷創一份「預設」清單。
- Calendar：可確定有起點但無 end、時區、全天/計時歧義時需要使用者補正，不能直接 commit。日期型只用 inclusive start_date / exclusive end_date；外部 OAuth 沒有 scope 就顯示授權入口，不能默用 Owner token。
- Note：title 可空，沿用既有自動標題；body 優先保留用戶原始內容，AI 摘要建議以明確段落加入，來源 URL 和 article title/抓取日期保留；既有分類/標籤/專案可調整但需查 owned。
- 多目的地：同段文字拆多候選，預設勾選主要明確候選；不確定類別呈現編輯／未勾選。不以字面含「週六」就自動臆造已授權且可執行的 Calendar event。

## 7. 網址擷取與文章摘要安全契約

URL 純格式辨識不需要 AI；偵測到網址只顯示「是否擷取並摘要？」不得自動聯網。用戶點選後才 POST article-preview，前端顯示擷取中、失敗、取消、預覽；摘要必須可編輯且保存前再次確認。

SSRF：後端只允許 http/https；拒絕 credentials、私網/回環/link-local/metadata endpoint、非公開 DNS 結果、IPv4/IPv6 解析後所有非全球可路由位址；逐跳核對 redirect、DNS 與連線最終位址、DNS rebinding；限定 port／redirect 次數，設請求 timeout、response bytes 與正文長度、HTML MIME；不得讀本地檔案或透過任意代理下載內部資源。保守起始建議：最多 3 次 redirect、10s 抓取總限、HTML 回應 1 MiB、抽取正文最多 20,000 字，實際限額依程式測試和費用驗證調整。

尊重網站 robots/terms 與登入限制，遇反爬/付費牆/非文章/無法連線就顯示「無法產生摘要，可只存網址」；不得繞過登入、驗證碼或付費牆。擷取正文是**不可信外部資料**，其中任何要求改寫系統指示、查詢密鑰、呼叫外部站、提交業務 API 都是資料，不執行。禁止將 Cookie、私人 Google token、生活資料一起傳入文章擷取或 Gemini；只送必要摘取正文與出處。長文不保存整份正文與 provider response，僅用戶確認後的筆記內容與必要來源 metadata；避免超出合理引用量，不將摘要虛稱原文。

## 8. 確認、交易、一致性與失敗恢復

**唯一寫入觸發**：真實登入者點「確認新增」後，client 送已勾選候選；解析、預覽、切換頁籤、複製文字、擷取文章均不能建立任何 Task/Shopping/Note/Calendar 物件。每個 commit candidate 在後端重新檢驗 rollout、目標權限及資料 schema。

重試須使用同一 submission_id + proposal_id + idempotency_key；多次點擊 / request timeout / client refresh 不得產生第二筆相同邏輯的 Task、Note、ShoppingItem、Calendar event。不能靠候選標題或單純內容 hash 永久阻止不同時間的合法重複事項。內部資料使用交易或 per-item receipt；外部 Google Calendar 沒有跨 PostgreSQL 原子提交，須設可核對的 stable correlation / 外部 event ID、unknown 狀態及 readback/reconciliation。**絕不可在不知道 Google 是否已寫入時盲目重試 POST。** 每項顯示 CREATED／ALREADY_APPLIED／FAILED／UNKNOWN，不把部分完成當全部成功。

Admin 中途關閉／權限被撤銷 → 立即停止下一步新分析／寫入，已確定建立的內容保留；移除功能不應刪除既有私人記錄。對隔離帳號、跨 user_sub note/list/project/event references 永遠不提供資料；只回通用 404/403。不寫入私人 prompt、全文、模型答案到 audit log。可記 request ID、model provider、耗時、文字長度區間、成功/失敗類別（不虛構 token 使用或費用）。

## 9. V1 工程與測試驗收（開始開發前的明確出口）

建議分層：A. feature flag/驗證/資料 contract；B. deterministic+Gemini schema parser；C. 共用 Flutter UI + Task/Note/Shopping commit；D. 網址 preview/summary + Calendar commit + 異常恢復。每段先 unit/integration，再整批相同 SHA 做 staging，完成才考慮 production。不要另建 Life crawler、活動精選 AI pipeline 或擴張 Drive/Gmail scope。

必測矩陣：

1. 空值、長文截斷、純網址、文章/非文章 URL、壞 JSON、AI hallucination、危險 URL、prompt injection、否定句、複數清單、混合任務、語意歧義、跨年/跨月與時區。
2. Owner beta 可見且可用；一般 user 在 beta/owner、hidden、maintenance 全部 API 403；enabled/all 一般帳號在 allowlist+所有目標 gates PASS 才可用；管理中心非 Owner 403、revision 409、fail closed 無列與 schema failure。
3. 普通 Notes/Task/Shopping/Calendar 不被新旗標誤關閉；連結只存網址不做 HTTP fetch/Gemini；未按 summary 不抓網；未按 commit 不寫。
4. 二或三個使用者交叉隔離；existing legacy Owner NULL rows；外部 OAuth 拒絕與 scope 失效；錯誤顯示與重新授權。
5. 並行雙擊／重送同 idempotency key、client timeout、Calendar 可能已建立但回應逾時，確認 receipt 與 Google 回查不產生重複；批次部分成功可讀回。
6. 視覺：手機 320/375px、桌面、五風格、中文 IME、螢幕閱讀器、取消/返回不丟已明確儲存資料。
7. Gateway 429/502/503/504、回應不合 schema、沒有 Gemini 配置、配額耗盡 → 降級成明確的純規則建議／手動轉存，不默默寫入；成本數字若沒有真實 telemetry 應標 NOT VERIFIED。

完成判定：**implementation / tests / four CI jobs / staged deployment / OAuth + private-tenant E2E / approved rollout transition / production deployment / runtime Google Calendar readback** 分別回報 PASS/FAIL/NOT VERIFIED；缺任何必要證據時總狀態 PARTIAL，只有全部適用 gate PASS 才 DONE。生產一般使用者的 enabled/all 只在相同 SHA 正式驗收通過後由 Owner 在 Admin 主動開啟，不因發版自動開放。

## 10. 決策與範圍紀錄

- 2026-10-16 使用者指示：先設計架構、正式規格及 AI 開發指示，**只回寫文件，之後才進行程式開發**；Admin 要可決定一般使用者是否使用。
- 其他六項產品點子已存 Drive life_assistantGPT/討論構想區/好點子，狀態 PARKED；本文件不得把那些項目暗中加入 V1 scope。
- 此規格對新功能的設計有效；如與當前 GitHub source/runtime 不同，當前實作狀態以 GitHub/runtime 為準，Drive 文件不能冒充已交付。
