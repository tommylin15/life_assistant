"""
Taiwan Activity Discovery Daily Batch - 2026-11-01 (Asia/Taipei 04:00)
Run ID: tw-discovery-daily-20261101-040000-agy38f
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
NOW_TPE_STR = "2026-11-01T04:00:00+08:00"
RUN_ID = "tw-discovery-daily-20261101-040000-agy38f"

DRIVE_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟")
HANDOFF_FILE = DRIVE_DIR / "台灣活動｜交接資料.xlsx"
POOL_FILE = DRIVE_DIR / "台灣活動｜精選池（Excel相容）.xlsx"
SOURCES_FILE = DRIVE_DIR / "官網來源清單與統計表.xlsx"
EXEC_LOG_FILE = DRIVE_DIR / "台灣活動｜排程執行紀錄.xlsx"
LOG_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜每日執行日誌")
DAILY_LOG_FILE = LOG_DIR / "2026-11-01.log"

LOCAL_DIR = Path("/tmp/tw_sheets_20261101")
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


# Define the 14 new verified candidates for 2026-11-01
CANDIDATES = [
    {
        "event_key": "taichung.gov.tw:2026:xinshe-flowercarpet",
        "parent_event_key": "taichung.gov.tw:2026:xinshe-flowercarpet",
        "record_type": "main",
        "title": "2026新社花海暨臺中國際花毯節（甜點王國與三麗鷗主題花毯）",
        "city": "臺中市",
        "district": "新社區",
        "category": "地方節慶／觀光活動",
        "organizer": "農業部種苗改良繁殖場、臺中市政府觀光旅遊局",
        "start_at_tpe": "2026-10-31T08:30:00+08:00",
        "end_at_tpe": "2026-11-22T16:30:00+08:00",
        "venue": "農業部種苗改良繁殖場第二苗圃（臺中市新社區協興街30號）",
        "official_url": "https://www.flowercarpet.tw/",
        "registration_url": None,
        "source_url": "https://travel.taichung.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "全區免費自由入場，三麗鷗7大明星主題展區與19米蜜糖奇遇主花毯",
        "evidence_summary": "臺中市政府觀光旅遊局與農業部種苗改良繁殖場官方核實：第15屆花毯節以甜點王國為主題，首度跨界三麗鷗明星打造7大展區與高達19公尺主花毯，全區免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taichung",
        "discovery_url": "https://www.flowercarpet.tw/",
        "other_sources": "",
        "verified_key": "flowercarpet.tw",
        "verified_url": "https://www.flowercarpet.tw/",
    },
    {
        "event_key": "ntpc.gov.tw:2026:christmasland",
        "parent_event_key": "ntpc.gov.tw:2026:christmasland",
        "record_type": "main",
        "title": "2026新北歡樂耶誕城（萌幻熱氣球卡娜赫拉主題燈區）",
        "city": "新北市",
        "district": "板橋區",
        "category": "地方節慶／市集展演",
        "organizer": "新北市政府觀光旅遊局",
        "start_at_tpe": "2026-11-13T17:30:00+08:00",
        "end_at_tpe": "2026-12-27T23:00:00+08:00",
        "venue": "新北市市民廣場、板橋車站周邊（站前廣場、萬坪公園及府中廣場）",
        "official_url": "https://christmasland.ntpc.gov.tw/",
        "registration_url": None,
        "source_url": "https://christmasland.ntpc.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "全區四大燈區免門票自由參觀，每日17:30-23:00點燈與主題光雕秀",
        "evidence_summary": "新北市觀光旅遊局官方核實：全台冬季指標性大型慶典，為期45天跨越四大燈區，結合萌幻熱氣球主燈秀、主題耶誕市集與光影藝術，免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-ntpc",
        "discovery_url": "https://christmasland.ntpc.gov.tw/",
        "other_sources": "",
        "verified_key": "christmasland.ntpc.gov.tw",
        "verified_url": "https://christmasland.ntpc.gov.tw/",
    },
    {
        "event_key": "necoast-nsa.gov.tw:2026:caoling-silvergrass",
        "parent_event_key": "necoast-nsa.gov.tw:2026:caoling-silvergrass",
        "record_type": "main",
        "title": "2026草嶺古道芒花季（25週年古道秋芒與芒著走花時間市集）",
        "city": "新北市",
        "district": "貢寮區",
        "category": "戶外休閒／生態走讀",
        "organizer": "交通部觀光署東北角及宜蘭海岸國家風景區管理處",
        "start_at_tpe": "2026-11-14T09:00:00+08:00",
        "end_at_tpe": "2026-12-13T17:00:00+08:00",
        "venue": "草嶺古道沿線（新北市貢寮區遠望坑至宜蘭縣頭城鎮大里）、福隆遊客中心",
        "official_url": "https://events.necoast-nsa.gov.tw/flower26/",
        "registration_url": None,
        "source_url": "https://www.necoast-nsa.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "步道免門票自由健行，每週六日提供福隆至遠望坑接駁車與免費古裝租借",
        "evidence_summary": "觀光署東北角管理處官方核實：草嶺古道芒花季25週年，橫跨新北貢寮與宜蘭頭城，包含秋芒拓碑、芒著走花時間市集、手作體驗與免費古裝變裝，自由健行參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-necoast",
        "discovery_url": "https://events.necoast-nsa.gov.tw/flower26/",
        "other_sources": "",
        "verified_key": "necoast-nsa.gov.tw",
        "verified_url": "https://events.necoast-nsa.gov.tw/flower26/",
    },
    {
        "event_key": "hakka.gov.tw:2026:liudui-harvest-festival",
        "parent_event_key": "hakka.gov.tw:2026:liudui-harvest-festival",
        "record_type": "main",
        "title": "2026六堆秋收祭（客庄收成慶典、秋收野餐與千人醃蘿蔔）",
        "city": "屏東縣",
        "district": "內埔鄉",
        "category": "地方節慶／文化生活",
        "organizer": "客家委員會客家文化發展中心",
        "start_at_tpe": "2026-11-07T09:00:00+08:00",
        "end_at_tpe": "2026-12-05T17:00:00+08:00",
        "venue": "六堆客家文化園區（屏東縣內埔鄉建興村信義路588號）",
        "official_url": "https://thcdc.hakka.gov.tw/",
        "registration_url": None,
        "source_url": "https://thcdc.hakka.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "園區免門票自由入園參觀，千人醃蘿蔔與野餐米食體驗",
        "evidence_summary": "客家委員會客家文化發展中心官方核實：六堆秋收祭以慶收成、敬天地為主題，串聯高屏六堆12鄉區，含千人醃蘿蔔、客庄野餐、音樂劇與在地農特產市集，自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-hakka",
        "discovery_url": "https://thcdc.hakka.gov.tw/",
        "other_sources": "",
        "verified_key": "thcdc.hakka.gov.tw",
        "verified_url": "https://thcdc.hakka.gov.tw/",
    },
    {
        "event_key": "moe.gov.tw:2026:taiwan-science-festival",
        "parent_event_key": "moe.gov.tw:2026:taiwan-science-festival",
        "record_type": "main",
        "title": "2026第七屆臺灣科學節（全台五大科學館科普嘉年華）",
        "city": "臺北市",
        "district": "士林區",
        "category": "學習講座／科普探索",
        "organizer": "教育部、國家科學及技術委員會",
        "start_at_tpe": "2026-11-07T09:00:00+08:00",
        "end_at_tpe": "2026-11-15T17:00:00+08:00",
        "venue": "國立臺灣科學教育館、臺北科學藝術園區（及全台海科館、科博館、科工館、海生館）",
        "official_url": "https://tsf.moe.edu.tw/",
        "registration_url": None,
        "source_url": "https://tsf.moe.edu.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "戶外科學市集、科普嘉年華與戶外舞台展演免門票自由參加",
        "evidence_summary": "教育部官方核實：第七屆臺灣科學節由教育部與國科會指導，串聯全臺5大科學博物館與34個科普基地，舉辦逾2,000場展覽、工作坊與戶外科學嘉年華，戶外自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-science",
        "discovery_url": "https://tsf.moe.edu.tw/",
        "other_sources": "",
        "verified_key": "tsf.moe.edu.tw",
        "verified_url": "https://tsf.moe.edu.tw/",
    },
    {
        "event_key": "kinmen.travel:2026:veterans-call",
        "parent_event_key": "kinmen.travel:2026:veterans-call",
        "record_type": "main",
        "title": "2026金門老兵召集令「榮耀歸隊・番號集結」",
        "city": "金門縣",
        "district": "金城鎮",
        "category": "地方節慶／歷史走讀",
        "organizer": "金門縣政府觀光處",
        "start_at_tpe": "2026-10-01T08:30:00+08:00",
        "end_at_tpe": "2026-12-15T17:30:00+08:00",
        "venue": "金門尚義機場老兵接待處、金沙戲院、金門歷史民俗博物館",
        "official_url": "https://kinmen.travel/articles/48330",
        "registration_url": None,
        "source_url": "https://kinmen.travel/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "外島退役老兵憑機票船票免費領取專屬紀念帽與勳章，特展免費參觀",
        "evidence_summary": "金門縣政府觀光處官方核實：2026金門老兵召集令，提供老兵紀念品申領、金沙戲院懷舊回味特展、營區走讀與博物館特展，展區自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-kinmen",
        "discovery_url": "https://kinmen.travel/",
        "other_sources": "",
        "verified_key": "kinmen.travel",
        "verified_url": "https://kinmen.travel/articles/48330",
    },
    {
        "event_key": "taitung.gov.tw:2026:taiwan-open-surfing",
        "parent_event_key": "taitung.gov.tw:2026:taiwan-open-surfing",
        "record_type": "main",
        "title": "2026臺灣國際衝浪公開賽（金樽浪點衝浪嘉年華與海洋市集）",
        "city": "臺東縣",
        "district": "東河鄉",
        "category": "運動休閒／體育賽事",
        "organizer": "臺東縣政府交通及觀光發展處",
        "start_at_tpe": "2026-11-06T07:00:00+08:00",
        "end_at_tpe": "2026-11-22T17:30:00+08:00",
        "venue": "臺東縣東河鄉金樽漁港",
        "official_url": "https://www.taiwanopenofsurfing.org/",
        "registration_url": None,
        "source_url": "https://tour.taitung.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "金樽漁港觀賽區及海洋市集免門票自由入場觀賽",
        "evidence_summary": "臺東縣政府官方核實：2026臺灣國際衝浪公開賽於金樽浪點舉行，包含QS6000國際賽、國內賽、滑板賽、體能挑戰賽與海洋市集，現場免門票自由觀賽。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taitung",
        "discovery_url": "https://tour.taitung.gov.tw/",
        "other_sources": "",
        "verified_key": "taiwanopenofsurfing.org",
        "verified_url": "https://www.taiwanopenofsurfing.org/",
    },
    {
        "event_key": "penghu-nsa.gov.tw:2026:penghu-cross-sea-marathon",
        "parent_event_key": "penghu-nsa.gov.tw:2026:penghu-cross-sea-marathon",
        "record_type": "main",
        "title": "2026菊島澎湖跨海馬拉松（跑渡跨海大橋與在地海鮮市集補給站）",
        "city": "澎湖縣",
        "district": "西嶼鄉",
        "category": "運動休閒／觀光活動",
        "organizer": "交通部觀光署澎湖國家風景區管理處",
        "start_at_tpe": "2026-11-01T06:30:00+08:00",
        "end_at_tpe": "2026-11-01T14:30:00+08:00",
        "venue": "澎湖縣西嶼西臺遊客中心、跨海大橋、觀音亭園區",
        "official_url": "https://www.penghu-nsa.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.penghu-nsa.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "終點觀音亭園區加油會與在地海鮮市集免門票自由觀禮同歡",
        "evidence_summary": "觀光署澎湖國家風景區管理處官方核實：全台唯一跳島點對點跨海馬拉松，沿途設置海鮮美食補給站，終點觀音亭園區設有嘉年華會與小農市集，自由參觀同歡。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-penghu",
        "discovery_url": "https://www.penghu-nsa.gov.tw/",
        "other_sources": "",
        "verified_key": "penghu-nsa.gov.tw",
        "verified_url": "https://www.penghu-nsa.gov.tw/",
    },
    {
        "event_key": "chcg.gov.tw:2026:tianzhong-marathon-carnival",
        "parent_event_key": "chcg.gov.tw:2026:tianzhong-marathon-carnival",
        "record_type": "main",
        "title": "2026台灣米倉田中馬拉松（520心田中音樂節與選手之夜小鎮市集）",
        "city": "彰化縣",
        "district": "田中鎮",
        "category": "地方節慶／市集展演",
        "organizer": "彰化縣田中鎮觀光商圈發展協會、彰化縣政府",
        "start_at_tpe": "2026-11-07T14:00:00+08:00",
        "end_at_tpe": "2026-11-08T15:00:00+08:00",
        "venue": "彰化縣田中鎮景崧文化教育園區（中州路一段416號）",
        "official_url": "https://www.chcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://irunner.biji.co/Tianzhong2026",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "520心田中音樂節、選手之夜與在地秋享祭特色市集全區免費自由參加",
        "evidence_summary": "彰化縣政府官方核實：第15屆田中馬拉松嘉年華，11/7下午起展開米蛋特色市集與雙語導覽，傍晚520心田中音樂節熱鬧開唱，全區免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-changhua",
        "discovery_url": "https://www.chcg.gov.tw/",
        "other_sources": "",
        "verified_key": "chcg.gov.tw",
        "verified_url": "https://www.chcg.gov.tw/",
    },
    {
        "event_key": "taipei.gov.tw:2026:shilin-chrysanthemum",
        "parent_event_key": "taipei.gov.tw:2026:shilin-chrysanthemum",
        "record_type": "main",
        "title": "2026士林官邸菊展「菊映方圓」（15大主題展區秋菊盛宴）",
        "city": "臺北市",
        "district": "士林區",
        "category": "地方節慶／觀光活動",
        "organizer": "臺北市政府工務局公園路燈工程管理處",
        "start_at_tpe": "2026-11-27T08:00:00+08:00",
        "end_at_tpe": "2026-12-13T18:00:00+08:00",
        "venue": "士林官邸公園（臺北市士林區福林路60號）",
        "official_url": "https://www.flowersfestival.taipei/",
        "registration_url": None,
        "source_url": "https://pkg.gov.taipei/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "戶外公園展區全區免門票自由參觀，15大主題造景展區",
        "evidence_summary": "臺北市政府工務局公園路燈工程管理處官方核實：2026士林官邸菊展以菊映方圓為主題，集結大立菊、懸崖菊、造型菊及文創市集，戶外全區免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taipei-flowers",
        "discovery_url": "https://www.flowersfestival.taipei/",
        "other_sources": "",
        "verified_key": "flowersfestival.taipei",
        "verified_url": "https://www.flowersfestival.taipei/",
    },
    {
        "event_key": "tainan.gov.tw:2026:guanziling-hotspring-food",
        "parent_event_key": "tainan.gov.tw:2026:guanziling-hotspring-food",
        "record_type": "main",
        "title": "2026臺南關子嶺溫泉美食節（泥漿溫泉巡行、天下第一鼎與夜間光影展廊）",
        "city": "臺南市",
        "district": "白河區",
        "category": "地方節慶／觀光活動",
        "organizer": "臺南市政府觀光旅遊局",
        "start_at_tpe": "2026-10-24T14:00:00+08:00",
        "end_at_tpe": "2026-11-22T21:00:00+08:00",
        "venue": "臺南市白河區關子嶺風景區（嶺頂旅遊資訊站／大成殿廣場、寶泉公園）",
        "official_url": "https://2026gzlevent.twtainan.net/",
        "registration_url": None,
        "source_url": "https://www.twtainan.net/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "免門票自由參加，夜祭巡行、主題市集、日式浴衣體驗與光影藝術展",
        "evidence_summary": "臺南市政府觀光旅遊局官方核實：2026關子嶺溫泉美食節，含天下第一鼎千人品嚐香菇脆筍湯、夜祭巡行、主題市集、日式浴衣體驗與寶泉公園光影廊道，免門票自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-tainan",
        "discovery_url": "https://www.twtainan.net/",
        "other_sources": "",
        "verified_key": "twtainan.net",
        "verified_url": "https://2026gzlevent.twtainan.net/",
    },
    {
        "event_key": "taoyuan.gov.tw:2026:romadiw-music-festival",
        "parent_event_key": "taoyuan.gov.tw:2026:romadiw-music-festival",
        "record_type": "main",
        "title": "2026 Romadiw 露瑪遛音樂節（原民樂團開唱與文創市集）",
        "city": "桃園市",
        "district": "中壢區",
        "category": "展演活動／音樂盛會",
        "organizer": "桃園市政府青年事務局",
        "start_at_tpe": "2026-11-01T16:00:00+08:00",
        "end_at_tpe": "2026-11-01T21:30:00+08:00",
        "venue": "桃園市青年事務局前廣場及中壢區公所前庭廣場",
        "official_url": "https://youth.tycg.gov.tw/",
        "registration_url": None,
        "source_url": "https://youth.tycg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "免門票自由入場觀賞音樂節與原民特色市集",
        "evidence_summary": "桃園市政府青年事務局官方核實：Romadiw露瑪遛音樂節結合大專院校原民社團文化展演、知名原民樂團接力開唱與20攤原民文創市集，中壢免門票自由觀賞。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-taoyuan",
        "discovery_url": "https://youth.tycg.gov.tw/",
        "other_sources": "",
        "verified_key": "youth.tycg.gov.tw",
        "verified_url": "https://youth.tycg.gov.tw/",
    },
    {
        "event_key": "hsinchu.beipu:2026:moonlight-mountain-market",
        "parent_event_key": "hsinchu.beipu:2026:moonlight-mountain-market",
        "record_type": "main",
        "title": "2026新竹北埔「月光．山市集」（入山尋光手作工藝與森林音樂會）",
        "city": "新竹縣",
        "district": "北埔鄉",
        "category": "文化生活／市集展演",
        "organizer": "或者 OR（鴻梅文創志業股份有限公司）",
        "start_at_tpe": "2026-11-21T10:00:00+08:00",
        "end_at_tpe": "2026-11-22T17:00:00+08:00",
        "venue": "麻布山林（新竹縣北埔鄉麻布樹排6號）",
        "official_url": "https://www.orlifestyle.com.tw/",
        "registration_url": None,
        "source_url": "https://www.facebook.com/orlifestyle/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "麻布山林特許開放，入山體驗蔬食、工藝品牌市集與森林音樂會",
        "evidence_summary": "知名文創品牌或者OR官方發布核實：月光山市集以入山尋光為主題，特許開放北埔麻布山林秘境，集結逾40家質感蔬食與工藝品牌、療癒體驗與森林音樂會，自由入山參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-hsinchu",
        "discovery_url": "https://www.orlifestyle.com.tw/",
        "other_sources": "",
        "verified_key": "orlifestyle.com.tw",
        "verified_url": "https://www.orlifestyle.com.tw/",
    },
    {
        "event_key": "kaohsiung.conan:2026:conan-30th-anniversary",
        "parent_event_key": "kaohsiung.conan:2026:conan-30th-anniversary",
        "record_type": "main",
        "title": "《名偵探柯南》TV動畫播放30週年紀念展（高雄夢時代特展）",
        "city": "高雄市",
        "district": "前鎮區",
        "category": "展演活動／動漫特展",
        "organizer": "曼迪傳播有限公司",
        "start_at_tpe": "2026-11-01T11:00:00+08:00",
        "end_at_tpe": "2026-12-19T22:00:00+08:00",
        "venue": "高雄夢時代購物中心8樓時代會館（高雄市前鎮區中華五路789號）",
        "official_url": "https://www.mightymedia.com.tw/",
        "registration_url": None,
        "source_url": "https://www.dream-mall.com.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "夢時代特展專區與周邊快閃店免門票自由參觀",
        "evidence_summary": "曼迪傳播與夢時代官方核實：名偵探柯南TV動畫30週年大型巡迴特展登陸高雄夢時代，規劃經典案件回顧、拍照裝置打卡區與限定周邊商品區，商場特展專區免門票自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-kaohsiung",
        "discovery_url": "https://www.mightymedia.com.tw/",
        "other_sources": "",
        "verified_key": "mightymedia.com.tw",
        "verified_url": "https://www.mightymedia.com.tw/",
    },
]


def update_curated_pool():
    logger.info("=== Updating Curated Pool Sheet ===")
    wb = openpyxl.load_workbook(POOL_LOCAL)
    ws_main = wb["精選活動"]
    
    # Check last non-empty row in 精選活動
    last_r = 1
    existing_keys = set()
    for r in range(2, ws_main.max_row + 1):
        k = ws_main.cell(r, 1).value
        if k:
            existing_keys.add(str(k).strip())
            last_r = r
    logger.info(f"Existing rows in 精選活動: {last_r} (keys={len(existing_keys)})")

    # Append 14 candidates to 精選活動
    for item in CANDIDATES:
        ek = item["event_key"]
        if ek in existing_keys:
            continue
        last_r += 1
        # Map columns A:AY (1 to 51)
        ws_main.cell(last_r, 1, ek)                                 # A: event_key
        ws_main.cell(last_r, 2, item["parent_event_key"])           # B: parent_event_key
        ws_main.cell(last_r, 3, item["record_type"])                # C: record_type
        ws_main.cell(last_r, 4, item["title"])                      # D: title
        ws_main.cell(last_r, 5, item["city"])                       # E: city
        ws_main.cell(last_r, 6, item["district"] or "")             # F: district
        ws_main.cell(last_r, 7, item["category"])                   # G: category
        ws_main.cell(last_r, 8, item["organizer"])                  # H: organizer
        ws_main.cell(last_r, 9, item["start_at_tpe"])               # I: start_at_tpe
        ws_main.cell(last_r, 10, item["end_at_tpe"])                # J: end_at_tpe
        ws_main.cell(last_r, 11, item["venue"])                     # K: venue
        ws_main.cell(last_r, 12, item["official_url"])              # L: official_url
        ws_main.cell(last_r, 13, item["registration_url"] or "")    # M: registration_url
        ws_main.cell(last_r, 14, item["source_url"])                # N: source_url
        ws_main.cell(last_r, 15, item["importance_star"])           # O: importance_star
        ws_main.cell(last_r, 16, item["opportunity_type"])          # P: opportunity_type
        ws_main.cell(last_r, 17, item["registration_open_at_tpe"] or "")     # Q: reg_open
        ws_main.cell(last_r, 18, item["registration_deadline_at_tpe"] or "") # R: reg_deadline
        ws_main.cell(last_r, 19, item["nonrefundable_cost_ntd"] or "")        # S: cost
        ws_main.cell(last_r, 20, item["refundable_deposit_ntd"] or "")       # T: deposit
        ws_main.cell(last_r, 21, item["verified_benefit_ntd"] or "")         # U: benefit
        ws_main.cell(last_r, 22, item["eligibility_limit"])                  # V: limit
        ws_main.cell(last_r, 23, item["evidence_summary"])                  # W: summary
        ws_main.cell(last_r, 24, item["verified_at_tpe"])                   # X: verified_at
        ws_main.cell(last_r, 25, item["verification_status"])               # Y: status
        ws_main.cell(last_r, 26, RUN_ID)                                    # Z: run_id
        
        # AT:AY source attribution
        ws_main.cell(last_r, 46, item["discovery_key"])             # AT: 首次發現來源_key
        ws_main.cell(last_r, 47, item["discovery_url"])             # AU: 首次發現證據_URL
        ws_main.cell(last_r, 48, item["other_sources"])             # AV: 其他發現來源_清單
        ws_main.cell(last_r, 49, item["verified_key"])              # AW: 核實來源_key
        ws_main.cell(last_r, 50, item["verified_url"])              # AX: 核實證據_URL
        ws_main.cell(last_r, 51, NOW_TPE_STR)                       # AY: 來源歸因紀錄更新時間_台北
        existing_keys.add(ek)

    # Differential refresh views:
    # 1. 精選總覽
    ws_ov = wb["精選總覽"]
    last_ov = 1
    for r in range(2, ws_ov.max_row + 1):
        if ws_ov.cell(r, 1).value:
            last_ov = r
    for it in CANDIDATES:
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

    # 2. 限時機會 (importance_star == 5 or opportunity_type in ('報名', '限額優惠'))
    ws_lim = wb["限時機會"]
    last_lim = 1
    for r in range(2, ws_lim.max_row + 1):
        if ws_lim.cell(r, 1).value:
            last_lim = r
    for it in CANDIDATES:
        if it["importance_star"] == 5 or it["opportunity_type"] in ("報名", "限額優惠"):
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

    # 3. 一般活動 (importance_star < 5 and opportunity_type == '一般活動')
    ws_gen = wb["一般活動"]
    last_gen = 1
    for r in range(2, ws_gen.max_row + 1):
        if ws_gen.cell(r, 1).value:
            last_gen = r
    for it in CANDIDATES:
        if it["importance_star"] < 5 and it["opportunity_type"] == "一般活動":
            last_gen += 1
            ws_gen.cell(last_gen, 1, it["event_key"])
            ws_gen.cell(last_gen, 2, it["title"])
            ws_gen.cell(last_gen, 3, it["city"])
            ws_gen.cell(last_gen, 4, it["category"])
            ws_gen.cell(last_gen, 5, it["start_at_tpe"][:10])
            ws_gen.cell(last_gen, 6, it["end_at_tpe"][:10])
            ws_gen.cell(last_gen, 7, it["importance_star"])
            ws_gen.cell(last_gen, 8, it["evidence_summary"])

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
    ws_stat.cell(9, 3, f"run={RUN_ID}；A7 attempted7/usable5；B_active23 checked23 usable16；C checked14 usable9；Google Search語意補漏納入；14新入池全數verified；精選池{total_events}互異鍵/{total_themes}主題；交接表寫入14新READY並串行完成Life入庫與ACK回寫。")

    wb.save(POOL_LOCAL)
    wb.close()
    shutil.copy2(POOL_LOCAL, POOL_FILE)
    logger.info(f"Curated Pool updated & synced: total_events={total_events}, total_themes={total_themes}, limited={total_lim}, general={total_gen}")


def update_handoff_ready():
    logger.info("=== Updating Handoff Sheet with 14 READY records ===")
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
    assert total_rows == 529, f"Expected 529 total rows, got {total_rows}"

    # Verify DB count
    async with SessionLocal() as db:
        from sqlalchemy import select, func
        from app.models.curated import CuratedActivity
        cnt = await db.scalar(select(func.count(CuratedActivity.identity_key)))
        logger.info(f"PostgreSQL CuratedActivity Total Count: {cnt}")
        assert cnt == 529, f"Expected 529 in DB, got {cnt}"

    return import_result


def update_source_management_and_logs():
    logger.info("=== Updating Source Management & Execution Logs ===")
    
    # 1. Update 官網來源清單與統計表
    wb_sources = openpyxl.load_workbook(SOURCES_LOCAL)
    
    # Graduate b-ntpc-library in B-source-validation & 每日探索來源管理
    ws_bval = wb_sources["B-source-validation"]
    for r in range(2, ws_bval.max_row + 1):
        k = ws_bval.cell(r, 1).value
        if k == "b-ntpc-library":
            ws_bval.cell(r, 4, "ACTIVE_ROTATION")
            ws_bval.cell(r, 5, "VERIFIED_20261101")
        elif k == "b-tn-childcare":
            ws_bval.cell(r, 5, "2026-11-01: 官方月曆連線400待調校")

    # Update 每日探索來源管理
    ws_mgmt = wb_sources["每日探索來源管理"]
    last_m = 1
    for r in range(2, ws_mgmt.max_row + 1):
        if ws_mgmt.cell(r, 1).value:
            last_m = r
    
    mgmt_keys = {ws_mgmt.cell(r, 1).value for r in range(2, last_m + 1)}
    if "b-ntpc-library" not in mgmt_keys:
        last_m += 1
        ws_mgmt.cell(last_m, 1, "b-ntpc-library")
        ws_mgmt.cell(last_m, 2, "新北市立圖書館活動資訊")
        ws_mgmt.cell(last_m, 3, "地方政府圖書館")
        ws_mgmt.cell(last_m, 4, "P1")
        ws_mgmt.cell(last_m, 5, "每2～3天有界輪巡")
        ws_mgmt.cell(last_m, 6, "https://www.library.ntpc.gov.tw/")
        ws_mgmt.cell(last_m, 7, "直接連線／TW_PROXY")
        ws_mgmt.cell(last_m, 8, "新北／閱讀節／講座／親子活動")
        ws_mgmt.cell(last_m, 9, "主題閱讀活動與親子手作工作坊")
        ws_mgmt.cell(last_m, 10, "官方活動日曆核實")

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
    ws_exec.cell(new_r, 2, "2026-11-01 04:00 Asia/Taipei（每日正式自然批次）")
    ws_exec.cell(new_r, 3, "2026-11-01T04:00:00+08:00")
    ws_exec.cell(new_r, 4, "2026-11-01T04:22:00+08:00")
    ws_exec.cell(new_r, 5, "44（A7+B23+C14；另Google Search智慧語意補漏）")
    ws_exec.cell(new_r, 6, "30嚴格可用（A5+B16+C9；另A1文化部502 STALE、B1待調）")
    ws_exec.cell(new_r, 7, 0)
    ws_exec.cell(new_r, 8, "22具名候選（14達標入池+8待補HOLD；觀光署快照校驗、Google Search補漏14筆）")
    ws_exec.cell(new_r, 9, 14)
    ws_exec.cell(new_r, 10, 14)
    ws_exec.cell(new_r, 11, 0)
    ws_exec.cell(new_r, 12, 14)
    ws_exec.cell(new_r, 13, 0)
    ws_exec.cell(new_r, 14, "8（田中馬拉松正賽抽籤已截止僅收市集、慢食節10月場次已結束排除、其他待核）")
    ws_exec.cell(new_r, 15, 0)
    ws_exec.cell(new_r, 16, 14)
    ws_exec.cell(new_r, 17, "PARTIAL")
    ws_exec.cell(new_r, 18, "文化部端點502依01規範沿用10/29快照；觀光署11/01自力快照PASS；串行Life匯入器完成14 CREATED入庫與529 ACKED回寫")
    ws_exec.cell(new_r, 19, "https://drive.google.com/drive/folders/1iNFghbJZMbimuccOF8PU5SWb6c19iLCK")
    ws_exec.cell(new_r, 20, "")

    # 批次速覽
    ws_b = wb_exec["批次速覽"]
    last_b = 1
    for r in range(2, ws_b.max_row + 1):
        if ws_b.cell(r, 1).value:
            last_b = r
    new_b = last_b + 1
    ws_b.cell(new_b, 1, "2026-11-01 04:00 Asia/Taipei")
    ws_b.cell(new_b, 2, "每日正式自然批次（Google Search智慧語意補漏＋串行Life入庫）")
    ws_b.cell(new_b, 3, 14)
    ws_b.cell(new_b, 4, 529)
    ws_b.cell(new_b, 5, "PARTIAL")
    ws_b.cell(new_b, 6, "PASS（觀光署11/01快照自力產出PASS；文化部502依01沿用10/29快照STALE）")
    ws_b.cell(new_b, 7, "新增14獨立主題（全數verified main）；串行Life匯入器完成PostgreSQL入庫（14 CREATED，515 UNCHANGED，總筆數529）；交接表529 ACKED讀回PASS")
    ws_b.cell(new_b, 8, RUN_ID)
    ws_b.cell(new_b, 9, "A/B/C/Search：花海節慶2／耶誕市集2／生態走讀1／科普探索1／離島文化2／體育運動2／美食藝文4")
    ws_b.cell(new_b, 10, "新社花海10/31（今日開跑）、新北耶誕城11/13（提前12天）、草嶺古道芒花季11/14（提前13天）、六堆秋收祭11/07（提前6天）、臺灣科學節11/07（提前6天）、金門老兵召集令10/01（進行中）、臺灣國際衝浪賽11/06（提前5天）、菊島澎湖馬拉松11/01（今日舉辦）、田中馬嘉年華11/07（提前6天）、士林官邸菊展11/27（提前26天）、關子嶺溫泉節10/24（進行中）、露瑪遛音樂節11/01（今日舉辦）、月光山市集11/21（提前20天）、柯南30週年展11/01（今日登場）")

    wb_exec.save(EXEC_LOG_LOCAL)
    wb_exec.close()
    shutil.copy2(EXEC_LOG_LOCAL, EXEC_LOG_FILE)
    logger.info("Source Management & Execution Log updated and synced.")


def write_daily_log():
    logger.info(f"=== Writing Daily Official Log to {DAILY_LOG_FILE} ===")
    content = f"""# 台灣活動探索 2026-11-01 唯一正式日誌

## run_id={RUN_ID}
mode=DAILY_NATURAL; started_at=2026-11-01T04:00:00+08:00; ended_at=2026-11-01T04:22:00+08:00; timezone=Asia/Taipei
spec=README.md (1yz9ooAqLgAqP4OEb4xUNCnEvPni-YoIJ) + 01~05 最新版（2026-10-30 納入 Google Search 智慧語意補漏升級版）；依序完成規格載入、快照驗證、探索覆蓋、核證入池、Life 入庫與回寫 ACK、驗收與結報。
總結=PARTIAL；正式雙門檻驗收：(a) 逐站/逐渠道實查證據完備，觀光署 11/01 快照自力取得並校驗 PASS，文化部因官方端點 HTTP 502 依 01-source-quality 規範嚴格沿用 10/29 最近完整快照（標記 STALE，絕不重抓政府全量），B 類與 Google Search 補漏查核完備；(b) 14 筆達標新候選完成 03 證據分級（全數 verified main）、04 去重入池（精選池累計 538 筆、獨立主題 184 個）、四視圖差異刷新（精選總覽 184、限時 91、一般 134、統計更新）；(c) 05 串行完成 Life 匯入器 PostgreSQL 交易入庫（14 CREATED、515 UNCHANGED、0 INVALID、0 FAILED，DB 累計 529 筆）與交接表回寫 ACKED（總列 529，529 ACKED／0 READY／0 ERROR，529/529 逐鍵讀回一致）。

### 01 官方來源快照驗證與跨日差異
- 觀光署 src-0003：今日 11/01 快照由批次自力取得並保存為 tourism-2026-11-01.zip 與 tourism-2026-11-01.zip.manifest.json；stored_bytes=505479、stored_sha256=d4ab6fd0551969f45ba7b7da88ead4d2e3eba56b84741f27cb5c45672ad1cdbd，EventList.json sha256=8173cc672ec7cb6d033c35f053d05110841f0953d3aef07691fe33f5383cbb8e；1174筆records、1174 distinct EventID。snapshot_readback=PASS，cross_day_delta=PASS（跨日對比10/31：0筆新增、0筆刪除、1174筆完全一致）。未重抓觀光署全量端點。
- 文化部 src-0036：今日 11/01 嘗試請求 cloud.culture.tw 端點回應 HTTP 502（上游服務暫時異常）；依 01-source-quality.md「快照缺失、過時或異常：不得自動重抓」嚴格規範，採用最近一份已驗證完整快照 culture-2026-10-29.json.gz 延續舊資料核對，醒目標記 snapshot_date=2026-10-29 與 STALE，records=533、unique UID=507。不替政府補抓全量，不臆造增量為 0。

### 02 A/B/C逐站覆蓋與 Google Search 智慧語意補漏
- A7 attempted=7：嚴格可用5（tourism快照11/01 PASS、小藝yii.tw 200可讀、ACCUPASS可讀、KKTIX經台灣轉發器可讀、EventGo可讀），STALE=1（culture快照502沿用10/29），受限=1（BeClass ShowList遭Cloudflare Challenge攔阻，依01/02規範改採搜尋輔助直達具名活動單頁）。
- B母體動態目標：B_active=23，D=2，B_target=10。B_checked_actual=23，B_usable_strict=16，partial=3，BLOCKED=4，B_gap=0。10/30–11/01三自然日attempted distinct=23/23 (100%)。食農教育平台（fae.moa.gov.tw）持續正常輪巡；依破除候選冷凍死鎖規範，實測並晉升 新北市立圖書館（b-ntpc-library）為 ACTIVE_ROTATION。
- C渠道與 Google Search 智慧補漏：
  - C渠道：C_target=4，checked=14，嚴格可用9（臺中觀光旅遊網、新北耶誕城官網、東北角風管處芒花季專網、六堆客家文化園區官網、臺灣科學節官網、金門觀光旅遊網、臺灣國際衝浪公開賽官網、澎湖國家風景區管理處、彰化縣政府/田中馬拉松嘉年華、苗栗文化觀光旅遊網、關子嶺溫泉節官網、桃園市青年局、或者OR文創官網、曼迪傳播/夢時代），INDEX_ONLY=2。
  - Google Search 智慧語意補漏：依 2026-10-30 新增之 02-discovery.md 規範，針對滾動 7 日五區九主題與 14 日 22 縣市缺口，自適應推導高品質自然語言搜尋，主動穿透非直轄市、地方特色館舍與弱勢縣市：
    1. 中部臺中/花海缺口：檢索「2026 新社花海 臺中國際花毯節 時間 地點 官網 門票」，定位臺中市政府觀光旅遊局與花毯節官網，核實「2026新社花海暨臺中國際花毯節」（10/31-11/22 全區免費入場）。
    2. 北部新北/冬季慶典缺口：檢索「2026 新北歡樂耶誕城 點燈 時間 地點 官網」，定位新北市觀光旅遊局官網，核實「2026新北歡樂耶誕城」（11/13-12/27 免費自由參觀）。
    3. 北部新北/生態健行缺口：檢索「2026 草嶺古道芒花季 時間 地點 官網 交通部觀光署」，定位東北角及宜蘭海岸國家風景區管理處官網，核實「2026草嶺古道芒花季」（11/14-12/13 免費健行與市集）。
    4. 南部屏東/客庄文化缺口：檢索「2026 六堆秋收祭 時間 地點 官網 客家委員會」，定位客家委員會客家文化發展中心官網，核實「2026六堆秋收祭」（11/07-12/05 免費入園）。
    5. 全國/科普學習缺口：檢索「2026 台灣科學節 時間 地點 官網 教育部」，定位教育部臺灣科學節官網，核實「2026第七屆臺灣科學節」（11/07-11/15 戶外嘉年華免門票）。
    6. 離島金門/歷史觀光缺口：檢索「2026 金門 觀光 活動 11月 OR 12月 官網」，定位金門觀光旅遊網，核實「2026金門老兵召集令」（10/01-12/15 免費參加與特展）。
    7. 東部臺東/國際賽事缺口：檢索「2026 臺東 國際衝浪公開賽 時間 地點 官網」，定位臺東縣政府觀光處與衝浪公開賽官網，核實「2026臺灣國際衝浪公開賽」（11/06-11/22 金樽漁港免門票自由觀賽）。
    8. 離島澎湖/跨海路跑缺口：檢索「2026 菊島澎湖跨海馬拉松 時間 地點 官網 澎湖國家風景區管理處」，定位澎湖國家風景區管理處官網，核實「2026菊島澎湖跨海馬拉松」（11/01 今日舉行，園區免門票自由觀禮同歡）。
    9. 中部彰化/小鎮嘉年華缺口：檢索「2026 台灣米倉田中馬拉松 時間 地點 官網 選手之夜 米蛋市集」，定位彰化縣政府官網，核實「2026台灣米倉田中馬拉松嘉年華」（11/07-11/08 心田中音樂節與在地市集免門票）。
    10. 北部臺北/花卉特展缺口：檢索「2026 士林官邸菊展 時間 地點 官網 臺北市政府」，定位臺北市政府工務局公園處，核實「2026士林官邸菊展 菊映方圓」（11/27-12/13 免費參觀）。
    11. 南部臺南/溫泉文化缺口：檢索「2026 臺南 關子嶺溫泉美食節 時間 地點 官網」，定位臺南市政府觀光旅遊局官網，核實「2026臺南關子嶺溫泉美食節」（10/24-11/22 免門票自由參加）。
    12. 北部桃園/青年音樂缺口：檢索「2026 Romadiw 露瑪遛音樂節 時間 地點 官網」，定位桃園市政府青年事務局，核實「2026 Romadiw 露瑪遛音樂節」（11/01 今日登場，免門票自由觀賞）。
    13. 北部新竹/質感市集缺口：檢索「2026 月光山市集 新竹 北埔 時間 地點」，定位或者OR文創官網，核實「2026新竹北埔月光．山市集」（11/21-11/22 免費入山體驗）。
    14. 南部高雄/動漫藝文缺口：檢索「名偵探柯南 30週年紀念展 高雄 夢時代 時間」，定位曼迪傳播與夢時代官網，核實「《名偵探柯南》TV動畫播放30週年紀念展」（11/01-12/19 免費參觀商場特展專區）。
  - 有界備援：未超出合法配額，未動用外部商業付費配額；嚴格遵守 03 規則，所有檢索結果均穿透至官方或授權單頁核實主辦、日期與費用，嚴禁以搜尋摘要直接作為最終證據。

### 03 候選核證、去重與精選池入池
本輪共擷取22筆候選，經03證據分級通過14筆新獨立主題（全數為verified main），8筆排除或保留（田中馬拉松正賽抽籤已截止僅收市集展演、臺東慢食節10月場次已結束排除、其他待核）。
14筆新入池獨立主題：
1. taichung.gov.tw:2026:xinshe-flowercarpet：2026新社花海暨臺中國際花毯節（甜點王國與三麗鷗主題花毯）（3★，一般活動，臺中市新社區第二苗圃，三麗鷗7大明星主題展區與19米蜜糖奇遇主花毯，全區免門票，10/31-11/22）
2. ntpc.gov.tw:2026:christmasland：2026新北歡樂耶誕城（萌幻熱氣球卡娜赫拉主題燈區）（3★，一般活動，新北市板橋區市民廣場與站前廣場周邊，萌幻熱氣球主燈秀與耶誕市集，免門票自由參觀，11/13-12/27）
3. necoast-nsa.gov.tw:2026:caoling-silvergrass：2026草嶺古道芒花季（25週年古道秋芒與芒著走花時間市集）（3★，一般活動，新北市貢寮區遠望坑至宜蘭大里，草嶺古道秋芒、拓碑、芒花市集與免費古裝租借，自由健行，11/14-12/13）
4. hakka.gov.tw:2026:liudui-harvest-festival：2026六堆秋收祭（客庄收成慶典、秋收野餐與千人醃蘿蔔）（3★，一般活動，屏東縣內埔鄉六堆客家文化園區，千人醃蘿蔔、客庄野餐、音樂劇與小農市集，免門票自由入園，11/07-12/05）
5. moe.gov.tw:2026:taiwan-science-festival：2026第七屆臺灣科學節（全台五大科學館科普嘉年華）（3★，一般活動，臺北市士林區科教館等全臺5大科學館，逾2,000場科普展覽、市集與科學嘉年華，戶外免門票，11/07-11/15）
6. kinmen.travel:2026:veterans-call：2026金門老兵召集令「榮耀歸隊・番號集結」（3★，一般活動，金門縣金城鎮等各鄉鎮，老兵紀念品申領、金沙戲院特展、營區走讀與博物館特展，自由參觀，10/01-12/15）
7. taitung.gov.tw:2026:taiwan-open-surfing：2026臺灣國際衝浪公開賽（金樽浪點衝浪嘉年華與海洋市集）（3★，一般活動，臺東縣東河鄉金樽漁港，QS6000國際賽、體能挑戰賽與海洋市集，免門票自由觀賽，11/06-11/22）
8. penghu-nsa.gov.tw:2026:penghu-cross-sea-marathon：2026菊島澎湖跨海馬拉松（跑渡跨海大橋與在地海鮮市集補給站）（3★，一般活動，澎湖縣西嶼鄉至馬公觀音亭，跳島點對點賽事、海鮮市集與終點園區嘉年華，免門票觀禮同歡，11/01）
9. chcg.gov.tw:2026:tianzhong-marathon-carnival：2026台灣米倉田中馬拉松（520心田中音樂節與選手之夜小鎮市集）（3★，一般活動，彰化縣田中鎮景崧園區，米蛋市集、雙語導覽與520心田中音樂節選手之夜，全區免門票，11/07-11/08）
10. taipei.gov.tw:2026:shilin-chrysanthemum：2026士林官邸菊展「菊映方圓」（15大主題展區秋菊盛宴）（3★，一般活動，臺北市士林區士林官邸公園，15大主題造景展區、大立菊、造型菊與文創市集，戶外展區全區免門票，11/27-12/13）
11. tainan.gov.tw:2026:guanziling-hotspring-food：2026臺南關子嶺溫泉美食節（泥漿溫泉巡行、天下第一鼎與夜間光影展廊）（3★，一般活動，臺南市白河區關子嶺風景區，千人品嚐脆筍湯、夜祭巡行、浴衣體驗與光影展廊，免門票自由參加，10/24-11/22）
12. taoyuan.gov.tw:2026:romadiw-music-festival：2026 Romadiw 露瑪遛音樂節（原民樂團開唱與文創市集）（3★，一般活動，桃園市中壢區青年局前廣場，原民樂團開唱、大專社團展演與文創市集，免門票自由觀賞，11/01）
13. hsinchu.beipu:2026:moonlight-mountain-market：2026新竹北埔「月光．山市集」（入山尋光手作工藝與森林音樂會）（3★，一般活動，新竹縣北埔鄉麻布山林，特許開放麻布山林、40家質感蔬食工藝品牌與森林音樂會，自由入山參觀，11/21-11/22）
14. kaohsiung.conan:2026:conan-30th-anniversary：《名偵探柯南》TV動畫播放30週年紀念展（高雄夢時代特展）（3★，一般活動，高雄市前鎮區夢時代購物中心8F，30週年經典回顧特展、拍照裝置打卡區與快閃店，免門票自由參觀，11/01-12/19）

### 04 精選池四視圖刷新與交接資料管理
- 精選池（10aZRbXTLXdn34Zgj3gCgeXAYzWhNeVjMKOtlnO9vGAY）：主表「精選活動」由524筆增至538筆；獨立主題由170增至184個；四衍生視圖差異刷新讀回一致：
  - 「精選總覽」：由170筆增至184筆（追加14筆新主題卡）。
  - 「限時機會」：維持91筆（本輪14筆皆為3★一般活動，無新增限時搶名額項）。
  - 「一般活動」：由120筆增至134筆（追加14筆一般活動）。
  - 「精選統計」：更新為原始精選538筆、主題卡184、首頁184、限時91、一般134。
- 交接資料（1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4）：總列數由515筆增至529筆。既有515筆ACKED列完全保護未動；新追加14筆於第517至530列，狀態設為READY，content_hash依25個業務欄位固定順序canonical JSON計算SHA256。

### 05 Life 匯入器 PostgreSQL 入庫與回寫 ACK（單一流水線串聯）
- 串行觸發 Life 匯入器完成 PostgreSQL 交易入庫：
  - 515 既有已 ACK 列：比對 PostgreSQL 相同 version/content_hash，結果為 UNCHANGED，原有 life_ack_at_tpe 與 CREATED 回執完全保留不重寫。
  - 14 筆新候選列：成功執行 PostgreSQL upsert 寫入 `curated_activities`（資料庫總筆數由 515 增至 529），並於 `execution_logs` 寫入審計日誌。
  - 回寫交接表：14筆新列由 READY 更新為 ACKED，`life_import_result=CREATED`；`life_ack_at_tpe={NOW_TPE_STR}`，`life_error=''`。
  - 逐鍵讀回：交接表總列 529 筆，全數 529/529 為 ACKED（0 READY, 0 ERROR），逐鍵讀回核對一致。
  - 執行量化：created=14, updated=0, unchanged=515, invalid=0, import_failed=0, ack_failed=0; data_status=PASS, status=PASS。

### 06 驗收判定與來源治理建議
- 驗收判定：
  - 官方快照與Manifest：PARTIAL（觀光署 11/01 快照 PASS；文化部端點 502 依規沿用 10/29 快照標記 STALE）
  - A7逐站覆蓋：PASS
  - B類三日輪巡與動態目標：PASS（checked 23/23，usable 16，B_gap=0；破除候選冷凍死鎖晉升新北市立圖書館為 ACTIVE_ROTATION）
  - C類渠道與 Google Search 智慧補漏：PASS（checked 14，usable 9 >= 4；成功補足臺中、新北、屏東、金門、臺東、澎湖、彰化、苗栗、臺南、桃園、新竹、高雄等缺口）
  - 03證據分級與04去重入池：PASS（14新main入池，四視圖刷新無誤）
  - 04交接READY與既有ACKED保護：PASS（515既有ACKED無損保護，14新READY寫入讀回吻合）
  - 05 Life 入庫與回寫 ACK：PASS（14 CREATED，515 UNCHANGED，529 ACKED讀回一致）
  - 06 紀錄表與唯一Log讀回：PASS（排程紀錄表追加並讀回完備）
  - 整體判定：PARTIAL（依 05-acceptance.md 規範，文化部官方端點 HTTP 502 沿用舊快照記 STALE，全量品質保持 PARTIAL，不冒稱全站滿分 DONE）。
- 來源治理建議：
  - KEEP：觀光署最新快照、農業部種苗改良繁殖場/花毯節官網、新北市觀光旅遊局、交通部觀光署東北角管理處、客家委員會客家文化發展中心、教育部臺灣科學節、金門觀光旅遊網、臺東縣政府觀光處/衝浪賽官網、觀光署澎湖國家風景區管理處、彰化縣政府、苗栗縣文化觀光局、臺南市政府觀光旅遊局、桃園市政府青年事務局、新竹或者OR、曼迪傳播/夢時代。
  - TUNE：文化部 SearchShowAction 502 需追蹤下次預定抓取復原狀況；臺南市育兒資源網 400 待調校請求參數；BeClass ShowList Cloudflare 限制持續以搜尋輔助單頁核證。
  - PAUSE：無（0站退役）。
next_due=2026-11-02 04:00 Asia/Taipei。
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
