# Life Omni｜LINE V2-02 八格 Rich Menu 正式素材與上架工作指示

2026-10-29｜**圖面／程式 SOURCE PASS；OA 實際套用與手機驗收 NOT VERIFIED**。

## 1. 成果與 Source of Truth

- GitHub 八格 JSON 契約：[`scripts/line_rich_menu_v2.py`](../../scripts/line_rich_menu_v2.py)，舊六格 [`scripts/line_rich_menu.py`](../../scripts/line_rich_menu.py) 不變。
- GitHub 圖面再製工具：[`scripts/build_line_rich_menu_v2.py`](../../scripts/build_line_rich_menu_v2.py)，使用 Pillow、Noto Sans CJK；提供 Owner 指定的雙生獸原稿可重建，未提供時使用程式內簡化雙獸造型。由此工具重建的圖可能受原始素材／字體版本影響；正式上傳基準是下方 **Drive 固定 JPG／SHA256**。
- 正式圖（**上傳這張**）：[life_omni_v2_eight_grid.jpg](https://drive.google.com/file/d/1mB_15NAsxDyj3ZGikP4x7FT30Mf4gx2O/view)，Drive ID `1mB_15NAsxDyj3ZGikP4x7FT30Mf4gx2O`，尺寸 **2500×1686**，JPEG，**289918 bytes**，SHA256 `33b2460021d41c71ba56cbd90830361205f01c46d30623f60d4e413e4c794f86`。
- 熱區紅框對照圖（**不可上傳 LINE**）：[life_omni_v2_positions_guide.jpg](https://drive.google.com/file/d/1yxrBJBiroarM0yXJE01Eg8Qr2cjAscdU/view)，ID `1yxrBJBiroarM0yXJE01Eg8Qr2cjAscdU`，397591 bytes。
- 兩份檔案已由 Drive metadata 讀回位於唯一授權根資料夾 `life_assistantGPT/LINE_U16_六格選單`（沿用既有資產資料夾 ID `13hiG7BMsBiQuOyYygPdqIKF3mztJjPJN`；資料夾名稱保留作為歷史，不代表 v2 仍是六格）。
- Google Colab Notebook：`Life_Omni_LINE_V2_02_Eight_Grid_Apply.ipynb`，由本輪 artifact 提供下載；讀取上方 Drive File ID，Token 採隱藏輸入，不存到 Drive/GitHub。本輪未聲稱 Colab 已在 LINE API 執行。

## 2. 點擊座標（與按鈕圖示整格對應）

| 位置 | 按鈕 | x | y | width | height | action |
|---|---|---:|---:|---:|---:|---|
| 上 1 | 快速記錄 | 0 | 0 | 625 | 843 | `postback v=2&cmd=capture.start` |
| 上 2 | 今日總覽 | 625 | 0 | 625 | 843 | `postback v=2&cmd=today.view` |
| 上 3 | 查我的資料 | 1250 | 0 | 625 | 843 | `postback v=2&cmd=search.start` |
| 上 4 | 待辦 | 1875 | 0 | 625 | 843 | `postback v=2&cmd=tasks.list` |
| 下 1 | 購物 | 0 | 843 | 625 | 843 | `postback v=2&cmd=shopping.list` |
| 下 2 | 日曆 | 625 | 843 | 625 | 843 | `postback v=2&cmd=calendar.today` |
| 下 3 | 活動 | 1250 | 843 | 625 | 843 | `postback v=2&cmd=events.latest` |
| 下 4 | Life Omni | 1875 | 843 | 625 | 843 | `uri https://<approved Life Hosting>/today` |

**行為邊界：** V2-01 的活動格 Postback 已有 Flex Carousel／分類／收藏程式；其他前六格暫走現有 `DEFERRED_MENU` LIFF fallback，**尚不是 v2 對話卡片**，不得宣稱 V2-03 已完成。第八格直達 Flutter Web `/today`，瀏覽器 Cookie 不一定與 LINE 共用。

## 3. 離線驗證與可重製

```bash
python -m unittest discover -s tests -p 'test_line_rich_menu_v2.py' -v
python scripts/line_rich_menu_v2.py --life-url https://gen-lang-client-0593591102.web.app/today
# 有 Owner 雙生獸圖源的本地環境：
python scripts/build_line_rich_menu_v2.py --mascot /path/to/twin-beasts.png --out /tmp/life-v2.jpg
python scripts/build_line_rich_menu_v2.py --mascot /path/to/twin-beasts.png --positions --out /tmp/positions-only.jpg
```

不得把 `--positions` 紅框對照圖當作正式 LINE 選單素材。正式圖按 Drive 原 SHA 上架，不以新生成圖自動覆蓋原版。

## 4. 上架（Owner Google Colab）與驗收

1. **先驗 Backend：** 目前 [V2-01 CI](../../doc/line_integration_b_wi.md) 有既有程式；但前輪已查得成功的 [V3 Release #40852323202](https://github.com/tommylin15/life_assistant/actions/runs/40852323202) 紀錄為 `LINE_ENABLED=false`。因此不能拿該成功 Release 當「LINE 對話可用」。
2. 先依 V3 發布程序以**最新已通過完整 CI 的 SHA** 手動發布 `promote=false`、`publish_staging=true`、`enable_line=true` 到 Staging，並驗證 `https://life-assistant-v3-stage-tl15.web.app/api/v1/line/config` 回 200、正確 `origin`／LIFF ID。用同一個 OA 測試時要確認它的 Webhook 是指向相同環境。
3. 在 Colab 上傳本輪 Notebook；它用你的 Google Drive OAuth 讀取上面固定 JPG、尺寸與 SHA，不需手動上傳圖片。執行時於 **`getpass()` 隱藏欄**貼 LINE Messaging API Channel Access Token，**不是 Channel Secret**；不應回貼 Token 聊天。
4. Colab 顯示 OA 名稱，輸入完整帳號名稱作套用確認。呼叫 LINE API：建 Rich Menu → 上傳 JPG → **直接覆蓋所有好友預設選單** → GET 讀回 ID。Owner 已選直接覆蓋，不要求備份舊選單；舊選單本身不會由這段程式刪除。
5. 必須有 `LINE_V2_DEFAULT_MENU_API=PASS` 與 `richMenuId` 才能標「OA API 套用 PASS」。LINE iOS/Android 仍依 [WI-05H](../../doc/line_integration_b_wi.md) 分別測試；第 1–6 格在 V2-03 前只驗 fallback，第 7 格驗 Flex、Tag、收藏，第 8 格驗 Life 登入。
6. 未見 LINE 真正 API 收據前 `OA apply=NOT VERIFIED`，未見手機測試前 `V2-02=PARTIAL`。與 v1 六格 Owner PASS 分開記錄，v1 功能與資料不刪除。

官方依據：[Rich Menu 使用文件](https://developers.line.biz/en/docs/messaging-api/using-rich-menus/)｜[Postback Action](https://developers.line.biz/en/docs/messaging-api/actions/)｜[圖片規格](https://developers.line.biz/en/reference/messaging-api/)。
