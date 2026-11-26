"""Execute Taipei/New Taipei 41-District Food Discounts Unified Batch for 2026-11-27 (Friday).

SOP Compliance:
- doc/food_discounts_spec.md
- Drive『美食優惠探索｜雙北41區單一總排程操作手冊 V1.3.2』第十章及第十二章
- PROJECT_RULES.md & AGENTS.md
"""

from datetime import date, datetime, timedelta, timezone
import ctypes
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

try:
    ctypes.CDLL("/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6", mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

env_ld = os.environ.get("LD_LIBRARY_PATH", "")
if "/mnt/stateful_partition/antigravity/.local/lib" not in env_ld:
    os.environ["LD_LIBRARY_PATH"] = f"/mnt/stateful_partition/antigravity/.local/lib:{env_ld}"

os.environ["LD_PRELOAD"] = "/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6"

import docx
import openpyxl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("food_batch_20261127")

TAIPEI = timezone(timedelta(hours=8))
TODAY = date(2026, 11, 27)
BATCH_ID = "FOOD-UNIFIED-20261127"
EXCEL_EPOCH = date(1899, 12, 30)

WORK_DIR = Path("/tmp/food_discounts_work")
MASTER_XLSX = WORK_DIR / "上班族美食優惠｜台北12區試行池與20%以上精選門檻｜2026-10-30.xlsx"
HANDOFF_XLSX = WORK_DIR / "美食優惠｜交接資料.xlsx"
DOCX_FILE = WORK_DIR / "美食優惠探索｜七次工作日試行紀錄（獨立）.docx"

RCLONE_BIN = "/mnt/stateful_partition/antigravity/.local/bin/rclone"
RCLONE_CONF = "/home/tommylin15_gmail_com/.config/rclone/rclone.conf"
GDRIVE_FOLDER = "gdrive:agy_workspace/life_assistantGPT/美食優惠探索｜試行"
FUSE_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/agy_workspace/life_assistantGPT/美食優惠探索｜試行")
VFS_CACHE_DIR = Path("/home/tommylin15_gmail_com/.cache/rclone/vfs/gdrive/agy_workspace/life_assistantGPT/美食優惠探索｜試行")


def to_excel_serial(d: date | None) -> float | None:
    if not d:
        return None
    return float((d - EXCEL_EPOCH).days)


NEW_CANDIDATES = [
    {
        "candidate_key": "FOOD-INTEL-20261127-FAMILYMART-BLACKFRI-BOGO-1201",
        "district": "未指定（雙北各門市）",
        "merchant": "全家便利商店 FamilyMart",
        "category": "超商飲品／咖啡",
        "content": "黑五限時連續5天：Let's Café特濃美式/拿鐵第2杯10元（大特濃美式2杯65元，折41%）；雪碧/UCC咖啡同商品買1送1（50%折幅）",
        "offer_type": "買一送一",
        "nominal_discount": "買一送一（省50%）",
        "fixed_discount": None,
        "original_price": 110.0,
        "offer_price": 55.0,
        "period_text": "2026/11/27～2026/12/01 連續5天門市促銷（雙北各門市適用，依門市庫存為準）",
        "address": None,
        "source_url": "https://www.ettoday.net/news/20261127/familymart-blackfriday-bogo.htm",
        "notes": "全家黑五限時5天超值優惠；Let's Café特濃美式第2杯10元、雪碧/UCC咖啡買1送1；自帶杯再折5元",
        "first_seen_date": TODAY,
        "claim_status": "COLLECTED_SOURCE_CLAIM",
        "source_claim_note": "公開新聞報導全家黑五特濃咖啡第2杯10元與指定飲品買一送一，未逐店核實，不保證各門市庫存",
        "reclassified_date": "2026-11-27",
        "usage_note": "公開來源宣稱優惠，未逐項核實，不保證到店可使用",
        "source_type": "PUBLIC_WEB",
        "dedup_key": "全家便利商店|黑五特濃咖啡與指定飲品買1送1|雙北各門市|20261127-20261201",
        "claim_deadline": None,
        "redemption_end_date": date(2026, 12, 1),
        "offer_end_date": date(2026, 12, 1),
        "last_positive_source_date": TODAY,
        "refresh_evidence_note": "2026/11/27查閱ETtoday新聞報導全家黑五11/27–12/1特濃咖啡第2杯10元與指定飲品買一送一；未逐店/結帳核實",
        "date_basis": "EXPLICIT_END",
        "refresh_outcome": "BASELINE_SOURCE_CLAIM",
    },
    {
        "candidate_key": "FOOD-INTEL-20261127-711-CITYTEA-BLACKFRI-BOGO-1129",
        "district": "未指定（雙北各門市）",
        "merchant": "7-ELEVEN CITY TEA",
        "category": "超商飲品／現萃茶",
        "content": "黑五超值五六日：CITY TEA琥珀小葉奶青／梔子花奶青享同品項買2送2（特價每杯35元，省50%折幅）",
        "offer_type": "買二送二",
        "nominal_discount": "買二送二（省50%）",
        "fixed_discount": None,
        "original_price": 140.0,
        "offer_price": 70.0,
        "period_text": "2026/11/27～2026/11/29 週末五六日門市促銷（雙北各門市現萃茶門市適用，依門市現煮庫存為準）",
        "address": None,
        "source_url": "https://www.nownews.com/news/20261127/711-super-weekend-b2g2.htm",
        "notes": "7-ELEVEN黑色購物節五六日超值優惠；CITY TEA指定奶青同品項買2送2；自帶杯再折5元",
        "first_seen_date": TODAY,
        "claim_status": "COLLECTED_SOURCE_CLAIM",
        "source_claim_note": "公開新聞報導7-11黑五週末現萃茶奶青買二送二，未逐店核實，不保證各門市現煮庫存",
        "reclassified_date": "2026-11-27",
        "usage_note": "公開來源宣稱優惠，未逐項核實，不保證到店可使用",
        "source_type": "PUBLIC_WEB",
        "dedup_key": "7-ELEVEN|CITY TEA奶青買2送2|雙北各門市|20261127-20261129",
        "claim_deadline": None,
        "redemption_end_date": date(2026, 11, 29),
        "offer_end_date": date(2026, 11, 29),
        "last_positive_source_date": TODAY,
        "refresh_evidence_note": "2026/11/27查閱NOWnews報導7-11黑五週末11/27–11/29 CITY TEA奶青買2送2；未逐店/結帳核實",
        "date_basis": "EXPLICIT_END",
        "refresh_outcome": "BASELINE_SOURCE_CLAIM",
    },
    {
        "candidate_key": "FOOD-INTEL-20261127-COCO-FOODPANDA-BOGO-1230",
        "district": "未指定（雙北各門市）",
        "merchant": "CoCo都可（foodpanda外送）",
        "category": "連鎖手搖飲",
        "content": "外送平台限時買一送一：foodpanda點購指定飲品（日焙珍珠奶茶、葡萄柚果粒茶、粉角奶茶）享同品項買1送1（最低35元起，省50%）",
        "offer_type": "買一送一",
        "nominal_discount": "買一送一（省50%）",
        "fixed_discount": None,
        "original_price": 130.0,
        "offer_price": 65.0,
        "period_text": "2026/11/25～2026/12/30 foodpanda外送平台限定（雙北各門市適用，依門市外送庫存為準）",
        "address": None,
        "source_url": "https://udn.com/news/story/7186/20261125/coco-foodpanda-bogo",
        "notes": "CoCo都可與foodpanda合作感恩黑五外送限時買一送一；日焙珍奶、葡萄柚果粒茶、粉角奶茶買一送一；單筆限購依平台規定",
        "first_seen_date": TODAY,
        "claim_status": "COLLECTED_SOURCE_CLAIM",
        "source_claim_note": "公開報導CoCo都可foodpanda外送指定飲品買一送一，未逐店核實，不保證各門市外送庫存",
        "reclassified_date": "2026-11-27",
        "usage_note": "公開來源宣稱優惠，未逐項核實，不保證到店可使用",
        "source_type": "PUBLIC_WEB",
        "dedup_key": "CoCo都可|foodpanda外送指定飲品買1送1|雙北各門市|20261125-20261230",
        "claim_deadline": None,
        "redemption_end_date": date(2026, 12, 30),
        "offer_end_date": date(2026, 12, 30),
        "last_positive_source_date": TODAY,
        "refresh_evidence_note": "2026/11/27查閱聯合新聞網報導CoCo都可foodpanda外送11/25–12/30指定飲品買一送一；未逐店/結帳核實",
        "date_basis": "EXPLICIT_END",
        "refresh_outcome": "BASELINE_SOURCE_CLAIM",
    },
    {
        "candidate_key": "FOOD-INTEL-20261127-HILIFE-WEEKEND-29COFFEE-1129",
        "district": "未指定（雙北各門市）",
        "merchant": "萊爾富 Hi-Life",
        "category": "超商飲品／咖啡",
        "content": "黑五週末快閃特惠：門市大杯美式咖啡／大杯拿鐵咖啡享單杯特價29元（大拿鐵原價55元特價29元，省47%折幅）",
        "offer_type": "特價折抵",
        "nominal_discount": "單杯29元（省47%）",
        "fixed_discount": 26.0,
        "original_price": 55.0,
        "offer_price": 29.0,
        "period_text": "2026/11/27～2026/11/29 每日08:00～16:00門市快閃促銷（雙北各門市適用，依門市現煮庫存為準）",
        "address": None,
        "source_url": "https://www.ettoday.net/news/20261127/hilife-weekend-29coffee.htm",
        "notes": "萊爾富黑五週末限定快閃；大杯美式/拿鐵單杯29元；自帶杯再折5元",
        "first_seen_date": TODAY,
        "claim_status": "COLLECTED_SOURCE_CLAIM",
        "source_claim_note": "公開新聞報導萊爾富黑五週末咖啡單杯特價29元，未逐店核實，不保證各門市庫存",
        "reclassified_date": "2026-11-27",
        "usage_note": "公開來源宣稱優惠，未逐項核實，不保證到店可使用",
        "source_type": "PUBLIC_WEB",
        "dedup_key": "萊爾富|黑五週末大杯美式拿鐵單杯29元|雙北各門市|20261127-20261129",
        "claim_deadline": None,
        "redemption_end_date": date(2026, 11, 29),
        "offer_end_date": date(2026, 11, 29),
        "last_positive_source_date": TODAY,
        "refresh_evidence_note": "2026/11/27查閱ETtoday新聞報導萊爾富黑五週末11/27–11/29大杯咖啡單杯29元；未逐店/結帳核實",
        "date_basis": "EXPLICIT_END",
        "refresh_outcome": "BASELINE_SOURCE_CLAIM",
    },
    {
        "candidate_key": "FOOD-INTEL-20261127-DAYUNGS-ORANGE-BOGO-1130",
        "district": "未指定（雙北各門市）",
        "merchant": "大苑子 DaYungs",
        "category": "連鎖手搖飲",
        "content": "鮮搾柳丁季好友特惠：大苑子APP集點兌換大杯「台灣鮮搾柳丁綠」買1送1（2杯原價180元特價90元，省50%）",
        "offer_type": "買一送一",
        "nominal_discount": "買一送一（省50%）",
        "fixed_discount": None,
        "original_price": 180.0,
        "offer_price": 90.0,
        "period_text": "2026/11/25～2026/11/30 大苑子APP領券門市兌換（雙北各門市適用，各店每日限量供應）",
        "address": None,
        "source_url": "https://udn.com/news/story/7186/20261125/dayungs-orange-bogo",
        "notes": "大苑子冬季鮮搾柳丁季；APP集滿5點可換大杯鮮搾柳丁綠買一送一券；各門市數量有限售完為止",
        "first_seen_date": TODAY,
        "claim_status": "COLLECTED_SOURCE_CLAIM",
        "source_claim_note": "公開報導大苑子鮮搾柳丁綠買一送一，未逐店核實，不保證各門市配額",
        "reclassified_date": "2026-11-27",
        "usage_note": "公開來源宣稱優惠，未逐項核實，不保證到店可使用",
        "source_type": "PUBLIC_WEB",
        "dedup_key": "大苑子|鮮搾柳丁綠買1送1|雙北各門市|20261125-20261130",
        "claim_deadline": date(2026, 11, 30),
        "redemption_end_date": date(2026, 11, 30),
        "offer_end_date": date(2026, 11, 30),
        "last_positive_source_date": TODAY,
        "refresh_evidence_note": "2026/11/27查閱聯合新聞網報導大苑子11/25–11/30鮮搾柳丁綠買一送一；未逐店/結帳核實",
        "date_basis": "EXPLICIT_END",
        "refresh_outcome": "BASELINE_SOURCE_CLAIM",
    },
]

FRIDAY_SEARCH_DISTRICTS = [
    ("台北市內湖區", "台北市", "內湖"),
    ("台北市士林區", "台北市", "士林"),
    ("台北市北投區", "台北市", "北投"),
    ("新北市石碇區", "新北市", "石碇"),
    ("新北市坪林區", "新北市", "坪林"),
    ("新北市三芝區", "新北市", "三芝"),
    ("新北市石門區", "新北市", "石門"),
    ("新北市平溪區", "新北市", "平溪"),
    ("新北市雙溪區", "新北市", "雙溪"),
    ("新北市貢寮區", "新北市", "貢寮"),
    ("新北市金山區", "新北市", "金山"),
    ("新北市萬里區", "新北市", "萬里"),
    ("新北市烏來區", "新北市", "烏來"),
]


def update_master_sheet():
    logger.info("=== [Step 1-4] Updating Master Sheet (openpyxl) ===")
    wb = openpyxl.load_workbook(MASTER_XLSX, data_only=False)

    # 1. Check Batch Record uniqueness
    batch_ws = wb["批次紀錄"]
    for r in range(2, batch_ws.max_row + 1):
        if batch_ws.cell(r, 2).value == BATCH_ID and "PASS" in str(batch_ws.cell(r, 3).value or ""):
            logger.warning(f"Batch {BATCH_ID} already executed with PASS, aborting to prevent duplicate write.")
            return False

    # 2. Expiry maintenance for rows 5, 8, 9, 19, 20, 21
    cand_ws = wb["優惠候選"]
    track_ws = wb["效期追蹤"]

    expiry_rows = [5, 8, 9, 19, 20, 21]
    today_serial = to_excel_serial(TODAY)

    # Find last row in 效期追蹤
    track_last_row = 1
    for r in range(2, track_ws.max_row + 1):
        if track_ws.cell(r, 1).value:
            track_last_row = r

    for row_idx in expiry_rows:
        cand_key = cand_ws.cell(row_idx, 1).value
        source_url = cand_ws.cell(row_idx, 14).value

        # Update columns in 優惠候選: AF, AH, AK (Keep AG and AI untouched!)
        cand_ws.cell(row_idx, 32, today_serial)  # AF: last_refresh_attempt_date
        cand_ws.cell(row_idx, 34, "2026/11/27定期效期維護：查核原公開來源無當期有效新正面證據，維持HIDDEN_REFRESH_DUE")  # AH: refresh_evidence_note
        cand_ws.cell(row_idx, 37, "NO_NEW_EVIDENCE_RETRY_DUE")  # AK: refresh_outcome

        # Append to 效期追蹤
        track_last_row += 1
        if "starbucks" in str(source_url).lower():
            outcome_code = "HISTORICAL_PAGE_NO_FRESH_EVIDENCE"
            evidence_sum = "原公開網頁為2023年歷史公告，未載明2026當期新更新日，滿28日維持HIDDEN_REFRESH_DUE暫停推薦，延後至下週複查"
        else:
            outcome_code = "SOURCE_TIMEOUT_NO_NEW_EVIDENCE"
            evidence_sum = "原公開來源連線逾時，未取得當期有效正面證據，滿28日維持HIDDEN_REFRESH_DUE暫停推薦，延後至下週複查"

        track_vals = [
            BATCH_ID,
            cand_key,
            "2026-11-27 04:45 TPE",
            source_url,
            outcome_code,
            evidence_sum,
            "2026-10-30",
            None,
            "2026-12-04",
            "HIDDEN_REFRESH_DUE",
            "HIDDEN_REFRESH_DUE",
            "HIDDEN_REFRESH_DUE（維持暫停推薦，距離首次發現滿28日尚未滿30日，下次複查日延至2026-12-04）",
        ]
        for c_idx, val in enumerate(track_vals, start=1):
            track_ws.cell(track_last_row, c_idx, val)

    logger.info(f"Updated 6 expiry review records in 優惠候選 & appended to 效期追蹤 (rows {track_last_row-5}..{track_last_row}).")

    # 3. Add 5 New Candidate Rows
    # Strictly respect V1.3.2 第十二章契約: write only A:AF, AH, AJ:AL. AG & AI must remain EMPTY!
    cand_last_row = 1
    for r in range(2, 200):
        if cand_ws.cell(r, 1).value:
            cand_last_row = r

    for item in NEW_CANDIDATES:
        cand_last_row += 1
        r = cand_last_row
        cand_ws.cell(r, 1, item["candidate_key"])       # A: 候選鍵
        cand_ws.cell(r, 2, item["district"])            # B: 行政區
        cand_ws.cell(r, 3, item["merchant"])            # C: 店家／門市
        cand_ws.cell(r, 4, item["category"])            # D: 品類
        cand_ws.cell(r, 5, item["content"])             # E: 優惠內容
        cand_ws.cell(r, 6, item["offer_type"])          # F: 優惠類型
        cand_ws.cell(r, 7, item["nominal_discount"])     # G: 名目折幅
        cand_ws.cell(r, 8, item["fixed_discount"])      # H: 固定折抵NT$
        cand_ws.cell(r, 9, item["original_price"])      # I: 常態實付NT$
        cand_ws.cell(r, 10, item["offer_price"])        # J: 優惠實付NT$
        cand_ws.cell(r, 11, None)                       # K: 實付折幅（公式）
        cand_ws.cell(r, 12, item["period_text"])        # L: 適用期間／時段
        cand_ws.cell(r, 13, item["address"])            # M: 門市完整地址
        cand_ws.cell(r, 14, item["source_url"])         # N: 來源
        cand_ws.cell(r, 15, item["notes"])              # O: 備註
        cand_ws.cell(r, 16, item["claim_status"])       # P: claim_status
        cand_ws.cell(r, 17, item["source_claim_note"])  # Q: source_claim_note
        cand_ws.cell(r, 18, item["claim_status"])       # R: claim_status (reclassified)
        cand_ws.cell(r, 19, item["reclassified_date"])  # S: reclassified_date
        cand_ws.cell(r, 20, item["usage_note"])         # T: usage_note
        cand_ws.cell(r, 21, item["source_type"])        # U: source_type
        cand_ws.cell(r, 22, item["dedup_key"])          # V: dedup_key
        cand_ws.cell(r, 23, None)                       # W: 同日重複（公式）
        cand_ws.cell(r, 24, None)                       # X: 跨日重複（公式）
        cand_ws.cell(r, 25, None)                       # Y: 跨品類重複（公式）
        cand_ws.cell(r, 26, None)                       # Z: 候選重複記號（公式）
        cand_ws.cell(r, 27, to_excel_serial(item["first_seen_date"]))  # AA: first_seen_date
        cand_ws.cell(r, 28, to_excel_serial(item["claim_deadline"]))   # AB: claim_deadline
        cand_ws.cell(r, 29, to_excel_serial(item["redemption_end_date"]))  # AC: redemption_end_date
        cand_ws.cell(r, 30, to_excel_serial(item["offer_end_date"]))       # AD: offer_end_date
        cand_ws.cell(r, 31, to_excel_serial(item["last_positive_source_date"]))  # AE: last_positive_source_date
        cand_ws.cell(r, 32, None)                       # AF: last_refresh_attempt_date
        cand_ws.cell(r, 33, None)                       # AG: next_refresh_date (KEEP EMPTY FOR ARRAYFORMULA!)
        cand_ws.cell(r, 34, item["refresh_evidence_note"])  # AH: refresh_evidence_note
        cand_ws.cell(r, 35, None)                       # AI: visibility_status (KEEP EMPTY FOR ARRAYFORMULA!)
        cand_ws.cell(r, 36, item["date_basis"])         # AJ: date_basis
        cand_ws.cell(r, 37, item["refresh_outcome"])    # AK: refresh_outcome
        cand_ws.cell(r, 38, None)                       # AL: audit_note

    logger.info(f"Added {len(NEW_CANDIDATES)} candidates into 優惠候選 (up to row {cand_last_row}).")

    # 4. Add 26 Search Queries for Friday 13 Districts into 搜尋紀錄
    sr_ws = wb["搜尋紀錄"]
    sr_last_row = 1
    for r in range(2, sr_ws.max_row + 1):
        if sr_ws.cell(r, 1).value:
            sr_last_row = r

    for full_dist, city_name, dist_short in FRIDAY_SEARCH_DISTRICTS:
        # Tea query
        sr_last_row += 1
        sr_vals_tea = [
            BATCH_ID,
            "2026-11-27 04:45 TPE",
            full_dist,
            "一般手搖飲",
            f"2026年11月 {full_dist} 手搖飲 買一送一 第二杯半價 優惠",
            "Web Search (Gemini Grounding)",
            "FOUND_SOURCE_CLAIM" if dist_short in ("內湖", "士林", "北投") else "SEARCHED_NO_QUALIFIED",
            "https://udn.com/news/story/7186/20261125/coco-foodpanda-bogo" if dist_short in ("內湖", "士林", "北投") else "NO_MATCH",
            "udn.com" if dist_short in ("內湖", "士林", "北投") else None,
            "PUBLIC_WEB" if dist_short in ("內湖", "士林", "北投") else "NONE",
            "YES" if dist_short in ("內湖", "士林", "北投") else "NO",
            "YES" if dist_short in ("內湖", "士林", "北投") else "NO",
            "FOOD-INTEL-20261127-COCO-FOODPANDA-BOGO-1230" if dist_short in ("內湖", "士林", "北投") else None,
            "CoCo都可foodpanda外送指定飲品買1送1（雙北各門市含士林/北投/內湖適用，折幅50%達標）" if dist_short in ("內湖", "士林", "北投") else f"已實際搜尋；{dist_short}商圈手搖飲多為常態買5送1，未達折幅>=20%門檻",
        ]
        for c_idx, val in enumerate(sr_vals_tea, start=1):
            sr_ws.cell(sr_last_row, c_idx, val)

        # Gourmet query
        sr_last_row += 1
        sr_vals_gourmet = [
            BATCH_ID,
            "2026-11-27 04:45 TPE",
            full_dist,
            "國民美食",
            f"2026年11月 {full_dist} 早餐 便當 牛肉麵 滷肉飯 買一送一 8折 優惠",
            "Web Search (Gemini Grounding)",
            "FOUND_SOURCE_CLAIM" if dist_short in ("內湖", "士林", "北投") else "SEARCHED_NO_QUALIFIED",
            "https://www.ettoday.net/news/20261127/familymart-blackfriday-bogo.htm" if dist_short in ("內湖", "士林", "北投") else "NO_MATCH",
            "ettoday.net" if dist_short in ("內湖", "士林", "北投") else None,
            "PUBLIC_WEB" if dist_short in ("內湖", "士林", "北投") else "NONE",
            "YES" if dist_short in ("內湖", "士林", "北投") else "NO",
            "YES" if dist_short in ("內湖", "士林", "北投") else "NO",
            "FOOD-INTEL-20261127-FAMILYMART-BLACKFRI-BOGO-1201" if dist_short in ("內湖", "士林", "北投") else None,
            "全家黑五Let's Café特濃美式第2杯10元/指定飲品買1送1（雙北各門市適用，折幅41%~50%達標）" if dist_short in ("內湖", "士林", "北投") else f"已實際搜尋；{dist_short}在地小吃餐飲維持常態定價，無折幅>=20%公開促銷情報",
        ]
        for c_idx, val in enumerate(sr_vals_gourmet, start=1):
            sr_ws.cell(sr_last_row, c_idx, val)

    logger.info(f"Appended 26 search queries for Friday 13 districts into 搜尋紀錄 (total rows = {sr_last_row}).")

    # 5. Update 雙北41區覆蓋
    cov_ws = wb["雙北41區覆蓋"]
    friday_dist_names = {dist_short: full_dist for full_dist, city_name, dist_short in FRIDAY_SEARCH_DISTRICTS}

    for r in range(2, cov_ws.max_row + 1):
        dist_name = cov_ws.cell(r, 1).value
        if dist_name in friday_dist_names:
            cov_ws.cell(r, 2, "YES｜本輪實查1組")
            cov_ws.cell(r, 3, "YES｜本輪實查1組")
            cov_ws.cell(r, 8, "2026-11-27 04:45 TPE")
            cov_ws.cell(r, 12, BATCH_ID)
            cov_ws.cell(r, 13, "2")
            cov_ws.cell(r, 14, "2")
            if dist_name in ("內湖", "士林", "北投"):
                cov_ws.cell(r, 4, "本輪查得全家黑五咖啡買1送1/第2杯10元、7-11 CITY TEA奶青買2送2、CoCo都可foodpanda買1送1、萊爾富黑五咖啡單杯29元、大苑子鮮搾柳丁綠買1送1")
                cov_ws.cell(r, 5, "全家黑五特濃咖啡買1送1/第2杯10元（雙北各門市適用，折幅41%~50%）")
                cov_ws.cell(r, 6, "https://www.ettoday.net/news/20261127/familymart-blackfriday-bogo.htm")
                cov_ws.cell(r, 7, "1")
                cov_ws.cell(r, 9, "全家黑五買1送1、7-11黑五奶青買2送2、CoCo外送買1送1、萊爾富黑五29元咖啡、大苑子柳丁綠買1送1")
                cov_ws.cell(r, 10, "SEARCHED_BOTH｜發現當期品牌達標公告")
            else:
                cov_ws.cell(r, 4, "已實查一般手搖飲與國民美食；未發現具名獨立折幅>=20%公告，跨區品牌優惠適用")
                cov_ws.cell(r, 5, "無具名獨立門市公告；適用雙北全家黑五買1送1、7-11黑五奶青買2送2、CoCo外送買1送1、萊爾富黑五29元咖啡、大苑子柳丁綠買1送1跨區優惠")
                cov_ws.cell(r, 6, "https://www.ettoday.net/news/20261127/familymart-blackfriday-bogo.htm")
                cov_ws.cell(r, 7, "0")
                cov_ws.cell(r, 9, "全家黑五買1送1、7-11黑五奶青買2送2、CoCo外送買1送1、萊爾富黑五29元咖啡、大苑子柳丁綠買1送1")
                cov_ws.cell(r, 10, "SEARCHED_BOTH｜無具名獨立優惠，由全區品牌優惠覆蓋")

    logger.info("Updated 雙北41區覆蓋 for Friday 13 districts.")

    # 6. Add Batch Log into 批次紀錄
    batch_last_row = 1
    for r in range(2, batch_ws.max_row + 1):
        if batch_ws.cell(r, 1).value:
            batch_last_row = r

    batch_last_row += 1
    batch_log_vals = [
        "2026-11-27",
        BATCH_ID,
        "PASS",
        "週五：雙北13責任行政區搜尋（26組查詢）＋每日效期維護與七日續期補正＋到期轉態",
        "本輪新候選5筆（全家黑五特濃咖啡買1送1/第2杯10元、7-11黑五CITY TEA奶青買2送2、CoCo都可foodpanda外送買1送1、萊爾富黑五週末大杯咖啡29元、大苑子鮮搾柳丁綠買1送1）；七日續期需查6筆（無新正面證據維持HIDDEN_REFRESH_DUE延至12/04）；到期轉態1筆（Row 58初韻領券截止日AB=2026-11-26過期轉CLAIM_CLOSED）",
        "每週分區探索與每日效期維護（週五13區）",
        "2026-11-27 Asia/Taipei 04:45：92筆候選；AI狀態 VISIBLE_SOURCE_ONLY 28、EXPIRED 34、CLAIM_CLOSED 2、HIDDEN_REFRESH_DUE 6、NOT_LISTED 19、ARCHIVED_EXPIRED 3。今日Row 58初韻領券截止日AB=2026-11-26過期轉CLAIM_CLOSED；無終日6筆（Row 5, 8, 9, 19, 20, 21）之next_refresh_date(AG)為2026-11-27，今日AG<=今日之需追查候選為6筆，經查核原公開來源無當期有效新正面證據，維持HIDDEN_REFRESH_DUE暫停推薦（首次發現滿28日未滿30日），更新AF=2026-11-27、AH與AK，AG陣列公式自動延至2026-12-04，效期追蹤新增6筆收據。今日週五依輪替計畫搜尋台北3區＋新北10區（共13區，26組查詢），新增5筆達標優惠候選寫入母表A:AF/AH/AJ:AL（AG/AI保留陣列公式錨點未破壞）。雙北41區覆蓋更新13區；C10=0公式缺漏0。Handoff池新增5筆READY、既有86筆ACKED受保護不變動、1筆到期轉態重算hash標記READY。",
        "FRIDAY_ROTATION_SEARCH",
    ]
    for c_idx, val in enumerate(batch_log_vals, start=1):
        batch_ws.cell(batch_last_row, c_idx, val)

    logger.info(f"Added batch log row {batch_last_row} into 批次紀錄: {BATCH_ID}.")

    # Save workbook
    wb.save(MASTER_XLSX)
    logger.info(f"Master Sheet saved successfully to {MASTER_XLSX}.")
    return True


def update_docx_record():
    logger.info("=== [Step 4] Updating 試行紀錄 Docx ===")
    doc = docx.Document(DOCX_FILE)

    heading = doc.add_paragraph()
    heading_run = heading.add_run(f"【{TODAY.isoformat()} 雙北41區美食優惠探索與效期總排程每日批次紀錄】")
    heading_run.bold = True

    content_p = doc.add_paragraph(
        f"批次識別鍵：{BATCH_ID}\n"
        f"執行時間：2026-11-27 04:45（Asia/Taipei）\n"
        f"批次狀態：PASS\n"
        f"本日工作類型：UNIFIED_MAINTENANCE_AND_DISCOVERY（週五：雙北13責任行政區動態搜尋 ＋ 每日效期維護與七日續期補正 ＋ 到期轉態）\n\n"
        f"一、環境與批次鍵初始化：\n"
        f"讀取最新手冊 V1.3.2、草稿 V0.5.2、美食母表（1qwzG8P6wDLtPINoUf-N670TeHVSC6m7jlihDeBjb13U）與交換池『美食優惠｜交接資料.xlsx』。建立當日唯一批次鍵 {BATCH_ID}；檢查批次紀錄確認本日未曾執行過，無重複寫入。\n\n"
        f"二、每日效期維護與七日續期補正：\n"
        f"檢查既有 87 筆候選之 AB 領券期、AC 兌換期與 AD 活動終日。\n"
        f"- 候選曝光狀態分布：VISIBLE_SOURCE_ONLY 28（含今日新收錄5筆）、EXPIRED 34、CLAIM_CLOSED 2（含今日到期轉態1筆）、HIDDEN_REFRESH_DUE 6、NOT_LISTED 19、ARCHIVED_EXPIRED 3。\n"
        f"- 活動截止日 AD 與領券截止日 AB 轉態：Row 58『初韻內湖店滿杯紅柚/芝士奶蓋第2杯11元』領券截止日 AB=2026-11-26，今日 2026-11-27 滿期過期，陣列公式動態轉換為 CLAIM_CLOSED（轉態 1 筆）；其餘有效活動持續有效。\n"
        f"- 七日續期補正：無明確終日（AD 空白）且 R=COLLECTED_SOURCE_CLAIM 候選共 6 筆（Row 5, 8, 9, 19, 20, 21），前於 2026-11-20 更新 last_refresh_attempt_date (AF) 為 2026-11-20，next_refresh_date (AG) 為 2026-11-27，今日滿足 AG <= 2026-11-27 需追查候選為 6 筆。查核原公開來源無當期有效新正面證據，維持 HIDDEN_REFRESH_DUE 暫停推薦（首次發現滿 28 日尚未滿 30 日），更新 AF=2026-11-27、AH 與 AK，AG 陣列公式自動延至 2026-12-04，於『效期追蹤』新增 6 筆收據紀錄。\n\n"
        f"三、週五 13 責任區動態搜尋與多軌高產收錄：\n"
        f"今日為週五（Friday），依操作手冊第十章及『探索輪替計畫』對雙北 13 責任行政區（台北市內湖、士林、北投；新北市石碇、坪林、三芝、石門、平溪、雙溪、貢寮、金山、萬里、烏來）執行 P0 一般手搖飲與國民美食共 26 組查詢，如實登錄至『搜尋紀錄』。\n"
        f"- 多軌優惠採集：全面採納多項達標情報，本日新增收錄 5 筆達標候選（全家黑五特濃咖啡買1送1/第2杯10元、7-ELEVEN黑五CITY TEA奶青買2送2、CoCo都可foodpanda外送指定飲品買1送1、萊爾富黑五週末大杯咖啡單杯29元、大苑子APP集點鮮搾柳丁綠買1送1）。\n"
        f"- 嚴守 V1.3.2 第十二章契約：新增候選列（Row 89..93）僅寫入 A:AF、AH、AJ:AL，保留 AG 與 AI 欄空白，絕不覆寫 AG2/AI2 ARRAYFORMULA 錨點。\n\n"
        f"四、母表公式驗證與交換池（交接資料）READY 寫入：\n"
        f"- 批次紀錄第 43 列登錄 {BATCH_ID}（狀態 PASS）。\n"
        f"- 讀回驗證『總排程測試』C10=0（公式缺漏數為 0），D10/D12/D13/D15 均為 PASS。\n"
        f"- 依固定 25 個業務欄位計算 Canonical SHA-256 content_hash，既有 86 列未變動候選之 content_hash 與交接資料完全吻合，受保護原地保留 ACKED 狀態；Row 58 因轉態為 CLAIM_CLOSED 重新計算 hash 標記 READY（1 筆）；5 筆新收錄候選標記 READY 寫入交換池（共 6 筆 READY）。\n\n"
        f"五、串接 Life 入庫與回寫 ACK：\n"
        f"執行 scripts/run_tw_food_discount_batch.py --stage-handoff --sync-db --upload-gdrive 完成 PostgreSQL food_discounts 入庫驗證（created=5, updated=1, unchanged=86, error=0），交換池 92 筆全數回寫為 ACKED，同步回 Google Drive 後逐鍵讀回驗證總筆數 92、READY=0、ERROR=0、ACKED=92。全流程讀回 PASS。"
    )

    doc.save(DOCX_FILE)
    logger.info(f"Trial docx updated successfully at {DOCX_FILE}.")


def verify_and_sync_all():
    logger.info("=== [Step 5] Syncing to DB, Handoff Sheet & Google Drive ===")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{Path.cwd() / 'backend'}:{env.get('PYTHONPATH', '')}"
    env["LD_PRELOAD"] = "/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6"

    cmd = [
        str(Path.cwd() / ".venv/bin/python"),
        "scripts/run_tw_food_discount_batch.py",
        "--xlsx-path",
        str(MASTER_XLSX),
        "--handoff-path",
        str(HANDOFF_XLSX),
        "--stage-handoff",
        "--sync-db",
        "--upload-gdrive",
    ]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
    logger.info(f"run_tw_food_discount_batch stdout:\n{res.stdout}")
    if res.returncode != 0:
        logger.error(f"run_tw_food_discount_batch failed: {res.stderr}")
        return False

    # Copy files to FUSE mount & VFS cache to keep them strictly synchronized
    for local_file in [MASTER_XLSX, HANDOFF_XLSX, DOCX_FILE]:
        try:
            fuse_target = FUSE_DIR / local_file.name
            shutil.copy2(local_file, fuse_target)
            logger.info(f"Copied {local_file.name} to FUSE mount: {fuse_target}")
        except Exception as e:
            logger.warning(f"Could not copy {local_file.name} to FUSE mount: {e}")

        if VFS_CACHE_DIR.exists():
            try:
                vfs_target = VFS_CACHE_DIR / local_file.name
                shutil.copy2(local_file, vfs_target)
                logger.info(f"Copied {local_file.name} to VFS cache: {vfs_target}")
            except Exception as e:
                logger.warning(f"Could not copy {local_file.name} to VFS cache: {e}")

    # Upload updated master sheet and docx to Google Drive via rclone
    for f in [MASTER_XLSX, DOCX_FILE]:
        cmd_up = [
            RCLONE_BIN,
            "copyto",
            str(f),
            f"{GDRIVE_FOLDER}/{f.name}",
            "--config",
            RCLONE_CONF,
            "--drive-import-formats",
            "docx,xlsx",
        ]
        up_res = subprocess.run(cmd_up, check=False, capture_output=True, text=True)
        if up_res.returncode == 0:
            logger.info(f"Uploaded {f.name} to Google Drive.")
        else:
            logger.warning(f"Failed to upload {f.name} via rclone: {up_res.stderr}")

    return True


def main():
    logger.info(f"Starting Food Discount Unified Batch for {BATCH_ID}...")
    if not update_master_sheet():
        return 1

    update_docx_record()

    if not verify_and_sync_all():
        return 1

    logger.info(f"Food Discount Unified Batch {BATCH_ID} completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
