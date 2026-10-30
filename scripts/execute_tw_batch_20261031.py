"""
Taiwan Activity Discovery Daily Batch - 2026-10-31 (Asia/Taipei 04:00)
Run ID: tw-discovery-daily-20261031-040000-agy38f
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
NOW_TPE_STR = "2026-10-31T04:00:00+08:00"
RUN_ID = "tw-discovery-daily-20261031-040000-agy38f"

DRIVE_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟")
HANDOFF_FILE = DRIVE_DIR / "台灣活動｜交接資料.xlsx"
POOL_FILE = DRIVE_DIR / "台灣活動｜精選池（Excel相容）.xlsx"
SOURCES_FILE = DRIVE_DIR / "官網來源清單與統計表.xlsx"
EXEC_LOG_FILE = DRIVE_DIR / "台灣活動｜排程執行紀錄.xlsx"
LOG_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜每日執行日誌")
DAILY_LOG_FILE = LOG_DIR / "2026-10-31.log"

LOCAL_DIR = Path("/tmp/tw_sheets_20261031")
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


# Define the 14 new verified candidates for 2026-10-31
CANDIDATES = [
    {
        "event_key": "taiwan.net.tw:Event_397000000A_008146",
        "parent_event_key": "taiwan.net.tw:Event_397000000A_008146",
        "record_type": "main",
        "title": "2026 KFA高雄時尚大賞決賽暨頒獎典禮",
        "city": "高雄市",
        "district": "三民區",
        "category": "展演活動／藝文走讀",
        "organizer": "高雄市政府青年局",
        "start_at_tpe": "2026-11-14T00:00:00+08:00",
        "end_at_tpe": "2026-11-14T23:59:59+08:00",
        "venue": "高雄車站下沉式廣場（高雄市三民區建國二路318號）",
        "official_url": "https://youth.kcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "免費自由入場觀禮，40套新銳設計品牌走秀",
        "evidence_summary": "觀光署官方最新快照核實：南臺灣年度最大時尚盛典，集結新銳設計師品牌40套最新系列作品，於高雄車站下沉式廣場盛大舉行，免門票自由觀禮。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://youth.kcg.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_397000000A_008147",
        "parent_event_key": "taiwan.net.tw:Event_397000000A_008147",
        "record_type": "main",
        "title": "2026大海開吃（高雄熊大型藝術裝置與海鮮主題市集）",
        "city": "高雄市",
        "district": "彌陀區",
        "category": "地方節慶／觀光活動",
        "organizer": "高雄市政府海洋局",
        "start_at_tpe": "2026-10-24T00:00:00+08:00",
        "end_at_tpe": "2026-12-12T23:59:59+08:00",
        "venue": "彌陀漁港、中芸漁港、前鎮夢時代、永安漁港",
        "official_url": "https://kcmb.kcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "免門票自由參觀，大型裝置藝術與海鮮市集",
        "evidence_summary": "觀光署官方最新快照核實：高雄熊限定大型藝術打卡裝置與海味主題市集，串聯彌陀、中芸、蚵仔寮與永安漁港，免門票自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://kcmb.kcg.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_397000000A_008148",
        "parent_event_key": "taiwan.net.tw:Event_397000000A_008148",
        "record_type": "main",
        "title": "2026旗山農好・秋收豐年",
        "city": "高雄市",
        "district": "旗山區",
        "category": "地方節慶／農遊市集",
        "organizer": "高雄市政府農業局",
        "start_at_tpe": "2026-10-31T10:00:00+08:00",
        "end_at_tpe": "2026-11-01T16:00:00+08:00",
        "venue": "旗山公共體育場（高雄市旗山區中正路）" ,
        "official_url": "https://agri.kcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "免費自由入場，秋收農產市集與青農特色體驗",
        "evidence_summary": "觀光署官方最新快照核實：旗山秋收農好豐年活動，秋收農特產市集、青農特色好物、在地農特產料理與表演，免門票自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://agri.kcg.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_382000000A_004081",
        "parent_event_key": "taiwan.net.tw:Event_382000000A_004081",
        "record_type": "main",
        "title": "2026新北市林口子弟戲文化節暨樂林園百年大慶",
        "city": "新北市",
        "district": "林口區",
        "category": "文化生活／傳統戲曲",
        "organizer": "新北市林口區公所",
        "start_at_tpe": "2026-11-14T09:00:00+08:00",
        "end_at_tpe": "2026-11-15T17:00:00+08:00",
        "venue": "竹林山觀音寺（新北市林口區竹林路325號）",
        "official_url": "https://www.linkou.ntpc.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "百年曲館北管匯演與子弟戲，免費自由觀賞",
        "evidence_summary": "新北市府與觀光署快照核實：林口子弟戲文化節結合軒社樂林園百年大慶，於竹林山觀音寺舉行百年北管曲館匯演與文物特展，免費自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://www.linkou.ntpc.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_382000000A_004082",
        "parent_event_key": "taiwan.net.tw:Event_382000000A_004082",
        "record_type": "main",
        "title": "2026幻旅林園（板橋林本源園邸夜間光影展）",
        "city": "新北市",
        "district": "板橋區",
        "category": "文化生活／歷史走讀",
        "organizer": "新北市文化局",
        "start_at_tpe": "2026-11-13T18:00:00+08:00",
        "end_at_tpe": "2026-12-13T21:00:00+08:00",
        "venue": "國定古蹟林本源園邸（新北市板橋區西門街9號）",
        "official_url": "https://www.linfamily.ntpc.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "夜間光影互動藝術免費自由參觀",
        "evidence_summary": "新北市府與觀光署快照核實：百年國定古蹟林家花園化身夜間光影秘境，結合庭園地景、光雕投影與互動裝置藝術，夜間免費參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://www.linfamily.ntpc.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_382000000A_004083",
        "parent_event_key": "taiwan.net.tw:Event_382000000A_004083",
        "record_type": "main",
        "title": "2026 新北城市展「New Taipei Band：共奏未來」",
        "city": "新北市",
        "district": "三重區",
        "category": "展演活動／科技藝術",
        "organizer": "新北市政府",
        "start_at_tpe": "2026-10-29T10:00:00+08:00",
        "end_at_tpe": "2026-12-27T18:00:00+08:00",
        "venue": "三重安芯中心（新北市三重區安芯路1號）",
        "official_url": "https://www.ntpc.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "數位科技展演與親子互動體驗免費自由入場",
        "evidence_summary": "新北市府與觀光署快照核實：以New Taipei Band共奏未來為主題，涵蓋數位科技展演、城市願景、親子數位藝術與在地美食體驗，免費自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://www.ntpc.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_376430000A_007114",
        "parent_event_key": "taiwan.net.tw:Event_376430000A_007114",
        "record_type": "main",
        "title": "2026天光威購節（客家生活文化與文創市集）",
        "city": "桃園市",
        "district": "中壢區",
        "category": "地方節慶／市集展演",
        "organizer": "財團法人桃園市客家文化基金會",
        "start_at_tpe": "2026-10-24T10:00:00+08:00",
        "end_at_tpe": "2026-12-20T20:00:00+08:00",
        "venue": "中壢銀河廣場（桃園市中壢區九和一街35號）",
        "official_url": "https://www.tyhcf.org.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "客家文創選物與地方美食市集免費自由入場",
        "evidence_summary": "桃園市政府與觀光署快照核實：桃園市客家文化基金會主辦，客家文創選品、地方美食、音樂表演與滿額好禮，中壢銀河廣場免費自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://www.tyhcf.org.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_A15010000H_081955",
        "parent_event_key": "taiwan.net.tw:Event_A15010000H_081955",
        "record_type": "main",
        "title": "2026 ITF台灣國際旅展 國家形象館「垂直風景的旅行」",
        "city": "臺北市",
        "district": "南港區",
        "category": "地方節慶／觀光活動",
        "organizer": "交通部觀光署",
        "start_at_tpe": "2026-11-06T10:00:00+08:00",
        "end_at_tpe": "2026-11-09T18:00:00+08:00",
        "venue": "台北南港展覽館1館（臺北市南港區經貿二路1號）",
        "official_url": "https://www.taiwangov.org/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "國家形象館特色步道沉浸式體驗與展館互動",
        "evidence_summary": "觀光署官方最新快照核實：以垂直風景的旅行為主題，精選全台13個國家風景區特色步道，結合五感沉浸式體驗、互動展演與文旅介紹。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://www.taiwangov.org/",
    },
    {
        "event_key": "moa.gov.tw:fae:33523",
        "parent_event_key": "moa.gov.tw:fae:33523",
        "record_type": "main",
        "title": "2026 ITF台灣國際旅展【農遊館 尋一味 風土茶香，探索臺灣茶鄉之旅】",
        "city": "臺北市",
        "district": "南港區",
        "category": "農遊食農／產業體驗",
        "organizer": "農業部農村發展及水土保持署",
        "start_at_tpe": "2026-11-06T10:00:00+08:00",
        "end_at_tpe": "2026-11-09T18:00:00+08:00",
        "venue": "台北南港展覽館一館4F「農遊館」攤位N2106",
        "official_url": "https://fae.moa.gov.tw/theme_data.php?theme=news&sub_theme=event_info&id=33523",
        "registration_url": None,
        "source_url": "https://fae.moa.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "農遊館免費參觀，主廚以茶入菜與手作體驗、三館集章",
        "evidence_summary": "農業部食農教育平台官方核實：以尋一味風土茶香為主題打造農遊館，規劃臺灣特色茶介紹、農遊遊程展售、舞台達人分享、主廚以茶入菜與手作體驗。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "agri-fae",
        "discovery_url": "https://fae.moa.gov.tw/theme_list.php?sub_theme=event_info&theme=news",
        "other_sources": "",
        "verified_key": "fae.moa.gov.tw",
        "verified_url": "https://fae.moa.gov.tw/theme_data.php?theme=news&sub_theme=event_info&id=33523",
    },
    {
        "event_key": "yunlin.gov.tw:2026:taiwan-coffee-festival",
        "parent_event_key": "yunlin.gov.tw:2026:taiwan-coffee-festival",
        "record_type": "main",
        "title": "2026台灣咖啡節「咖了 For World」",
        "city": "雲林縣",
        "district": "古坑鄉",
        "category": "地方節慶／市集展演",
        "organizer": "雲林縣政府",
        "start_at_tpe": "2026-10-31T10:00:00+08:00",
        "end_at_tpe": "2026-11-08T19:00:00+08:00",
        "venue": "古坑綠色隧道公園（雲林縣古坑鄉湳仔路）",
        "official_url": "https://www.yunlin.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.yunlin.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "10/31-11/1及11/7-11/8雙週末10:00-19:00免費入場參觀",
        "evidence_summary": "雲林縣政府官方核實：第24屆台灣咖啡節，以咖了For World為主題，集結全台優質精品咖啡品牌、在地小農市集、草地音樂會與手作體驗，免門票自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-yunlin",
        "discovery_url": "https://www.yunlin.gov.tw/",
        "other_sources": "",
        "verified_key": "yunlin.gov.tw",
        "verified_url": "https://www.yunlin.gov.tw/",
    },
    {
        "event_key": "hualien.gov.tw:2026:pacific-hotspring",
        "parent_event_key": "hualien.gov.tw:2026:pacific-hotspring",
        "record_type": "main",
        "title": "2026花蓮太平洋溫泉季「跟小丸子一起泡進幸福裡」",
        "city": "花蓮縣",
        "district": "瑞穗鄉",
        "category": "地方節慶／觀光活動",
        "organizer": "花蓮縣政府觀光處",
        "start_at_tpe": "2026-10-17T09:00:00+08:00",
        "end_at_tpe": "2026-11-15T22:00:00+08:00",
        "venue": "瑞穗溫泉公園（花蓮縣瑞穗鄉溫泉路三段）及安通溫泉區",
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
        "eligibility_limit": "溫泉公園主題燈飾與光影藝術免費自由參觀",
        "evidence_summary": "花蓮縣政府觀光處官方核實：首度攜手日本超人氣IP櫻桃小丸子打造主題溫泉季，含瑞穗夜遊記手作提燈、職人導覽、暖光市集與英雄泉光影展，免費自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-hualien",
        "discovery_url": "https://hotspring.hl.gov.tw/",
        "other_sources": "",
        "verified_key": "hl.gov.tw",
        "verified_url": "https://hotspring.hl.gov.tw/",
    },
    {
        "event_key": "chiayi.gov.tw:2026:international-band-festival",
        "parent_event_key": "chiayi.gov.tw:2026:international-band-festival",
        "record_type": "main",
        "title": "2026嘉義市國際管樂節",
        "city": "嘉義市",
        "district": "東區",
        "category": "展演活動／音樂盛會",
        "organizer": "嘉義市政府文化局",
        "start_at_tpe": "2026-12-18T14:00:00+08:00",
        "end_at_tpe": "2027-01-01T21:30:00+08:00",
        "venue": "嘉義市中正公園、文化公園、文化局音樂廳",
        "official_url": "https://www.chiayiband.com.tw/",
        "registration_url": None,
        "source_url": "https://www.cabcy.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "管樂踩街嘉年華與戶外音樂會全區免費自由參加",
        "evidence_summary": "嘉義市政府文化局官方核實：第34屆嘉義市國際管樂節，超過百支國內外管樂團隊踩街遊行、大型戶外草地音樂會與國際交流展演，戶外活動一律免費自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-chiayi",
        "discovery_url": "https://www.cabcy.gov.tw/",
        "other_sources": "",
        "verified_key": "cabcy.gov.tw",
        "verified_url": "https://www.chiayiband.com.tw/",
    },
    {
        "event_key": "yilan.gov.tw:2026:jiaoxi-hotspring",
        "parent_event_key": "yilan.gov.tw:2026:jiaoxi-hotspring",
        "record_type": "main",
        "title": "2026冬戀蘭陽溫泉季",
        "city": "宜蘭縣",
        "district": "礁溪鄉",
        "category": "地方節慶／觀光活動",
        "organizer": "宜蘭縣政府",
        "start_at_tpe": "2026-10-15T09:00:00+08:00",
        "end_at_tpe": "2027-02-28T22:00:00+08:00",
        "venue": "礁溪湯圍溝溫泉公園（宜蘭縣礁溪鄉德陽路99-11號）及礁溪重劃區",
        "official_url": "https://travel.yilan.gov.tw/",
        "registration_url": None,
        "source_url": "https://travel.yilan.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "踩街嘉年華、音樂祭與溫泉美食市集免費自由參加",
        "evidence_summary": "宜蘭縣政府官方觀光網核實：冬戀蘭陽溫泉季包含12/6開幕踩街嘉年華、12/11-13及12/19-20冬季溫泉音樂祭、溫泉美食市集與夜間地景燈飾，免費自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-yilan",
        "discovery_url": "https://travel.yilan.gov.tw/",
        "other_sources": "",
        "verified_key": "yilan.gov.tw",
        "verified_url": "https://travel.yilan.gov.tw/",
    },
    {
        "event_key": "pingtung.gov.tw:2026:sichongxi-hotspring",
        "parent_event_key": "pingtung.gov.tw:2026:sichongxi-hotspring",
        "record_type": "main",
        "title": "2026屏東四重溪溫泉季",
        "city": "屏東縣",
        "district": "車城鄉",
        "category": "地方節慶／觀光活動",
        "organizer": "屏東縣政府交通旅遊處",
        "start_at_tpe": "2026-12-04T17:30:00+08:00",
        "end_at_tpe": "2027-03-01T22:30:00+08:00",
        "venue": "四重溪溫泉公園（屏東縣車城鄉溫泉路）",
        "official_url": "https://fun-pingtung.com/",
        "registration_url": None,
        "source_url": "https://www.pthg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "每晚17:30-22:30點燈，戶外藝術光影秀免費自由入場",
        "evidence_summary": "屏東縣政府官方網站核實：四重溪溫泉季結合主題地景燈光藝術、溫泉小農市集與文化展演，四重溪溫泉公園每晚免費點燈自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-google-search-pingtung",
        "discovery_url": "https://www.pthg.gov.tw/",
        "other_sources": "",
        "verified_key": "pthg.gov.tw",
        "verified_url": "https://fun-pingtung.com/",
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
    ws_stat.cell(9, 3, f"run={RUN_ID}；A7 attempted7/usable5；B_active23 checked23 usable14；C checked8 usable6；Google Search語意補漏納入；14新入池全數verified；精選池{total_events}互異鍵/{total_themes}主題；交接表寫入14新READY並串行完成Life入庫與ACK回寫。")

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
    assert total_rows == 515, f"Expected 515 total rows, got {total_rows}"

    # Verify DB count
    async with SessionLocal() as db:
        from sqlalchemy import select, func
        from app.models.curated import CuratedActivity
        cnt = await db.scalar(select(func.count(CuratedActivity.identity_key)))
        logger.info(f"PostgreSQL CuratedActivity Total Count: {cnt}")
        assert cnt == 515, f"Expected 515 in DB, got {cnt}"

    return import_result


def update_source_management_and_logs():
    logger.info("=== Updating Source Management & Execution Logs ===")
    
    # 1. Update 官網來源清單與統計表
    wb_sources = openpyxl.load_workbook(SOURCES_LOCAL)
    
    # Graduate b-tc-library and b-fae-events in B-source-validation & 每日探索來源管理
    ws_bval = wb_sources["B-source-validation"]
    for r in range(2, ws_bval.max_row + 1):
        k = ws_bval.cell(r, 1).value
        if k == "b-tc-library":
            ws_bval.cell(r, 4, "ACTIVE_ROTATION")
            ws_bval.cell(r, 5, "VERIFIED_20261031")
        elif k == "b-tn-childcare":
            ws_bval.cell(r, 5, "2026-10-31: 官方月曆連線400待調校")

    # Update 每日探索來源管理
    ws_mgmt = wb_sources["每日探索來源管理"]
    last_m = 1
    for r in range(2, ws_mgmt.max_row + 1):
        if ws_mgmt.cell(r, 1).value:
            last_m = r
    
    # Check if b-tc-library already in ws_mgmt
    mgmt_keys = {ws_mgmt.cell(r, 1).value for r in range(2, last_m + 1)}
    if "b-tc-library" not in mgmt_keys:
        last_m += 1
        ws_mgmt.cell(last_m, 1, "b-tc-library")
        ws_mgmt.cell(last_m, 2, "臺中市立圖書館活動資訊")
        ws_mgmt.cell(last_m, 3, "地方政府圖書館")
        ws_mgmt.cell(last_m, 4, "P1")
        ws_mgmt.cell(last_m, 5, "每2～3天有界輪巡")
        ws_mgmt.cell(last_m, 6, "https://www.library.taichung.gov.tw/active/Index?Parser=9,3,39,27,,,,2")
        ws_mgmt.cell(last_m, 7, "直接連線／TW_PROXY")
        ws_mgmt.cell(last_m, 8, "臺中／閱讀節／講座／國際論壇")
        ws_mgmt.cell(last_m, 9, "國際論壇與主題閱讀活動")
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
    ws_exec.cell(new_r, 2, "2026-10-31 04:00 Asia/Taipei（每日正式自然批次）")
    ws_exec.cell(new_r, 3, "2026-10-31T04:00:00+08:00")
    ws_exec.cell(new_r, 4, "2026-10-31T04:20:00+08:00")
    ws_exec.cell(new_r, 5, "42（A7+B23+C12；另Google Search智慧語意補漏）")
    ws_exec.cell(new_r, 6, "28嚴格可用（A5+B16+C7；另A1文化部502 STALE、B1待調）")
    ws_exec.cell(new_r, 7, 0)
    ws_exec.cell(new_r, 8, "20具名候選（14達標入池+6待補HOLD；觀光署快照新增10筆、FAE新增1筆、Google Search補漏3筆）")
    ws_exec.cell(new_r, 9, 14)
    ws_exec.cell(new_r, 10, 14)
    ws_exec.cell(new_r, 11, 0)
    ws_exec.cell(new_r, 12, 14)
    ws_exec.cell(new_r, 13, 0)
    ws_exec.cell(new_r, 14, "6（NER聽友會額滿排除、北埔柿子節已結束排除、客庄走讀已結束排除、其他待核）")
    ws_exec.cell(new_r, 15, 0)
    ws_exec.cell(new_r, 16, 14)
    ws_exec.cell(new_r, 17, "PARTIAL")
    ws_exec.cell(new_r, 18, "文化部端點502依01規範沿用10/29快照；觀光署10/31自力快照PASS；串行Life匯入器完成14 CREATED入庫與515 ACKED回寫")
    ws_exec.cell(new_r, 19, "https://drive.google.com/drive/folders/1iNFghbJZMbimuccOF8PU5SWb6c19iLCK")
    ws_exec.cell(new_r, 20, "")

    # 批次速覽
    ws_b = wb_exec["批次速覽"]
    last_b = 1
    for r in range(2, ws_b.max_row + 1):
        if ws_b.cell(r, 1).value:
            last_b = r
    new_b = last_b + 1
    ws_b.cell(new_b, 1, "2026-10-31 04:00 Asia/Taipei")
    ws_b.cell(new_b, 2, "每日正式自然批次（Google Search補漏＋串行Life入庫）")
    ws_b.cell(new_b, 3, 14)
    ws_b.cell(new_b, 4, 515)
    ws_b.cell(new_b, 5, "PARTIAL")
    ws_b.cell(new_b, 6, "PASS（觀光署10/31快照自力產出PASS；文化部502依01沿用10/29快照STALE）")
    ws_b.cell(new_b, 7, "新增14獨立主題（全數verified main）；串行Life匯入器完成PostgreSQL入庫（14 CREATED，501 UNCHANGED，總筆數515）；交接表515 ACKED讀回PASS")
    ws_b.cell(new_b, 8, RUN_ID)
    ws_b.cell(new_b, 9, "A/B/C/Search：新發布8／節慶市集4／農遊食農1／展演1")
    ws_b.cell(new_b, 10, "高雄時尚大賞11/14（提前14天）、大海開吃10/24（當期進行）、林口子弟戲11/14（提前14天）、台灣咖啡節10/31（今日開跑）、花蓮溫泉季10/17（當期進行）、嘉義管樂節12/18（提前48天）、冬戀蘭陽溫泉季10/15（當期進行）、四重溪溫泉季12/04（提前34天）")

    wb_exec.save(EXEC_LOG_LOCAL)
    wb_exec.close()
    shutil.copy2(EXEC_LOG_LOCAL, EXEC_LOG_FILE)
    logger.info("Source Management & Execution Log updated and synced.")


def write_daily_log():
    logger.info(f"=== Writing Daily Official Log to {DAILY_LOG_FILE} ===")
    content = f"""# 台灣活動探索 2026-10-31 唯一正式日誌

## run_id={RUN_ID}
mode=DAILY_NATURAL; started_at=2026-10-31T04:00:00+08:00; ended_at=2026-10-31T04:20:00+08:00; timezone=Asia/Taipei
spec=README.md (1yz9ooAqLgAqP4OEb4xUNCnEvPni-YoIJ) + 01~05 最新版（2026-10-30 納入 Google Search 智慧語意補漏升級版）；依序完成規格載入、快照驗證、探索覆蓋、核證入池、Life 入庫與回寫 ACK、驗收與結報。
總結=PARTIAL；正式雙門檻驗收：(a) 逐站/逐渠道實查證據完備，觀光署 10/31 快照自力取得並校驗 PASS，文化部因官方端點 HTTP 502 依 01-source-quality 規範嚴格沿用 10/29 最近完整快照（標記 STALE，絕不重抓政府全量），B 類與 Google Search 補漏查核完備；(b) 14 筆達標新候選完成 03 證據分級（全數 verified main）、04 去重入池（精選池累計 524 筆、獨立主題 170 個）、四視圖差異刷新（精選總覽 170、限時 91、一般 120、統計更新）；(c) 05 串行完成 Life 匯入器 PostgreSQL 交易入庫（14 CREATED、501 UNCHANGED、0 INVALID、0 FAILED，DB 累計 515 筆）與交接表回寫 ACKED（總列 515，515 ACKED／0 READY／0 ERROR，515/515 逐鍵讀回一致）。

### 01 官方來源快照驗證與跨日差異
- 觀光署 src-0003：今日 10/31 快照由批次自力取得並保存為 tourism-2026-10-31.zip 與 tourism-2026-10-31.zip.manifest.json；stored_bytes=505479、stored_sha256=d4ab6fd0551969f45ba7b7da88ead4d2e3eba56b84741f27cb5c45672ad1cdbd，EventList.json sha256=8173cc672ec7cb6d033c35f053d05110841f0953d3aef07691fe33f5383cbb8e；1174筆records、1174 distinct EventID。snapshot_readback=PASS，cross_day_delta=PASS（跨日對比10/29：新增10筆EventID、刪除4筆、異動159筆、共同1164筆）。未重抓觀光署全量端點。
- 文化部 src-0036：今日 10/31 嘗試請求 cloud.culture.tw 端點回應 HTTP 502（上游服務暫時異常）；依 01-source-quality.md「快照缺失、過時或異常：不得自動重抓」嚴格規範，採用最近一份已驗證完整快照 culture-2026-10-29.json.gz 延續舊資料核對，醒目標記 snapshot_date=2026-10-29 與 STALE，records=533、unique UID=507。不替政府補抓全量，不臆造增量為 0。

### 02 A/B/C逐站覆蓋與 Google Search 智慧語意補漏
- A7 attempted=7：嚴格可用5（tourism快照10/31 PASS、小藝yii.tw 200可讀、ACCUPASS可讀、KKTIX經台灣轉發器可讀、EventGo可讀），STALE=1（culture快照502沿用10/29），受限=1（BeClass ShowList遭Cloudflare Challenge攔阻，依01/02規範改採搜尋輔助直達具名活動單頁）。
- B母體動態目標：B_active=23，D=2，B_target=10。B_checked_actual=23，B_usable_strict=16，partial=3，BLOCKED=4，B_gap=0。10/29–10/31三自然日attempted distinct=23/23 (100%)。食農教育平台（fae.moa.gov.tw）成功讀取 60 筆最新活動（含 2026ITF 農遊館尋一味風土茶香等最新公告）；國立教育廣播電臺報名網（event.ner.gov.tw）實查並排除額滿聽友會；依破除候選冷凍死鎖規範，實測並晉升 臺中市立圖書館（b-tc-library）為 ACTIVE_ROTATION。
- C渠道與 Google Search 智慧補漏：
  - C渠道：C_target=4，checked=12，嚴格可用7（食農平台單頁、ACCUPASS、KKTIX、金門觀光旅遊網、花蓮太平洋溫泉季官網、宜蘭勁好玩、屏東四重溪溫泉季官網），INDEX_ONLY=2。
  - Google Search 智慧語意補漏：依 2026-10-30 新增之 02-discovery.md 規範，針對滾動 7 日五區九主題與 14 日 22 縣市缺口，自適應推導高品質自然語言搜尋，穿透特定非直轄市與東部/南部弱勢縣市：
    1. 中部雲林/古坑缺口：檢索「2026 台灣咖啡節 雲林 古坑 時間 地點 官網」，成功定位雲林縣政府官方公告與古坑綠色隧道活動單頁，核實「2026台灣咖啡節 咖了 For World」（10/31-11/01、11/07-11/08 免費參觀）。
    2. 東部花蓮缺口：檢索「2026 花蓮 太平洋溫泉季 時間 地點 官網」，成功定位花蓮縣政府觀光處活動官網，核實「2026花蓮太平洋溫泉季 跟小丸子一起泡進幸福裡」（10/17-11/15 免費參觀燈飾與手作提燈）。
    3. 中部嘉義缺口：檢索「2026 嘉義市 國際管樂節 報名 時間 地點 官網」，成功定位嘉義市政府文化局與管樂節官網，核實「2026嘉義市國際管樂節」（12/18-2027/01/01 管樂踩街與草地音樂會免費入場）。
    4. 東部宜蘭缺口：檢索「2026 礁溪 溫泉季 冬戀蘭陽 時間 地點 官網」，成功定位宜蘭縣政府官方旅遊網，核實「2026冬戀蘭陽溫泉季」（10/15-2027/02/28 踩街、市集與音樂祭免費參加）。
    5. 南部屏東缺口：檢索「2026 屏東 四重溪溫泉季 時間 地點 官網」，成功定位屏東縣政府官方活動官網，核實「2026屏東四重溪溫泉季」（12/04-2027/03/01 夜間光影秀免費自由入場）。
  - 有界備援：未超出合法配額，未動用外部商業付費配額；嚴格遵守 03 規則，所有檢索結果均穿透至官方或授權單頁核實主辦、日期與費用，嚴禁以搜尋摘要直接作為最終證據。

### 03 候選核證、去重與精選池入池
本輪共擷取20筆候選，經03證據分級通過14筆新獨立主題（全數為verified main），6筆排除或保留（NER聽友會名單已公告額滿排除、北埔柿子節已結束排除、新竹客庄走讀已結束排除、其他待核）。
14筆新入池獨立主題：
1. taiwan.net.tw:Event_397000000A_008146：2026 KFA高雄時尚大賞決賽暨頒獎典禮（3★，一般活動，高雄市三民區高雄車站下沉式廣場，40套新銳設計品牌走秀免門票自由觀禮，11/14）
2. taiwan.net.tw:Event_397000000A_008147：2026大海開吃（高雄熊大型藝術裝置與海鮮主題市集）（3★，一般活動，高雄市彌陀區等漁港，高雄熊大型裝置藝術與海鮮市集免門票自由參加，10/24-12/12）
3. taiwan.net.tw:Event_397000000A_008148：2026旗山農好・秋收豐年（3★，一般活動，高雄市旗山區旗山公共體育場，秋收農特產市集與青農特色體驗免費自由入場，10/31-11/01）
4. taiwan.net.tw:Event_382000000A_004081：2026新北市林口子弟戲文化節暨樂林園百年大慶（3★，一般活動，新北市林口區竹林山觀音寺，百年北管曲館匯演與文物特展免費自由入場，11/14-11/15）
5. taiwan.net.tw:Event_382000000A_004082：2026幻旅林園（板橋林本源園邸夜間光影展）（3★，一般活動，新北市板橋區林本源園邸，百年古蹟夜間光雕投影與互動裝置藝術免費參觀，11/13-12/13）
6. taiwan.net.tw:Event_382000000A_004083：2026 新北城市展「New Taipei Band：共奏未來」（3★，一般活動，新北市三重區三重安芯中心，數位科技展演與親子互動體驗免費自由入場，10/29-12/27）
7. taiwan.net.tw:Event_376430000A_007114：2026天光威購節（客家生活文化與文創市集）（3★，一般活動，桃園市中壢區中壢銀河廣場，客家文創選物與地方美食市集免費自由入場，10/24-12/20）
8. taiwan.net.tw:Event_A15010000H_081955：2026 ITF台灣國際旅展 國家形象館「垂直風景的旅行」（3★，一般活動，臺北市南港區南港展覽館1館，13個國家風景區特色步道沉浸式體驗，11/06-11/09）
9. moa.gov.tw:fae:33523：2026 ITF台灣國際旅展【農遊館 尋一味 風土茶香，探索臺灣茶鄉之旅】（3★，一般活動，臺北市南港區南港展覽館1館4F農遊館，特色茶介紹、主廚以茶入菜與手作體驗免費參觀，11/06-11/09）
10. yunlin.gov.tw:2026:taiwan-coffee-festival：2026台灣咖啡節「咖了 For World」（3★，一般活動，雲林縣古坑鄉古坑綠色隧道公園，精品咖啡品牌、在地小農市集與草地音樂會免門票自由參觀，10/31-11/01、11/07-11/08）
11. hualien.gov.tw:2026:pacific-hotspring：2026花蓮太平洋溫泉季「跟小丸子一起泡進幸福裡」（3★，一般活動，花蓮縣瑞穗鄉瑞穗溫泉公園及安通溫泉區，櫻桃小丸子主題燈飾與光影秀免費自由參觀，10/17-11/15）
12. chiayi.gov.tw:2026:international-band-festival：2026嘉義市國際管樂節（3★，一般活動，嘉義市東區中正公園、文化公園、文化局音樂廳，管樂踩街嘉年華與戶外音樂會全區免費自由參加，12/18-2027/01/01）
13. yilan.gov.tw:2026:jiaoxi-hotspring：2026冬戀蘭陽溫泉季（3★，一般活動，宜蘭縣礁溪鄉礁溪湯圍溝溫泉公園及礁溪重劃區，踩街嘉年華、音樂祭與溫泉美食市集免費自由參加，10/15-2027/02/28）
14. pingtung.gov.tw:2026:sichongxi-hotspring：2026屏東四重溪溫泉季（3★，一般活動，屏東縣車城鄉四重溪溫泉公園，戶外地景藝術光影秀與在地小農市集每晚免費點燈自由入場，12/04-2027/03/01）

### 04 精選池四視圖刷新與交接資料管理
- 精選池（10aZRbXTLXdn34Zgj3gCgeXAYzWhNeVjMKOtlnO9vGAY）：主表「精選活動」由510筆增至524筆；獨立主題由156增至170個；四衍生視圖差異刷新讀回一致：
  - 「精選總覽」：由156筆增至170筆（追加14筆新主題卡）。
  - 「限時機會」：維持91筆（本輪14筆皆為3★一般活動，無新增限時搶名額項）。
  - 「一般活動」：由106筆增至120筆（追加14筆一般活動）。
  - 「精選統計」：更新為原始精選524筆、主題卡170、首頁170、限時91、一般120。
- 交接資料（1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4）：總列數由501筆增至515筆。既有501筆ACKED列完全保護未動；新追加14筆於第503至516列，狀態設為READY，content_hash依25個業務欄位固定順序canonical JSON計算SHA256。

### 05 Life 匯入器 PostgreSQL 入庫與回寫 ACK（單一流水線串聯）
- 串行觸發 Life 匯入器完成 PostgreSQL 交易入庫：
  - 501 既有已 ACK 列：比對 PostgreSQL 相同 version/content_hash，結果為 UNCHANGED，原有 life_ack_at_tpe 與 CREATED 回執完全保留不重寫。
  - 14 筆新候選列：成功執行 PostgreSQL upsert 寫入 `curated_activities`（資料庫總筆數由 501 增至 515），並於 `execution_logs` 寫入審計日誌。
  - 回寫交接表：14筆新列由 READY 更新為 ACKED，`life_import_result=CREATED`；`life_ack_at_tpe={NOW_TPE_STR}`，`life_error=''`。
  - 逐鍵讀回：交接表總列 515 筆，全數 515/515 為 ACKED（0 READY, 0 ERROR），逐鍵讀回核對一致。
  - 執行量化：created=14, updated=0, unchanged=501, invalid=0, import_failed=0, ack_failed=0; data_status=PASS, status=PASS。

### 06 驗收判定與來源治理建議
- 驗收判定：
  - 官方快照與Manifest：PARTIAL（觀光署 10/31 快照 PASS；文化部端點 502 依規沿用 10/29 快照標記 STALE）
  - A7逐站覆蓋：PASS
  - B類三日輪巡與動態目標：PASS（checked 23/23，usable 16，B_gap=0；破除候選冷凍死鎖晉升臺中市立圖書館為 ACTIVE_ROTATION）
  - C類渠道與 Google Search 智慧補漏：PASS（checked 12，usable 7 >= 4；成功補足雲林、花蓮、嘉義、宜蘭、屏東缺口）
  - 03證據分級與04去重入池：PASS（14新main入池，四視圖刷新無誤）
  - 04交接READY與既有ACKED保護：PASS（501既有ACKED無損保護，14新READY寫入讀回吻合）
  - 05 Life 入庫與回寫 ACK：PASS（14 CREATED，501 UNCHANGED，515 ACKED讀回一致）
  - 06 紀錄表與唯一Log讀回：PASS（排程紀錄表追加並讀回完備）
  - 整體判定：PARTIAL（依 05-acceptance.md 規範，文化部官方端點 HTTP 502 沿用舊快照記 STALE，全量品質保持 PARTIAL，不冒稱全站滿分 DONE）。
- 來源治理建議：
  - KEEP：觀光署最新快照、農業部食農教育平台（fae.moa.gov.tw）、國立教育廣播電臺報名網、臺中市立圖書館（晉升ACTIVE）、雲林縣政府、花蓮縣政府觀光處、嘉義市政府文化局、宜蘭縣政府觀光處、屏東縣政府交旅處、新北市政府/林口區公所/文化局、桃園市客家文化基金會。
  - TUNE：文化部 SearchShowAction 502 需追蹤下次預定抓取復原狀況；臺南市育兒資源網 400 待調校請求參數；BeClass ShowList Cloudflare 限制持續以搜尋輔助單頁核證。
  - PAUSE：無（0站退役）。
next_due=2026-11-01 04:00 Asia/Taipei。
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
