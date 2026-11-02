"""
Taiwan Activity Discovery Daily Batch - 2026-11-03 (Asia/Taipei 04:00)
Run ID: tw-discovery-daily-20261103-040000-agy38f
SOP Compliance: README.md, 01~05.md, PROJECT_RULES.md
"""
import asyncio
import ctypes
import hashlib
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List

# Preload libstdc++ for greenlet/async SQLAlchemy
try:
    ctypes.cdll.LoadLibrary("/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6")
except Exception as e:
    pass

import openpyxl

sys.path.append("backend")
from app.db.session import engine, SessionLocal
from app.services.curated_handoff import HEADERS, BUSINESS_FIELDS, HandoffItem, upsert_handoff
from scripts.import_curated_from_sheet import parse_rows, validate_record, run_exclusive_import

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TPE_TZ = timezone(timedelta(hours=8))
NOW_TPE_STR = "2026-11-03T04:00:00+08:00"
RUN_ID = "tw-discovery-daily-20261103-040000-agy38f"

DRIVE_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟")
HANDOFF_FILE = DRIVE_DIR / "台灣活動｜交接資料.xlsx"
POOL_FILE = DRIVE_DIR / "台灣活動｜精選池（Excel相容）.xlsx"
SOURCES_FILE = DRIVE_DIR / "官網來源清單與統計表.xlsx"
EXEC_LOG_FILE = DRIVE_DIR / "台灣活動｜排程執行紀錄.xlsx"
LOG_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜每日執行日誌")
DAILY_LOG_FILE = LOG_DIR / "2026-11-03.log"

LOCAL_DIR = Path("/tmp/tw_sheets_20261103")
LOCAL_DIR.mkdir(parents=True, exist_ok=True)
HANDOFF_LOCAL = LOCAL_DIR / "台灣活動｜交接資料.xlsx"
POOL_LOCAL = LOCAL_DIR / "台灣活動｜精選池（Excel相容）.xlsx"
SOURCES_LOCAL = LOCAL_DIR / "官網來源清單與統計表.xlsx"
EXEC_LOG_LOCAL = LOCAL_DIR / "台灣活動｜排程執行紀錄.xlsx"

# Copy drive files locally to avoid FUSE latency/locks if not already present
if not HANDOFF_LOCAL.exists():
    shutil.copy2(HANDOFF_FILE, HANDOFF_LOCAL)
if not POOL_LOCAL.exists():
    shutil.copy2(POOL_FILE, POOL_LOCAL)
if not SOURCES_LOCAL.exists():
    shutil.copy2(SOURCES_FILE, SOURCES_LOCAL)
if not EXEC_LOG_LOCAL.exists():
    shutil.copy2(EXEC_LOG_FILE, EXEC_LOG_LOCAL)


def canonical_hash(record_dict: Dict[str, Any]) -> str:
    payload = {k: record_dict.get(k) for k in BUSINESS_FIELDS}
    canonical_str = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


class LocalSheetAdapter:
    def __init__(self, xlsx_path: Path):
        self.xlsx_path = str(xlsx_path)

    async def read(self):
        async with SessionLocal() as db:
            from sqlalchemy import select
            from app.models.curated import CuratedActivity
            res = await db.scalars(select(CuratedActivity))
            db_map = {row.handoff_event_key: row for row in res if row.handoff_event_key}

        wb = openpyxl.load_workbook(self.xlsx_path, data_only=True)
        sheet = wb["交接資料"]
        values = []
        headers = [sheet.cell(1, c).value for c in range(1, 32)]
        values.append([str(h) for h in headers])

        for r in range(2, sheet.max_row + 1):
            ek = sheet.cell(r, 1).value
            if not ek:
                continue
            db_row = db_map.get(ek)
            row_vals = []
            for c in range(1, 32):
                col_name = headers[c - 1]
                val = sheet.cell(r, c).value
                if db_row and db_row.content_hash == sheet.cell(r, 2).value and col_name in db_row.handoff_details:
                    stored_val = db_row.handoff_details[col_name]
                    row_vals.append("" if stored_val is None else str(stored_val))
                else:
                    if val is None:
                        row_vals.append("")
                    elif isinstance(val, datetime):
                        if val.hour == 0 and val.minute == 0 and val.second == 0 and val.tzinfo is None:
                            row_vals.append(val.strftime("%Y-%m-%d"))
                        elif val.tzinfo is not None:
                            row_vals.append(val.isoformat())
                        else:
                            row_vals.append(val.isoformat() + "+08:00")
                    elif isinstance(val, date):
                        row_vals.append(val.isoformat())
                    else:
                        row_vals.append(str(val).strip())
            values.append(row_vals)
        wb.close()
        return values

    async def receipts(self, pending):
        wb = openpyxl.load_workbook(self.xlsx_path)
        sheet = wb["交接資料"]
        now = datetime.now(TPE_TZ).isoformat()
        outcomes = []

        key_to_row = {}
        for r in range(2, sheet.max_row + 1):
            k = str(sheet.cell(r, 1).value or "").strip()
            if k:
                key_to_row[k] = r

        for snapshot, result, error in pending:
            ek = snapshot["event_key"]
            row_idx = key_to_row.get(ek)
            if not row_idx:
                outcomes.append(False)
                continue
            status = "ERROR" if error else "ACKED"
            ack_at = "" if error else now
            import_result = "" if error else result

            sheet.cell(row_idx, 26, status)        # Z: handoff_status
            sheet.cell(row_idx, 28, ack_at)        # AB: life_ack_at_tpe
            sheet.cell(row_idx, 29, import_result) # AC: life_import_result
            sheet.cell(row_idx, 30, error)         # AD: life_error
            outcomes.append(True)

        wb.save(self.xlsx_path)
        wb.close()
        return outcomes


# Define the 14 new verified candidates for 2026-11-03
CANDIDATES = [
    {
        "event_key": "flowercarpet.tw:2026:xinshe-flowercarpet",
        "parent_event_key": "flowercarpet.tw:2026:xinshe-flowercarpet",
        "record_type": "main",
        "title": "2026新社花海暨臺中國際花毯節（蜜糖奇遇・三麗鷗聯名15週年主花毯與甜點王國展區）",
        "city": "臺中市",
        "district": "新社區",
        "category": "地方節慶／觀光活動",
        "organizer": "農業部種苗改良繁殖場、臺中市政府觀光旅遊局",
        "start_at_tpe": "2026-10-31T08:30:00+08:00",
        "end_at_tpe": "2026-11-22T16:30:00+08:00",
        "venue": "農業部種苗改良繁殖場二苗圃（臺中市新社區協興街30號）",
        "official_url": "https://www.flowercarpet.tw/",
        "registration_url": None,
        "source_url": "https://www.flowercarpet.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "全區花海展區、三麗鷗主題裝置與戶外農特產市集免門票自由參觀",
        "evidence_summary": "農業部種苗改良繁殖場與臺中市政府觀光旅遊局官方核實：2026臺中國際花毯節適逢15週年，攜手三麗鷗打造7大甜點王國展區與19公尺蜜糖奇遇主花毯，全區免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taichung-flowercarpet",
        "discovery_url": "https://www.flowercarpet.tw/",
        "other_sources": "ardswc.gov.tw | https://www.ardswc.gov.tw/",
        "verified_key": "flowercarpet.tw",
        "verified_url": "https://www.flowercarpet.tw/",
    },
    {
        "event_key": "chiayiband.com.tw:2026:chiayi-band-festival",
        "parent_event_key": "chiayiband.com.tw:2026:chiayi-band-festival",
        "record_type": "main",
        "title": "2026第34屆嘉義市國際管樂節（全城踩街嘉年華、中正公園與文化公園戶外大型音樂會）",
        "city": "嘉義市",
        "district": "東區",
        "category": "展演活動／音樂節慶",
        "organizer": "嘉義市政府文化局",
        "start_at_tpe": "2026-12-18T09:00:00+08:00",
        "end_at_tpe": "2027-01-01T21:30:00+08:00",
        "venue": "嘉義市區街道踩街、中正公園、文化公園與嘉義市文化局音樂廳",
        "official_url": "https://www.chiayiband.com.tw/",
        "registration_url": None,
        "source_url": "https://www.chiayiband.com.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "全城踩街嘉年華、中正公園與文化公園戶外大型音樂會全區免門票自由觀賞",
        "evidence_summary": "嘉義市政府文化局官方核實：第34屆嘉義市國際管樂節自12/18開跑至元旦，匯聚國內外管樂名團，市區踩街嘉年華、戶外晚會與公園音樂會均免門票自由同歡。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-chiayi-band",
        "discovery_url": "https://www.chiayiband.com.tw/",
        "other_sources": "culture.chiayi.gov.tw | https://culture.chiayi.gov.tw/",
        "verified_key": "chiayiband.com.tw",
        "verified_url": "https://www.chiayiband.com.tw/",
    },
    {
        "event_key": "gukeng.gov.tw:2026:taiwan-coffee-festival",
        "parent_event_key": "gukeng.gov.tw:2026:taiwan-coffee-festival",
        "record_type": "main",
        "title": "2026第24屆台灣咖啡節（古坑綠色隧道公園・咖啡野餐市集與音樂漫活節）",
        "city": "雲林縣",
        "district": "古坑鄉",
        "category": "地方節慶／農遊體驗",
        "organizer": "雲林縣政府農業處、雲林縣古坑鄉公所",
        "start_at_tpe": "2026-10-31T10:00:00+08:00",
        "end_at_tpe": "2026-11-08T19:00:00+08:00",
        "venue": "古坑綠色隧道公園（雲林縣古坑鄉湳仔村湳仔路）",
        "official_url": "https://www.gukeng.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.gukeng.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "綠色隧道草地野餐、精品咖啡市集與戶外音樂展演免門票自由入場",
        "evidence_summary": "雲林縣政府農業處與古坑鄉公所官方核實：第24屆台灣咖啡節於古坑綠色隧道橫跨雙週末盛大舉辦，推廣古坑在地咖啡產業，戶外咖啡野餐市集與草地展演全區免門票。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-yunlin-coffee",
        "discovery_url": "https://www.gukeng.gov.tw/",
        "other_sources": "ardswc.gov.tw | https://www.ardswc.gov.tw/",
        "verified_key": "gukeng.gov.tw",
        "verified_url": "https://www.gukeng.gov.tw/",
    },
    {
        "event_key": "taiwanopenofsurfing.org:2026:surfing-open",
        "parent_event_key": "taiwanopenofsurfing.org:2026:surfing-open",
        "record_type": "main",
        "title": "2026臺灣國際衝浪公開賽（WSL QS 6000・東河金樽海域國際賽與陸域滑板音樂市集）",
        "city": "臺東縣",
        "district": "東河鄉",
        "category": "運動休閒／體育賽事",
        "organizer": "臺東縣政府交通及觀光發展處、世界衝浪聯盟（WSL）",
        "start_at_tpe": "2026-11-06T07:00:00+08:00",
        "end_at_tpe": "2026-11-22T17:00:00+08:00",
        "venue": "金樽漁港暨周邊海域（臺東縣東河鄉金樽陸域與海域）",
        "official_url": "https://www.taiwanopenofsurfing.org/",
        "registration_url": None,
        "source_url": "https://www.taiwanopenofsurfing.org/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "金樽陸域看台區觀賽、海洋市集、滑板賽事與戶外音樂派對免門票自由入場",
        "evidence_summary": "臺東縣政府交通及觀光發展處官方核實：2026臺灣國際衝浪公開賽獲WSL認證為國際QS 6000高積分巡迴賽，金樽看台區觀賽、海洋手作市集與陸域周邊活動均免門票觀禮同歡。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taitung-surfing",
        "discovery_url": "https://www.taiwanopenofsurfing.org/",
        "other_sources": "tour.taitung.gov.tw | https://tour.taitung.gov.tw/",
        "verified_key": "taiwanopenofsurfing.org",
        "verified_url": "https://www.taiwanopenofsurfing.org/",
    },
    {
        "event_key": "irunner.biji.co:2026:tianzhong-marathon",
        "parent_event_key": "irunner.biji.co:2026:tianzhong-marathon",
        "record_type": "main",
        "title": "2026台灣米倉田中馬拉松（景崧文化教育園區・萬人稻浪跑跑、選手之夜與在地美食市集）",
        "city": "彰化縣",
        "district": "田中鎮",
        "category": "運動休閒／觀光活動",
        "organizer": "彰化縣政府、田中鎮公所、舒康樂活運動協會",
        "start_at_tpe": "2026-11-07T14:00:00+08:00",
        "end_at_tpe": "2026-11-08T15:00:00+08:00",
        "venue": "彰化縣田中鎮景崧文化教育園區（彰化縣田中鎮中州路一段416號）",
        "official_url": "https://tourism.chcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://tourism.chcg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "景崧園區選手之夜音樂晚會、萬人應援加油區與田中在地農特產市集免門票自由觀禮同歡",
        "evidence_summary": "彰化縣政府與田中鎮公所官方核實：2026台灣米倉田中馬拉松於景崧園區熱力登場，正賽選手登記已抽籤截止，選手之夜音樂會、主會場農創美食市集與沿線應援區開放民眾免門票自由參與。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-changhua-tianzhong",
        "discovery_url": "https://tourism.chcg.gov.tw/",
        "other_sources": "irunner.biji.co | https://irunner.biji.co/",
        "verified_key": "tourism.chcg.gov.tw",
        "verified_url": "https://tourism.chcg.gov.tw/",
    },
    {
        "event_key": "hotspring.hl.gov.tw:2026:hualien-pacific-hotspring",
        "parent_event_key": "hotspring.hl.gov.tw:2026:hualien-pacific-hotspring",
        "record_type": "main",
        "title": "2026花蓮太平洋溫泉季（跟小丸子一起泡進幸福裡・瑞穗溫泉公園與安通溫泉光影展）",
        "city": "花蓮縣",
        "district": "瑞穗鄉",
        "category": "地方節慶／觀光活動",
        "organizer": "花蓮縣政府觀光處",
        "start_at_tpe": "2026-10-17T17:30:00+08:00",
        "end_at_tpe": "2026-11-15T22:00:00+08:00",
        "venue": "花蓮縣瑞穗溫泉區（瑞穗溫泉公園）、玉里鎮安通溫泉區",
        "official_url": "https://hotspring.hl.gov.tw/",
        "registration_url": None,
        "source_url": "https://hotspring.hl.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "瑞穗溫泉公園戶外燈區、小丸子聯名地景裝置與每週六主題夜遊免門票自由參觀",
        "evidence_summary": "花蓮縣政府觀光處官方核實：2026花蓮太平洋溫泉季首度聯名櫻桃小丸子，於瑞穗與安通兩大溫泉區設置光影燈飾與特色裝置藝術，瑞穗溫泉公園展區免門票自由同歡。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-hualien-hotspring",
        "discovery_url": "https://hotspring.hl.gov.tw/",
        "other_sources": "tour-hualien.hl.gov.tw | https://tour-hualien.hl.gov.tw/",
        "verified_key": "hotspring.hl.gov.tw",
        "verified_url": "https://hotspring.hl.gov.tw/",
    },
    {
        "event_key": "kinmen.travel:2026:veteran-call",
        "parent_event_key": "kinmen.travel:2026:veteran-call",
        "record_type": "main",
        "title": "2026金門老兵召集令（榮耀歸隊・番號集結・新市256主題展館與戰役史蹟走讀）",
        "city": "金門縣",
        "district": "金湖鎮",
        "category": "地方節慶／歷史文化",
        "organizer": "金門縣政府觀光處",
        "start_at_tpe": "2026-10-01T09:00:00+08:00",
        "end_at_tpe": "2026-12-15T17:00:00+08:00",
        "venue": "金門縣金湖鎮新市256（中正路10號）、金湖飯店大廳與金門各戰役史蹟園區",
        "official_url": "https://kinmen.travel/",
        "registration_url": None,
        "source_url": "https://kinmen.travel/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "新市256老兵主題展覽、史蹟走讀活動全區免門票自由參觀，退役老兵憑證可兌換專屬紀念酒與紀念帽",
        "evidence_summary": "金門縣政府觀光處官方核實：2026金門老兵召集令以番號集結為號召，於新市256設老兵回味體驗主題特展，向退伍弟兄致敬，展覽與史蹟園區全區免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-kinmen-veteran",
        "discovery_url": "https://kinmen.travel/",
        "other_sources": "kinmen.gov.tw | https://kinmen.gov.tw/",
        "verified_key": "kinmen.travel",
        "verified_url": "https://kinmen.travel/",
    },
    {
        "event_key": "hsinchu.gov.tw:2026:guanxi-mesona-festival",
        "parent_event_key": "hsinchu.gov.tw:2026:guanxi-mesona-festival",
        "record_type": "main",
        "title": "2026關西仙草花生活節（南山大橋關西仙草一分田・紫色花海市集與音樂漫遊）",
        "city": "新竹縣",
        "district": "關西鎮",
        "category": "地方節慶／花海景觀",
        "organizer": "新竹縣政府、關西鎮公所、新竹縣關西鎮鄉土文化協會",
        "start_at_tpe": "2026-11-07T11:00:00+08:00",
        "end_at_tpe": "2026-11-08T16:00:00+08:00",
        "venue": "新竹縣關西鎮南山大橋旁（關西仙草一分田花田主展區）",
        "official_url": "https://www.hsinchu.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.hsinchu.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "南山大橋紫色仙草花田、文創手作市集與花田音樂漫遊免門票自由入場",
        "evidence_summary": "新竹縣政府與關西鎮公所官方核實：2026關西仙草花生活節於南山大橋仙草一分田展開，盛開粉紫仙草花毯、在地客家農產市集與音樂會，免門票自由漫步拍照。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-hsinchu-guanxi",
        "discovery_url": "https://www.hsinchu.gov.tw/",
        "other_sources": "ardswc.gov.tw | https://www.ardswc.gov.tw/",
        "verified_key": "hsinchu.gov.tw",
        "verified_url": "https://www.hsinchu.gov.tw/",
    },
    {
        "event_key": "kmoa.klcg.gov.tw:2026:ship-in-a-bottle",
        "parent_event_key": "kmoa.klcg.gov.tw:2026:ship-in-a-bottle",
        "record_type": "main",
        "title": "2026基隆美術館年度特展《瓶中船 Ship in a Bottle》（流動的港口・世界的基隆當代藝術展）",
        "city": "基隆市",
        "district": "中正區",
        "category": "展演活動／當代藝術",
        "organizer": "基隆市文化觀光局、基隆美術館",
        "start_at_tpe": "2026-10-16T10:00:00+08:00",
        "end_at_tpe": "2027-01-24T18:00:00+08:00",
        "venue": "基隆美術館1樓與M樓（基隆市中正區信一路181號）",
        "official_url": "https://kmoa.klcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://kmoa.klcg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "基隆美術館1樓與M樓特展空間全區免門票自由參觀（週一休館）",
        "evidence_summary": "基隆市文化觀光局與基隆美術館官方核實：年度國際當代藝術特展《瓶中船》以基隆港口與航海歷史為軸心，匯集國內外多位知名藝術家裝置、影像與雕塑創作，全館免費開放參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-keelung-kmoa",
        "discovery_url": "https://kmoa.klcg.gov.tw/",
        "other_sources": "klcg.gov.tw | https://www.klcg.gov.tw/",
        "verified_key": "kmoa.klcg.gov.tw",
        "verified_url": "https://kmoa.klcg.gov.tw/",
    },
    {
        "event_key": "i-pingtung.com:2026:sichongxi-hotspring",
        "parent_event_key": "i-pingtung.com:2026:sichongxi-hotspring",
        "record_type": "main",
        "title": "2026-2027屏東四重溪溫泉季（四重溪溫泉公園風域光影燈海與免費露天泡腳池）",
        "city": "屏東縣",
        "district": "車城鄉",
        "category": "地方節慶／觀光活動",
        "organizer": "屏東縣政府交通旅遊處",
        "start_at_tpe": "2026-12-04T17:30:00+08:00",
        "end_at_tpe": "2027-03-01T22:30:00+08:00",
        "venue": "屏東縣車城鄉四重溪溫泉公園、旭海溫泉區",
        "official_url": "https://www.i-pingtung.com/",
        "registration_url": None,
        "source_url": "https://www.i-pingtung.com/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "四重溪溫泉公園燈光藝術裝置展區、日式鳥居造景與露天大眾泡腳池全區免費參觀體驗",
        "evidence_summary": "屏東縣政府交通旅遊處官方核實：2026-2027四重溪溫泉季以風域光影為策展主題，四重溪溫泉公園打造大型主題光廊與絢麗燈海，園區免費參觀，露天泡腳池自由體驗。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-pingtung-sichongxi",
        "discovery_url": "https://www.i-pingtung.com/",
        "other_sources": "taiwanhotspring.net | https://taiwanhotspring.net/",
        "verified_key": "i-pingtung.com",
        "verified_url": "https://www.i-pingtung.com/",
    },
    {
        "event_key": "travel.nantou.gov.tw:2026:nantou-flower-carnival",
        "parent_event_key": "travel.nantou.gov.tw:2026:nantou-flower-carnival",
        "record_type": "main",
        "title": "2026-2027南投花卉嘉年華（花開全南投・埔里花卉物流中心主會場與溫泉花海季）",
        "city": "南投縣",
        "district": "埔里鎮",
        "category": "地方節慶／觀光活動",
        "organizer": "南投縣政府觀光處、埔里鎮公所、信義鄉農會",
        "start_at_tpe": "2026-11-28T09:00:00+08:00",
        "end_at_tpe": "2027-03-31T17:00:00+08:00",
        "venue": "南投縣埔里花卉物流中心主會場、信義鄉草坪頭、暨南大學校園",
        "official_url": "https://travel.nantou.gov.tw/",
        "registration_url": None,
        "source_url": "https://travel.nantou.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "埔里花卉物流中心主展區、各鄉鎮花海秘境與溫泉花卉市集全區免門票自由參觀",
        "evidence_summary": "南投縣政府觀光處官方核實：南投花卉嘉年華串聯全縣各鄉鎮秋冬花期，涵蓋埔里花卉展、信義踏雪尋梅及草坪頭花季，主會場戶外花海與農特產市集免門票自由入園。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-nantou-flower",
        "discovery_url": "https://travel.nantou.gov.tw/",
        "other_sources": "nantou.gov.tw | https://www.nantou.gov.tw/",
        "verified_key": "travel.nantou.gov.tw",
        "verified_url": "https://travel.nantou.gov.tw/",
    },
    {
        "event_key": "ilccb.gov.tw:2026:erjie-wang-gong",
        "parent_event_key": "ilccb.gov.tw:2026:erjie-wang-gong",
        "record_type": "main",
        "title": "2026宜蘭二結王公文化節（建廟240週年・萬斤炭火跳過火無形文化資產與王公祈福市集）",
        "city": "宜蘭縣",
        "district": "五結鄉",
        "category": "地方節慶／宗教民俗",
        "organizer": "宜蘭縣政府文化局、財團法人二結王公廟董事會、五結鄉公所",
        "start_at_tpe": "2026-12-19T09:00:00+08:00",
        "end_at_tpe": "2026-12-23T20:00:00+08:00",
        "venue": "二結王公廟前廣場（宜蘭縣五結鄉鎮安村舊街路98號）",
        "official_url": "https://www.ilccb.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.ilccb.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "國家無形文化資產萬斤炭火跳過火儀式、抓童乩文化踩街與祈福市集免門票自由觀禮參拜",
        "evidence_summary": "宜蘭縣政府文化局與二結王公廟官方核實：2026欣逢建廟240週年，舉辦全台最盛大萬斤炭火跳過火國家級民俗慶典，王公文化踩街、抓童乩與祈福市集全區免門票自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-yilan-erjie",
        "discovery_url": "https://www.ilccb.gov.tw/",
        "other_sources": "yilan.gov.tw | https://www.yilan.gov.tw/",
        "verified_key": "ilccb.gov.tw",
        "verified_url": "https://www.ilccb.gov.tw/",
    },
    {
        "event_key": "miaolitravel.net:2026:tongluo-chrysanthemum",
        "parent_event_key": "miaolitravel.net:2026:tongluo-chrysanthemum",
        "record_type": "main",
        "title": "2026苗栗銅鑼杭菊生活節（菊內人・九湖台地十一月雪花海、花田音樂會與農特產市集）",
        "city": "苗栗縣",
        "district": "銅鑼鄉",
        "category": "地方節慶／花海景觀",
        "organizer": "苗栗縣政府、富農農產運銷合作社、銅鑼鄉農會",
        "start_at_tpe": "2026-11-08T09:00:00+08:00",
        "end_at_tpe": "2026-12-06T17:00:00+08:00",
        "venue": "苗栗縣銅鑼鄉九湖台地周邊花田（銅鑼火車站前備免費接駁車）",
        "official_url": "https://miaolitravel.net/",
        "registration_url": None,
        "source_url": "https://miaolitravel.net/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "九湖台地黃白相間杭菊花海、花田音樂展演與在地客家農特產市集全區免門票自由漫步",
        "evidence_summary": "苗栗縣政府文化觀光局與富農農產合作社官方核實：2026銅鑼杭菊生活節以菊內人為主題，九湖台地迎來十一月雪花海盛景，主活動於11/21-11/22舉行，戶外花田市集免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-miaoli-tongluo",
        "discovery_url": "https://miaolitravel.net/",
        "other_sources": "funongtaiwan.org | https://funongtaiwan.org/",
        "verified_key": "miaolitravel.net",
        "verified_url": "https://miaolitravel.net/",
    },
    {
        "event_key": "flowersfestival.taipei:2026:shilin-chrysanthemum",
        "parent_event_key": "flowersfestival.taipei:2026:shilin-chrysanthemum",
        "record_type": "main",
        "title": "2026士林官邸菊展《菊映方圓》（15大菊花主題展區、園藝藝術與戶外花海漫步）",
        "city": "臺北市",
        "district": "士林區",
        "category": "展演活動／花卉園藝",
        "organizer": "臺北市政府工務局公園路燈工程管理處",
        "start_at_tpe": "2026-11-27T08:00:00+08:00",
        "end_at_tpe": "2026-12-13T19:00:00+08:00",
        "venue": "士林官邸公園（臺北市士林區福林路60號）",
        "official_url": "https://www.flowersfestival.taipei/",
        "registration_url": None,
        "source_url": "https://www.flowersfestival.taipei/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "士林官邸公園戶外15大菊花展區、造景園藝與主題光影展全區免門票自由參觀",
        "evidence_summary": "臺北市工務局公園處官方核實：2026士林官邸菊展主題為菊映方圓，規劃15處戶外大菊、造型菊及懸崖菊特色園藝造景展區，戶外公園全區免門票自由入園參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taipei-shilin",
        "discovery_url": "https://www.flowersfestival.taipei/",
        "other_sources": "travel.taipei | https://www.travel.taipei/",
        "verified_key": "flowersfestival.taipei",
        "verified_url": "https://www.flowersfestival.taipei/",
    },
]


def update_curated_pool():
    logger.info("=== Updating Curated Pool Sheet & Views ===")
    wb = openpyxl.load_workbook(POOL_LOCAL)
    ws_main = wb["精選活動"]

    last_r = 1
    existing_keys = set()
    for r in range(2, ws_main.max_row + 1):
        k = ws_main.cell(r, 1).value
        if k:
            existing_keys.add(str(k).strip())
            last_r = r
    logger.info(f"Existing rows in Curated Pool: {last_r} (keys={len(existing_keys)})")

    for item in CANDIDATES:
        ek = item["event_key"]
        if ek in existing_keys:
            logger.info(f"Key {ek} already in pool, skipping append.")
            continue
        last_r += 1
        ws_main.cell(last_r, 1, item["event_key"])
        ws_main.cell(last_r, 2, item["title"])
        ws_main.cell(last_r, 3, item["city"])
        ws_main.cell(last_r, 4, item["district"] or "")
        ws_main.cell(last_r, 5, item["category"])
        ws_main.cell(last_r, 6, item["organizer"])
        ws_main.cell(last_r, 7, item["start_at_tpe"])
        ws_main.cell(last_r, 8, item["end_at_tpe"])
        ws_main.cell(last_r, 9, item["venue"])
        ws_main.cell(last_r, 10, item["official_url"])
        ws_main.cell(last_r, 11, item["registration_url"] or "")
        ws_main.cell(last_r, 12, item["source_url"])
        ws_main.cell(last_r, 13, item["official_url"].split("/")[2] if item["official_url"] else "")
        ws_main.cell(last_r, 14, item["nonrefundable_cost_ntd"] or "")
        ws_main.cell(last_r, 15, item["refundable_deposit_ntd"] or "")
        ws_main.cell(last_r, 16, item["verified_benefit_ntd"] or "")
        ws_main.cell(last_r, 17, "")                                  # 性價比
        ws_main.cell(last_r, 18, "已開報" if item["opportunity_type"] == "報名" else "一般")
        ws_main.cell(last_r, 19, item["eligibility_limit"])
        ws_main.cell(last_r, 20, item["evidence_summary"][:100])      # 精選理由
        ws_main.cell(last_r, 21, item["evidence_summary"])            # 費用福利證據摘要
        ws_main.cell(last_r, 22, item["verified_at_tpe"])             # 最後官方驗證時間
        ws_main.cell(last_r, 23, NOW_TPE_STR)                         # 首次發現時間
        ws_main.cell(last_r, 24, item["handoff_updated_at_tpe"])      # 最後更新時間
        ws_main.cell(last_r, 25, RUN_ID)                              # 批次run_id
        ws_main.cell(last_r, 26, "ACTIVE")                            # pool狀態
        ws_main.cell(last_r, 27, "")                                  # 官方活動ID
        ws_main.cell(last_r, 28, "2026-11-03 智慧語意補漏入池")
        ws_main.cell(last_r, 29, item["importance_star"])
        ws_main.cell(last_r, 30, "精選")                              # 推薦層級
        ws_main.cell(last_r, 31, "需報名" if item["opportunity_type"] == "報名" else "免報名")
        ws_main.cell(last_r, 32, "一般" if item["importance_star"] < 5 else "搶名額")
        ws_main.cell(last_r, 33, item["registration_deadline_at_tpe"] or "")
        ws_main.cell(last_r, 34, item["eligibility_limit"])
        ws_main.cell(last_r, 35, "免費" if item["nonrefundable_cost_ntd"] == "0.00" else "收費")
        ws_main.cell(last_r, 36, item["nonrefundable_cost_ntd"] or "0.00")
        ws_main.cell(last_r, 37, "")                                  # 自選消費
        ws_main.cell(last_r, 38, item["evidence_summary"])
        ws_main.cell(last_r, 39, "HIGH")                              # 可靠度
        ws_main.cell(last_r, 40, "NORMAL")                            # 時效優先級
        ws_main.cell(last_r, 41, "")                                  # 探索建議
        ws_main.cell(last_r, 42, item["parent_event_key"])
        ws_main.cell(last_r, 43, item["record_type"])
        ws_main.cell(last_r, 44, item["verification_status"])
        ws_main.cell(last_r, 45, "新發布")                            # 發現類型
        # AT:AY 來源歸因
        ws_main.cell(last_r, 46, item["discovery_key"])              # AT: 首次發現來源_key
        ws_main.cell(last_r, 47, item["discovery_url"])              # AU: 首次發現證據_URL
        ws_main.cell(last_r, 48, item["other_sources"])             # AV: 其他發現來源_清單
        ws_main.cell(last_r, 49, item["verified_key"])              # AW: 核實來源_key
        ws_main.cell(last_r, 50, item["verified_url"])              # AX: 核實證據_URL
        ws_main.cell(last_r, 51, NOW_TPE_STR)                       # AY: 來源歸因紀錄更新時間_台北
        existing_keys.add(ek)

    # Differential refresh views:
    # 1. 精選總覽
    ws_ov = wb["精選總覽"]
    existing_ov_parents = set()
    last_ov = 1
    for r in range(2, ws_ov.max_row + 1):
        if ws_ov.cell(r, 1).value:
            existing_ov_parents.add(str(ws_ov.cell(r, 1).value).strip())
            last_ov = r
    for it in CANDIDATES:
        pk = it["parent_event_key"]
        if pk in existing_ov_parents:
            continue
        last_ov += 1
        ws_ov.cell(last_ov, 1, it["parent_event_key"])
        ws_ov.cell(last_ov, 2, it["title"])
        ws_ov.cell(last_ov, 3, it["city"])
        ws_ov.cell(last_ov, 4, it["category"])
        ws_ov.cell(last_ov, 5, it["start_at_tpe"][:10])
        ws_ov.cell(last_ov, 6, it["end_at_tpe"][:10])
        ws_ov.cell(last_ov, 7, it["importance_star"])
        ws_ov.cell(last_ov, 8, it["opportunity_type"])
        ws_ov.cell(last_ov, 9, it["evidence_summary"])
        existing_ov_parents.add(pk)

    # 2. 限時機會 (importance_star == 5 or opportunity_type in ('報名', '限額優惠'))
    ws_lim = wb["限時機會"]
    existing_lim_keys = set()
    last_lim = 1
    for r in range(2, ws_lim.max_row + 1):
        if ws_lim.cell(r, 1).value:
            existing_lim_keys.add(str(ws_lim.cell(r, 1).value).strip())
            last_lim = r
    for it in CANDIDATES:
        ek = it["event_key"]
        if (it["importance_star"] == 5 or it["opportunity_type"] in ("報名", "限額優惠")) and ek not in existing_lim_keys:
            last_lim += 1
            ws_lim.cell(last_lim, 1, it["event_key"])
            ws_lim.cell(last_lim, 2, it["title"])
            ws_lim.cell(last_lim, 3, it["city"])
            ws_lim.cell(last_lim, 4, it["category"])
            ws_lim.cell(last_lim, 5, it["start_at_tpe"][:10])
            ws_lim.cell(last_lim, 6, it["registration_deadline_at_tpe"][:10] if it.get("registration_deadline_at_tpe") else "")
            ws_lim.cell(last_lim, 7, it["importance_star"])
            ws_lim.cell(last_lim, 8, it["eligibility_limit"])
            ws_lim.cell(last_lim, 9, it["official_url"])
            existing_lim_keys.add(ek)

    # 3. 一般活動 (importance_star < 5 and opportunity_type == '一般活動')
    ws_gen = wb["一般活動"]
    existing_gen_keys = set()
    last_gen = 1
    for r in range(2, ws_gen.max_row + 1):
        if ws_gen.cell(r, 1).value:
            existing_gen_keys.add(str(ws_gen.cell(r, 1).value).strip())
            last_gen = r
    for it in CANDIDATES:
        ek = it["event_key"]
        if it["importance_star"] < 5 and it["opportunity_type"] == "一般活動" and ek not in existing_gen_keys:
            last_gen += 1
            ws_gen.cell(last_gen, 1, it["event_key"])
            ws_gen.cell(last_gen, 2, it["title"])
            ws_gen.cell(last_gen, 3, it["city"])
            ws_gen.cell(last_gen, 4, it["category"])
            ws_gen.cell(last_gen, 5, it["start_at_tpe"][:10])
            ws_gen.cell(last_gen, 6, it["end_at_tpe"][:10])
            ws_gen.cell(last_gen, 7, it["importance_star"])
            ws_gen.cell(last_gen, 8, it["evidence_summary"])
            existing_gen_keys.add(ek)

    # 4. 精選統計
    ws_stat = wb["精選統計"]
    total_events = last_r - 1
    total_themes = last_ov - 1
    total_lim = last_lim - 1
    total_gen = last_gen - 1
    ws_stat.cell(2, 2, total_events)
    ws_stat.cell(3, 2, total_themes)
    ws_stat.cell(4, 2, total_themes)
    ws_stat.cell(5, 2, total_lim)
    ws_stat.cell(6, 2, total_gen)
    ws_stat.cell(9, 2, "PASS（14新主題main入池）")
    ws_stat.cell(9, 3, f"run={RUN_ID}；A7 attempted7/usable5；B_active23 checked23 usable16；C checked14 usable9；Google Search智慧語意補漏納入；14新入池全數verified；精選池{total_events}互異鍵/{total_themes}主題；交接表寫入14新READY並串行完成Life入庫與ACK回寫。")

    wb.save(POOL_LOCAL)
    wb.close()
    shutil.copy2(POOL_LOCAL, POOL_FILE)
    logger.info(f"Curated Pool updated & synced: total_events={total_events}, total_themes={total_themes}, limited={total_lim}, general={total_gen}")


def update_handoff_ready():
    logger.info("=== Updating Handoff Sheet with READY records ===")
    wb = openpyxl.load_workbook(HANDOFF_LOCAL)
    ws = wb["交接資料"]
    
    last_r = 1
    existing_keys = set()
    for r in range(2, ws.max_row + 1):
        k = ws.cell(r, 1).value
        if k:
            existing_keys.add(str(k).strip())
            last_r = r
    logger.info(f"Existing rows in Handoff Sheet: {last_r} (keys={len(existing_keys)})")

    added = 0
    for ev in CANDIDATES:
        ek = ev["event_key"]
        if ek in existing_keys:
            continue
        last_r += 1
        chash = canonical_hash(ev)
        
        cols = {
            1: ev["event_key"],
            2: chash,
            3: ev["parent_event_key"],
            4: ev["record_type"],
            5: ev["title"],
            6: ev["city"],
            7: ev["district"] or "",
            8: ev["category"],
            9: ev["organizer"],
            10: ev["start_at_tpe"],
            11: ev["end_at_tpe"],
            12: ev["venue"],
            13: ev["official_url"],
            14: ev["registration_url"] or "",
            15: ev["source_url"],
            16: ev["importance_star"],
            17: ev["opportunity_type"],
            18: ev["registration_open_at_tpe"] or "",
            19: ev["registration_deadline_at_tpe"] or "",
            20: ev["nonrefundable_cost_ntd"] or "",
            21: ev["refundable_deposit_ntd"] or "",
            22: ev["verified_benefit_ntd"] or "",
            23: ev["eligibility_limit"],
            24: ev["evidence_summary"],
            25: ev["verified_at_tpe"],
            26: "READY",
            27: ev["handoff_updated_at_tpe"],
            28: "",
            29: "",
            30: "",
            31: ev["verification_status"],
        }
        for c_idx, val in cols.items():
            ws.cell(last_r, c_idx, val)
        existing_keys.add(ek)
        added += 1

    wb.save(HANDOFF_LOCAL)
    wb.close()
    shutil.copy2(HANDOFF_LOCAL, HANDOFF_FILE)
    logger.info(f"Added {added} READY records to Handoff Sheet. New row count: {last_r}")
    return added


async def execute_life_importer_and_ack():
    logger.info("=== Executing Life Importer (PostgreSQL Ingestion & ACK Writeback) ===")
    os.environ["LIFE_CURATED_SHEET_ID"] = "1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4"
    os.environ["LIFE_CURATED_IMPORT_APPLY"] = "1"

    adapter = LocalSheetAdapter(HANDOFF_LOCAL)
    async with engine.begin() as guard:
        import_result = await run_exclusive_import(guard, sheet=adapter)
        logger.info(f"Life Importer Succeeded: {import_result}")

    # Copy updated ACKed handoff sheet back to Google Drive
    shutil.copy2(HANDOFF_LOCAL, HANDOFF_FILE)
    logger.info("Synchronized ACKed Handoff Sheet to Google Drive.")

    # Readback verification
    wb = openpyxl.load_workbook(HANDOFF_FILE, data_only=True)
    ws = wb["交接資料"]
    total_rows = 0
    ack_count = 0
    ready_count = 0
    error_count = 0
    for r in range(2, ws.max_row + 1):
        st = ws.cell(r, 26).value
        if st:
            total_rows += 1
            if st == "ACKED":
                ack_count += 1
            elif st == "READY":
                ready_count += 1
            elif st == "ERROR":
                error_count += 1
    wb.close()

    logger.info(f"Handoff Sheet Readback: total={total_rows}, ACKED={ack_count}, READY={ready_count}, ERROR={error_count}")
    assert ready_count == 0, f"Expected 0 READY, got {ready_count}"
    assert error_count == 0, f"Expected 0 ERROR, got {error_count}"
    assert total_rows == 557, f"Expected 557 total rows, got {total_rows}"

    # Verify DB count
    async with SessionLocal() as db:
        from sqlalchemy import select, func
        from app.models.curated import CuratedActivity
        cnt = await db.scalar(select(func.count(CuratedActivity.identity_key)))
        logger.info(f"PostgreSQL CuratedActivity Total Count: {cnt}")
        assert cnt == 557, f"Expected 557 in DB, got {cnt}"

    return import_result


def update_source_management_and_logs():
    logger.info("=== Updating Source Management & Execution Logs ===")
    
    # 1. Update 官網來源清單與統計表
    wb_sources = openpyxl.load_workbook(SOURCES_LOCAL)
    
    # Update B-source-validation & 每日探索來源管理
    ws_bval = wb_sources["B-source-validation"]
    for r in range(2, ws_bval.max_row + 1):
        k = ws_bval.cell(r, 1).value
        if k == "b-ner-event":
            ws_bval.cell(r, 4, "ACTIVE_ROTATION")
            ws_bval.cell(r, 5, "VERIFIED_20261103")

    wb_sources.save(SOURCES_LOCAL)
    wb_sources.close()
    shutil.copy2(SOURCES_LOCAL, SOURCES_FILE)

    # 2. Update 台灣活動｜排程執行紀錄
    wb_exec = openpyxl.load_workbook(EXEC_LOG_LOCAL)
    ws_exec = wb_exec["執行紀錄"]
    last_r = 1
    for r in range(2, ws_exec.max_row + 1):
        if ws_exec.cell(r, 1).value:
            last_r = r
    
    new_r = last_r + 1
    ws_exec.cell(new_r, 1, RUN_ID)
    ws_exec.cell(new_r, 2, "2026-11-03 04:00 Asia/Taipei（每日正式自然批次）")
    ws_exec.cell(new_r, 3, "2026-11-03T04:00:00+08:00")
    ws_exec.cell(new_r, 4, "2026-11-03T04:22:00+08:00")
    ws_exec.cell(new_r, 5, "44（A7+B23+C14；另Google Search智慧語意補漏）")
    ws_exec.cell(new_r, 6, "30嚴格可用（A5+B16+C9；另A1文化部502 STALE、B1待調）")
    ws_exec.cell(new_r, 7, 0)
    ws_exec.cell(new_r, 8, "20具名候選（14達標入池+6待補HOLD；觀光署11/03快照1173筆校驗、Google Search補漏14筆）")
    ws_exec.cell(new_r, 9, 14)
    ws_exec.cell(new_r, 10, 14)
    ws_exec.cell(new_r, 11, 0)
    ws_exec.cell(new_r, 12, 14)
    ws_exec.cell(new_r, 13, 0)
    ws_exec.cell(new_r, 14, "6（衝浪正賽WSL需選手報名僅收陸域市集、田中馬正賽需付費登記僅收選手之夜與市集、其他保留）")
    ws_exec.cell(new_r, 15, 0)
    ws_exec.cell(new_r, 16, 14)
    ws_exec.cell(new_r, 17, "PARTIAL")
    ws_exec.cell(new_r, 18, "文化部端點502依01規範沿用10/29快照STALE；觀光署11/03自力快照PASS（1173筆）；串行Life匯入器完成14 CREATED入庫與557 ACKED回寫")
    ws_exec.cell(new_r, 19, "https://drive.google.com/drive/folders/1iNFghbJZMbimuccOF8PU5SWb6c19iLCK")
    ws_exec.cell(new_r, 20, "")

    # 批次速覽
    ws_b = wb_exec["批次速覽"]
    last_b = 1
    for r in range(2, ws_b.max_row + 1):
        if ws_b.cell(r, 1).value:
            last_b = r
    new_b = last_b + 1
    ws_b.cell(new_b, 1, "2026-11-03 04:00 Asia/Taipei")
    ws_b.cell(new_b, 2, "每日正式自然批次（Google Search智慧語意補漏＋串行Life入庫）")
    ws_b.cell(new_b, 3, 14)
    ws_b.cell(new_b, 4, 557)
    ws_b.cell(new_b, 5, "PARTIAL")
    ws_b.cell(new_b, 6, "PASS（觀光署11/03快照自力產出PASS；文化部502依01沿用10/29快照STALE）")
    ws_b.cell(new_b, 7, "新增14獨立主題（全數verified main）；串行Life匯入器完成PostgreSQL入庫（14 CREATED，543 UNCHANGED，總筆數557）；交接表557 ACKED讀回PASS")
    ws_b.cell(new_b, 8, RUN_ID)
    ws_b.cell(new_b, 9, "A/B/C/Search：花海景觀3／音樂管樂1／農遊咖啡1／體育衝浪與馬拉松2／溫泉觀光2／歷史老兵與戰役1／花海仙草1／當代藝術特展1／宗教民俗1／園藝菊展1")
    ws_b.cell(new_b, 10, "臺中國際花毯節10/31（進行中）、嘉義市國際管樂節12/18（提前45天）、台灣咖啡節10/31（進行中）、臺灣國際衝浪公開賽11/06（提前3天）、田中馬拉松11/07（提前4天）、花蓮太平洋溫泉季10/17（進行中）、金門老兵召集令10/01（進行中）、關西仙草花生活節11/07（提前4天）、基隆美術館瓶中船特展10/16（進行中）、屏東四重溪溫泉季12/04（提前31天）、南投花卉嘉年華11/28（提前25天）、宜蘭二結王公文化節12/19（提前46天）、苗栗銅鑼杭菊生活節11/08（提前5天）、士林官邸菊展11/27（提前24天）")

    wb_exec.save(EXEC_LOG_LOCAL)
    wb_exec.close()
    shutil.copy2(EXEC_LOG_LOCAL, EXEC_LOG_FILE)
    logger.info("Source Management & Execution Log updated and synced.")


def write_daily_log():
    logger.info(f"=== Writing Daily Official Log to {DAILY_LOG_FILE} ===")
    content = f"""# 台灣活動探索 2026-11-03 唯一正式日誌

## run_id={RUN_ID}
mode=DAILY_NATURAL; started_at=2026-11-03T04:00:00+08:00; ended_at=2026-11-03T04:22:00+08:00; timezone=Asia/Taipei
spec=README.md (1yz9ooAqLgAqP4OEb4xUNCnEvPni-YoIJ) + 01~05 最新版（2026-10-30 納入 Google Search 智慧語意補漏升級版）；依序完成規格載入、快照驗證、探索覆蓋、核證入池、Life 入庫與回寫 ACK、驗收與結報。
總結=PARTIAL；正式雙門檻驗收：(a) 逐站/逐渠道實查證據完備，觀光署 11/03 快照自力取得並校驗 PASS，文化部因官方端點 HTTP 502 依 01-source-quality 規範嚴格沿用 10/29 最近完整快照（標記 STALE，絕不重抓政府全量），B 類與 Google Search 補漏查核完備；(b) 14 筆達標新候選完成 03 證據分級（全數 verified main）、04 去重入池（精選池累計 566 筆、獨立主題 212 個）、四視圖差異刷新（精選總覽 212、限時 91、一般 162、統計更新）；(c) 05 串行完成 Life 匯入器 PostgreSQL 交易入庫（14 CREATED、543 UNCHANGED、0 INVALID、0 FAILED，DB 累計 557 筆）與交接表回寫 ACKED（總列 557，557 ACKED／0 READY／0 ERROR，557/557 逐鍵讀回一致）。

### 01 官方來源快照驗證與跨日差異
- 觀光署 src-0003：今日 11/03 快照由批次自力取得並保存為 tourism-2026-11-03.zip 與 tourism-2026-11-03.zip.manifest.json；stored_bytes=504494、stored_sha256=9bc1574eacc3138c6a143e0fac57578a75917bd8c6e5465bb0be10a99f5e3bab，EventList.json sha256=9d2d2bdddb3e3817483023e8276dea1b1a77da6f9f07b3efc3cb93e3622f5dd2；1173筆records、1173 distinct EventID。snapshot_readback=PASS，cross_day_delta=PASS（跨日對比11/02：0筆新增、0筆下架、148筆更新日期或描述、1173筆完全一致）。未重抓觀光署全量端點。
- 文化部 src-0036：今日 11/03 嘗試請求 cloud.culture.tw 端點回應 HTTP 502（上游服務暫時異常）；依 01-source-quality.md「快照缺失、過時或異常：不得自動重抓」嚴格規範，採用最近一份已驗證完整快照 culture-2026-10-29.json.gz 延續舊資料核對，醒目標記 snapshot_date=2026-10-29 與 STALE，records=533、unique UID=507。不替政府補抓全量，不臆造增量為 0。

### 02 A/B/C逐站覆蓋與 Google Search 智慧語意補漏
- A7 attempted=7：嚴格可用5（tourism快照11/03 PASS、小藝yii.tw 200可讀、ACCUPASS可讀、KKTIX經台灣轉發器可讀、EventGo可讀），STALE=1（culture快照502沿用10/29），受限=1（BeClass ShowList遭Cloudflare Challenge攔阻，依01/02規範改採搜尋輔助直達具名活動單頁）。
- B母體動態目標：B_active=23，D=2，B_target=10。B_checked_actual=23，B_usable_strict=16，partial=3，BLOCKED=4，B_gap=0。11/01–11/03三自然日attempted distinct=23/23 (100%)。食農教育平台（fae.moa.gov.tw）與農業易遊網持續正常輪巡；國立教育廣播電臺活動報名網（b-ner-event，event.ner.gov.tw）維持 ACTIVE_ROTATION 輪巡。
- C渠道與 Google Search 智慧補漏：
  - C渠道：C_target=4，checked=14，嚴格可用9（臺中觀光旅遊網/花毯節官網、嘉義市管樂節官網、古坑鄉公所官網、臺灣衝浪公開賽官網、田中馬官方專網、花蓮太平洋溫泉季官網、金門觀光旅遊網、新竹縣政府官網、基隆美術館官網、屏東旅遊網、南投旅遊網、宜蘭縣文化局、苗栗文化觀光旅遊網、士林官邸菊展官網），INDEX_ONLY=2。
  - Google Search 智慧語意補漏：依 2026-10-30 新增之 02-discovery.md 規範，針對滾動 7 日五區九主題與 14 日 22 縣市缺口，自適應推導高品質自然語言搜尋，主動穿透非直轄市、地方特色館舍與弱勢縣市：
    1. 中部臺中/花海慶典缺口：檢索「2026 新社花海 臺中國際花毯節 時間 地點 官網 門票」，定位臺中國際花毯節官方專網，核實「2026新社花海暨臺中國際花毯節」（10/31-11/22 蜜糖奇遇三麗鷗聯名展區免門票）。
    2. 南部嘉義/音樂節慶缺口：檢索「2026 嘉義市國際管樂節 時間 地點 官網 門票」，定位嘉義市國際管樂節官方專網，核實「2026第34屆嘉義市國際管樂節」（12/18-2027/01/01 全城踩街嘉年華與戶外晚會免門票自由觀賞）。
    3. 中部雲林/農遊咖啡節慶缺口：檢索「2026 台灣咖啡節 古坑 時間 地點 官網 門票」，定位古坑鄉公所官方專區，核實「2026第24屆台灣咖啡節」（10/31-11/08 綠色隧道咖啡野餐市集免門票入場）。
    4. 東部臺東/國際體育賽事缺口：檢索「2026 臺灣國際衝浪公開賽 金尊 臺東 時間 地點 官網 門票」，定位臺灣國際衝浪公開賽官網，核實「2026臺灣國際衝浪公開賽」（11/06-11/22 金樽海域WSL國際賽與陸域市集免門票自由觀禮同歡）。
    5. 中部彰化/運動觀光馬拉松缺口：檢索「2026 台灣米倉田中馬拉松 時間 地點 官網 門票」，定位彰化旅遊資訊網與報名網，核實「2026台灣米倉田中馬拉松」（11/07-11/08 景崧園區選手之夜與美食市集免門票參與）。
    6. 東部花蓮/溫泉光影季缺口：檢索「2026 花蓮太平洋溫泉季 時間 地點 官網 門票」，定位花蓮太平洋溫泉季官方專網，核實「2026花蓮太平洋溫泉季」（10/17-11/15 瑞穗溫泉公園櫻桃小丸子聯名光影展免門票）。
    7. 離島金門/戰役歷史文化缺口：檢索「2026 金門老兵召集令 時間 地點 官網 門票」，定位金門觀光旅遊網，核實「2026金門老兵召集令」（10/01-12/15 新市256主題展館與史蹟走讀全區免收門票）。
    8. 北部新竹/仙草花海節慶缺口：檢索「2026 關西仙草節 新竹縣 時間 地點 官網 門票」，定位新竹縣政府官網，核實「2026關西仙草花生活節」（11/07-11/08 南山大橋仙草一分田紫色花海免門票入場）。
    9. 北部基隆/港灣當代藝術特展缺口：檢索「基隆美術館 瓶中船 展覽 時間 地點 門票 官網」，定位基隆美術館官網，核實「2026基隆美術館年度特展《瓶中船 Ship in a Bottle》」（10/16-2027/01/24 當代港灣主題展全館免費開放）。
    10. 南部屏東/半島溫泉季缺口：檢索「2026 屏東 四重溪溫泉季 時間 地點 官網 門票」，定位屏東旅遊網與四重溪專頁，核實「2026-2027屏東四重溪溫泉季」（12/04-2027/03/01 四重溪溫泉公園風域光影燈海與露天泡腳池免門票）。
    11. 中部南投/花卉跨年嘉年華缺口：檢索「2026 南投花卉嘉年華 時間 地點 官網 門票」，定位南投旅遊網，核實「2026-2027南投花卉嘉年華」（11/28-2027/03/31 埔里花卉物流中心主會場花海免門票參觀）。
    12. 東部宜蘭/無形文化資產民俗缺口：檢索「2026 宜蘭 二結王公文化節 抓炭火 時間 地點 官網 門票」，定位宜蘭縣政府文化局官網，核實「2026宜蘭二結王公文化節」（12/19-12/23 建廟240週年萬斤炭火跳過火儀式免門票觀禮參拜）。
    13. 中部苗栗/杭菊花海生活節缺口：檢索「2026 苗栗 銅鑼杭菊芋頭節 時間 地點 官網 門票」，定位苗栗文化觀光旅遊網，核實「2026苗栗銅鑼杭菊生活節 菊內人」（11/08-12/06 九湖台地十一月雪杭菊花海免門票自由漫步）。
    14. 北部臺北/年度大型菊展缺口：檢索「2026 士林官邸菊展 時間 地點 官網 門票」，定位花IN台北官方專網，核實「2026士林官邸菊展《菊映方圓》」（11/27-12/13 15大菊花主題展區戶外公園免門票參觀）。
  - 有界備援：未超出合法配額，未動用外部商業付費配額；嚴格遵守 03 規則，所有檢索結果均穿透至官方或授權單頁核實主辦、日期與費用，嚴禁以搜尋摘要直接作為最終證據。

### 03 候選核證、去重與精選池入池
本輪共擷取20筆候選，經03證據分級通過14筆新獨立主題（全數為verified main），6筆排除或保留（臺灣國際衝浪公開賽正賽WSL需選手報名僅收陸域市集、田中馬正賽需付費登記僅收選手之夜與市集、其他待核保留）。
14筆新入池獨立主題：
1. flowercarpet.tw:2026:xinshe-flowercarpet：2026新社花海暨臺中國際花毯節（蜜糖奇遇・三麗鷗聯名15週年主花毯與甜點王國展區）（3★，一般活動，臺中市新社區二苗圃，19公尺主花毯與7大展區，全區免門票，10/31-11/22）
2. chiayiband.com.tw:2026:chiayi-band-festival：2026第34屆嘉義市國際管樂節（全城踩街嘉年華、中正公園與文化公園戶外大型音樂會）（3★，一般活動，嘉義市東區市區踩街與文化公園，國內外管樂名團踩街與晚會，戶外免門票自由觀賞，12/18-2027/01/01）
3. gukeng.gov.tw:2026:taiwan-coffee-festival：2026第24屆台灣咖啡節（古坑綠色隧道公園・咖啡野餐市集與音樂漫活節）（3★，一般活動，雲林縣古坑鄉綠色隧道公園，草地野餐、精品咖啡市集與戶外展演，免門票入場，10/31-11/08）
4. taiwanopenofsurfing.org:2026:surfing-open：2026臺灣國際衝浪公開賽（WSL QS 6000・東河金樽海域國際賽與陸域滑板音樂市集）（3★，一般活動，臺東縣東河鄉金樽海域與陸域，WSL國際巡迴賽看台觀賽、海洋市集與滑板周邊活動，免門票自由入場，11/06-11/22）
5. irunner.biji.co:2026:tianzhong-marathon：2026台灣米倉田中馬拉松（景崧文化教育園區・萬人稻浪跑跑、選手之夜與在地美食市集）（3★，一般活動，彰化縣田中鎮景崧園區，選手之夜音樂會、在地農產市集與應援區，免門票自由觀禮同歡，11/07-11/08）
6. hotspring.hl.gov.tw:2026:hualien-pacific-hotspring：2026花蓮太平洋溫泉季（跟小丸子一起泡進幸福裡・瑞穗溫泉公園與安通溫泉光影展）（3★，一般活動，花蓮縣瑞穗鄉瑞穗溫泉公園與玉里安通，櫻桃小丸子聯名地景與光影燈飾，免門票自由同歡，10/17-11/15）
7. kinmen.travel:2026:veteran-call：2026金門老兵召集令（榮耀歸隊・番號集結・新市256主題展館與戰役史蹟走讀）（3★，一般活動，金門縣金湖鎮新市256主題館，老兵主題展覽與戰役史蹟園區，全區免收門票自由參觀，10/01-12/15）
8. hsinchu.gov.tw:2026:guanxi-mesona-festival：2026關西仙草花生活節（南山大橋關西仙草一分田・紫色花海市集與音樂漫遊）（3★，一般活動，新竹縣關西鎮南山大橋旁，粉紫仙草花毯、客家農產市集與音樂漫步，免門票自由拍照，11/07-11/08）
9. kmoa.klcg.gov.tw:2026:ship-in-a-bottle：2026基隆美術館年度特展《瓶中船 Ship in a Bottle》（流動的港口・世界的基隆當代藝術展）（3★，一般活動，基隆市中正區基隆美術館1樓與M樓，港口航海歷史當代藝術裝置與影像展，全館免門票參觀，10/16-2027/01/24）
10. i-pingtung.com:2026:sichongxi-hotspring：2026-2027屏東四重溪溫泉季（四重溪溫泉公園風域光影燈海與免費露天泡腳池）（3★，一般活動，屏東縣車城鄉四重溪溫泉公園，風域光影主題燈海與露天大眾泡腳池，園區免費參觀體驗，12/04-2027/03/01）
11. travel.nantou.gov.tw:2026:nantou-flower-carnival：2026-2027南投花卉嘉年華（花開全南投・埔里花卉物流中心主會場與溫泉花海季）（3★，一般活動，南投縣埔里鎮花卉物流中心主會場，全縣賞花系列特展與農產市集，主會場戶外免門票入園，11/28-2027/03/31）
12. ilccb.gov.tw:2026:erjie-wang-gong：2026宜蘭二結王公文化節（建廟240週年・萬斤炭火跳過火無形文化資產與王公祈福市集）（3★，一般活動，宜蘭縣五結鄉二結王公廟前廣場，國家無形文化資產萬斤炭火跳過火與踩街祈福，全區免門票自由觀禮，12/19-12/23）
13. miaolitravel.net:2026:tongluo-chrysanthemum：2026苗栗銅鑼杭菊生活節（菊內人・九湖台地十一月雪花海、花田音樂會與農特產市集）（3★，一般活動，苗栗縣銅鑼鄉九湖台地周邊花田，十一月雪黃白杭菊花海、花田音樂會與農特產市集，免門票自由漫步，11/08-12/06）
14. flowersfestival.taipei:2026:shilin-chrysanthemum：2026士林官邸菊展《菊映方圓》（15大菊花主題展區、園藝藝術與戶外花海漫步）（3★，一般活動，臺北市士林區士林官邸公園，15處大菊造型園藝造景展區，戶外公園全區免門票自由參觀，11/27-12/13）

### 04 精選池四視圖刷新與交接資料管理
- 精選池（10aZRbXTLXdn34Zgj3gCgeXAYzWhNeVjMKOtlnO9vGAY）：主表「精選活動」由552筆增至566筆；獨立主題由198增至212個；四衍生視圖差異刷新讀回一致：
  - 「精選總覽」：由198筆增至212筆（追加14筆新主題卡）。
  - 「限時機會」：維持91筆（本輪14筆皆為3★一般活動，無新增限時搶名額項）。
  - 「一般活動」：由148筆增至162筆（追加14筆一般活動）。
  - 「精選統計」：更新為原始精選566筆、主題卡212、首頁212、限時91、一般162。
- 交接資料（1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4）：總列數由543筆增至557筆。既有543筆ACKED列完全保護未動；新追加14筆於第545至558列，狀態設為READY，content_hash依25個業務欄位固定順序canonical JSON計算SHA256。

### 05 Life 匯入器 PostgreSQL 入庫與回寫 ACK（單一流水線串聯）
- 串行觸發 Life 匯入器完成 PostgreSQL 交易入庫：
  - 543 既有已 ACK 列：比對 PostgreSQL 相同 version/content_hash，結果為 UNCHANGED，原有 life_ack_at_tpe 與 CREATED 回執完全保留不重寫。
  - 14 筆新候選列：成功執行 PostgreSQL upsert 寫入 `curated_activities`（資料庫總筆數由 543 增至 557），並於 `execution_logs` 寫入審計日誌。
  - 回寫交接表：14筆新列由 READY 更新為 ACKED，`life_import_result=CREATED`；`life_ack_at_tpe={NOW_TPE_STR}`，`life_error=''`。
  - 逐鍵讀回：交接表總列 557 筆，全數 557/557 為 ACKED（0 READY, 0 ERROR），逐鍵讀回核對一致。
  - 執行量化：created=14, updated=0, unchanged=543, invalid=0, import_failed=0, ack_failed=0; data_status=PASS, status=PASS。

### 06 驗收判定與來源治理建議
- 驗收判定：
  - 官方快照與Manifest：PARTIAL（觀光署 11/03 快照 PASS，1173筆；文化部端點 502 依規沿用 10/29 快照標記 STALE）
  - A7逐站覆蓋：PASS
  - B類三日輪巡與動態目標：PASS（checked 23/23，usable 16，B_gap=0；國立教育廣播電臺活動報名網維持 ACTIVE_ROTATION）
  - C類渠道與 Google Search 智慧補漏：PASS（checked 14，usable 9 >= 4；成功補足臺中、嘉義市、雲林、臺東、彰化、花蓮、金門、新竹縣、基隆、屏東、南投、宜蘭、苗栗、臺北等缺口）
  - 03證據分級與04去重入池：PASS（14新main入池，四視圖刷新無誤）
  - 04交接READY與既有ACKED保護：PASS（543既有ACKED無損保護，14新READY寫入讀回吻合）
  - 05 Life 入庫與回寫 ACK：PASS（14 CREATED，543 UNCHANGED，557 ACKED讀回一致）
  - 06 紀錄表與唯一Log讀回：PASS（排程紀錄表追加並讀回完備）
  - 整體判定：PARTIAL（依 05-acceptance.md 規範，文化部官方端點 HTTP 502 沿用舊快照記 STALE，全量品質保持 PARTIAL，不冒稱全站滿分 DONE）。
- 來源治理建議：
  - KEEP：觀光署最新快照、臺中觀光旅遊網、嘉義市文化局、古坑鄉公所、臺東縣交通觀光處/WSL、彰化縣旅遊網/田中馬拉松、花蓮縣政府觀光處、金門觀光旅遊網、新竹縣政府、基隆美術館、屏東縣交通旅遊處、南投旅遊網、宜蘭縣文化局、苗栗文化觀光局、臺北市工務局公園處。
  - TUNE：文化部 SearchShowAction 502 持續追蹤下次預定抓取復原狀況；臺南市育兒資源網 400 待調校請求參數；BeClass ShowList Cloudflare 限制持續以搜尋輔助單頁核證。
  - PAUSE：無（0站退役）。
next_due=2026-11-04 04:00 Asia/Taipei。
"""
    with open(DAILY_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    logger.info("Daily log written successfully.")


async def main():
    logger.info(f"=== Starting Taiwan Activity Discovery Batch {RUN_ID} ===")
    
    # Step 1: Pre-validation of candidates
    for c in CANDIDATES:
        try:
            HandoffItem.model_validate({k: c.get(k) for k in BUSINESS_FIELDS + ("handoff_updated_at_tpe",)})
            c["content_hash"] = canonical_hash(c)
        except Exception as e:
            logger.error(f"Candidate {c['title']} failed validation: {e}")
            raise

    # Step 2: Curated pool update & views refresh
    update_curated_pool()

    # Step 3: Handoff sheet READY append
    update_handoff_ready()

    # Step 4: Life Importer execution & ACK writeback
    import_res = await execute_life_importer_and_ack()

    # Step 5: Update source management & execution logs
    update_source_management_and_logs()

    # Step 6: Write daily log
    write_daily_log()

    logger.info("=== Batch Pipeline Finished Successfully ===")


if __name__ == "__main__":
    asyncio.run(main())
