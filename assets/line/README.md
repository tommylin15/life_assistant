# Life × LINE 六格 Rich Menu（U16）

狀態：圖片原稿、重產程式、六格點擊座標已具備；LINE OA 套用與 iOS/Android 真人驗收 **NOT VERIFIED**。

## 產生圖片

原始 SVG：assets/line/rich_menu_v1.svg  
產圖程式：scripts/build_line_rich_menu.py  
六格文字與座標來源：scripts/line_rich_menu.py

CairoSVG 僅供本地設計產圖，不納入 Cloud Run runtime 依賴。執行：

    python -m pip install cairosvg==2.8.2
    python scripts/build_line_rich_menu.py --out /tmp/life-line-rich-menu.png --svg-out /tmp/life-line-rich-menu.svg
    python -m unittest discover -s tests -p 'test_line_rich_menu_art.py' -v

程式會驗證圖片是 PNG、尺寸 2500×1686、檔案不超過 1,000,000 bytes；不會使用 LINE API。務必在產圖環境確認繁體中文字體可正確顯示。不得將字型檔提交到倉庫。

## 點擊區與頁面

| 位置 | 標籤 | LIFF page | bounds (x, y, width, height) |
|---|---|---|---|
| 上左 | 快速記錄 | capture | 0,0,833,843 |
| 上中 | 今日總覽 | today | 833,0,833,843 |
| 上右 | 查我的資料 | search | 1666,0,834,843 |
| 下左 | 待辦・購物 | tasks | 0,843,833,843 |
| 下中 | 日曆・活動 | calendar | 833,843,833,843 |
| 下右 | 我的 Life | home | 1666,843,834,843 |

待辦・購物與日曆・活動是組合入口，初始會開 tasks/calendar；使用者可在 LIFF 裡切換 shopping/activities。

## OA 安全套用前置

**未核對環境前不得執行 --apply。** 既有套用工具會建立新 Rich Menu、上傳圖片，然後替「官方帳號所有好友」更換預設選單，不能當作只對單一測試帳號生效。

1. 唯讀確認現行 OA/Messaging API channel 與正在服務的 Staging 或 Production，記錄舊 richMenuId 與恢復方式；若共用同一 OA，不能讓一個 webhook 同時指向兩環境。
2. 確定實際 LIFF ID、LIFF Endpoint、Hosting Origin、/api/v1/line/config 相符，且沒有把測試 ID 誤用為正式 ID。
3. 先產生六格的 JSON 預覽，核對每格 LIFF URI：

       python scripts/line_rich_menu.py --liff-id <REAL_LIFF_ID>

4. 核對資料與圖檔後，才能在安全終端使用已有 Secret 中的 Messaging API access token，以環境變數 LIFE_LINE_ACCESS_TOKEN 注入，並**明確決定**是否執行以下會變更所有好友預設選單的命令：

       python scripts/line_rich_menu.py --liff-id <REAL_LIFF_ID> --image /tmp/life-line-rich-menu.png --apply

5. 寫下新 richMenuId，在 LINE iOS/Android 真正開啟 OA 聊天室、逐格測試六個 deep link、LIFF 登入及返回；per-user 選單可能覆蓋預設選單。LINE 電腦版沒有 Rich Menu，不作為 U16 成功證據。
6. 如需回復，使用事前記錄的舊 richMenuId 恢復預設選單；不刪除舊選單或原有 Life 資料。

**U16 = NOT VERIFIED** 直到 OA 實際套用、六格點擊與行動裝置驗收皆有證據。圖片／程式／CI 的 PASS 不可當作 OA 已套用。

官方文件：https://developers.line.biz/en/docs/messaging-api/using-rich-menus/
