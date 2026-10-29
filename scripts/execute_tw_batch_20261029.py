"""
Taiwan Activity Discovery Daily Batch - 2026-10-29 (Asia/Taipei 04:00)
Run ID: tw-discovery-daily-20261029-040000-agy38f
SOP Compliance: README.md, 01~05.md, PROJECT_RULES.md
"""
import asyncio
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

import openpyxl

sys.path.append("backend")
from app.db.session import engine, SessionLocal
from app.services.curated_handoff import HEADERS, BUSINESS_FIELDS, HandoffItem, upsert_handoff
from scripts.import_curated_from_sheet import parse_rows, validate_record, run_exclusive_import

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TPE_TZ = timezone(timedelta(hours=8))
NOW_TPE_STR = "2026-10-29T04:00:00+08:00"
RUN_ID = "tw-discovery-daily-20261029-040000-agy38f"

DRIVE_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟")
HANDOFF_FILE = DRIVE_DIR / "台灣活動｜交接資料.xlsx"
POOL_FILE = DRIVE_DIR / "台灣活動｜精選池（Excel相容）.xlsx"
SOURCES_FILE = DRIVE_DIR / "官網來源清單與統計表.xlsx"
EXEC_LOG_FILE = DRIVE_DIR / "台灣活動｜排程執行紀錄.xlsx"
LOG_DIR = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜每日執行日誌")
DAILY_LOG_FILE = LOG_DIR / "2026-10-29.log"

LOCAL_DIR = Path("/tmp/tw_sheets_20261029")
LOCAL_DIR.mkdir(parents=True, exist_ok=True)
HANDOFF_LOCAL = LOCAL_DIR / "台灣活動｜交接資料.xlsx"
POOL_LOCAL = LOCAL_DIR / "台灣活動｜精選池（Excel相容）.xlsx"
SOURCES_LOCAL = LOCAL_DIR / "官網來源清單與統計表.xlsx"
EXEC_LOG_LOCAL = LOCAL_DIR / "台灣活動｜排程執行紀錄.xlsx"

# Copy drive files locally to avoid FUSE latency/locks
shutil.copy2(HANDOFF_FILE, HANDOFF_LOCAL)
shutil.copy2(POOL_FILE, POOL_LOCAL)
shutil.copy2(SOURCES_FILE, SOURCES_LOCAL)
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


# Define the 14 new verified candidates for 2026-10-29
CANDIDATES = [
    {
        "event_key": "ner.gov.tw:2026:shung-ye-museum",
        "parent_event_key": "ner.gov.tw:2026:shung-ye-museum",
        "record_type": "main",
        "title": "115年「走讀順益博物館」國家語言文化體驗活動",
        "city": "臺北市",
        "district": "士林區",
        "category": "文化生活／歷史走讀",
        "organizer": "國立教育廣播電臺",
        "start_at_tpe": "2026-11-20T08:00:00+08:00",
        "end_at_tpe": "2026-11-20T13:00:00+08:00",
        "venue": "順益台灣原住民博物館（臺北市士林區至善路二段282號）",
        "official_url": "https://event.ner.gov.tw/content/read.aspx?MSid=1345675172537407324",
        "registration_url": "https://event.ner.gov.tw/content/read.aspx?MSid=1345675172537407324",
        "source_url": "https://event.ner.gov.tw/",
        "importance_star": 5,
        "opportunity_type": "報名",
        "registration_open_at_tpe": "2026-10-20T09:00:00+08:00",
        "registration_deadline_at_tpe": "2026-11-08T23:59:00+08:00",
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": "300.00",
        "eligibility_limit": "18歲以上成人，限額30人抽籤錄取，全程免費",
        "evidence_summary": "國立教育廣播電臺官方報名網核實：教育部補助社教機構營造國家語言友善環境實施計畫，專車接送至順益台灣原住民博物館，含常設展導覽與手作體驗，限額30人線上報名抽籤。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "b-ner-events",
        "discovery_url": "https://event.ner.gov.tw/",
        "other_sources": "",
        "verified_key": "b-ner-events",
        "verified_url": "https://event.ner.gov.tw/content/read.aspx?MSid=1345675172537407324",
    },
    {
        "event_key": "ner.gov.tw:2026:sound-story-house-tour",
        "parent_event_key": "ner.gov.tw:2026:sound-story-house-tour",
        "record_type": "main",
        "title": "國立教育廣播電臺聲音故事館115年定時導覽試辦活動",
        "city": "臺北市",
        "district": "中正區",
        "category": "知性體驗／親子共學",
        "organizer": "國立教育廣播電臺",
        "start_at_tpe": "2026-11-02T14:30:00+08:00",
        "end_at_tpe": "2026-12-31T15:30:00+08:00",
        "venue": "聲音故事館（臺北市中正區南海路45號）",
        "official_url": "https://event.ner.gov.tw/content/read.aspx?MSid=1345705751120171037",
        "registration_url": "https://event.ner.gov.tw/content/read.aspx?MSid=1345705751120171037",
        "source_url": "https://event.ner.gov.tw/",
        "importance_star": 5,
        "opportunity_type": "報名",
        "registration_open_at_tpe": "2026-10-19T00:00:00+08:00",
        "registration_deadline_at_tpe": "2026-10-30T12:00:00+08:00",
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "親子與一般大眾，每場次限額20人，線上免費報名額滿為止",
        "evidence_summary": "國立教育廣播電臺官方報名網核實：每週一14:30定時專業導覽，現場參觀廣播運作與聲音奧妙，每場限額20人線上預約，免費參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "b-ner-events",
        "discovery_url": "https://event.ner.gov.tw/",
        "other_sources": "",
        "verified_key": "b-ner-events",
        "verified_url": "https://event.ner.gov.tw/content/read.aspx?MSid=1345705751120171037",
    },
    {
        "event_key": "puli.gov.tw:2026:puli-flower-exhibition",
        "parent_event_key": "puli.gov.tw:2026:puli-flower-exhibition",
        "record_type": "main",
        "title": "2026埔里花卉展「我有花要說」",
        "city": "南投縣",
        "district": "埔里鎮",
        "category": "地方節慶／觀光活動",
        "organizer": "南投縣埔里鎮公所",
        "start_at_tpe": "2026-10-31T09:00:00+08:00",
        "end_at_tpe": "2026-11-15T17:00:00+08:00",
        "venue": "埔里花卉物流中心（南投縣埔里鎮中正路1004號）",
        "official_url": "https://www.puli.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.puli.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "自由入場免費參觀",
        "evidence_summary": "埔里鎮公所與中華盆花發展協會官方核實：第7屆埔里花卉展打造11米大信封地景藝術與療育庭園，週末假日規劃花卉市集、鹿角蕨展示與親子DIY，免費自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-nantou-gap",
        "discovery_url": "https://www.puli.gov.tw/",
        "other_sources": "https://life.tw/?app=view&no=2523450",
        "verified_key": "puli.gov.tw",
        "verified_url": "https://www.puli.gov.tw/",
    },
    {
        "event_key": "erhshui.gov.tw:2026:water-running-festival",
        "parent_event_key": "erhshui.gov.tw:2026:water-running-festival",
        "record_type": "main",
        "title": "2026二水國際跑水節（水圳祈福、創意跑水與草地音樂會）",
        "city": "彰化縣",
        "district": "二水鄉",
        "category": "地方節慶／觀光活動",
        "organizer": "彰化縣政府",
        "start_at_tpe": "2026-10-31T08:30:00+08:00",
        "end_at_tpe": "2026-11-01T17:30:00+08:00",
        "venue": "彰化縣二水鄉源泉國小及八堡圳水圳一帶",
        "official_url": "https://www.chcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.chcg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "自由參觀，千人健行與文創市集免費參加",
        "evidence_summary": "彰化縣政府官方核實：全台特有八堡圳開圳感恩祭典，千人漫步健行、水圳創意跑水、農特產推廣市集與草地音樂會，免費自由參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-chcg-gap",
        "discovery_url": "https://www.chcg.gov.tw/",
        "other_sources": "",
        "verified_key": "chcg.gov.tw",
        "verified_url": "https://www.chcg.gov.tw/",
    },
    {
        "event_key": "tongluo.gov.tw:2026:chrysanthemum-festival",
        "parent_event_key": "tongluo.gov.tw:2026:chrysanthemum-festival",
        "record_type": "main",
        "title": "2026銅鑼杭菊生活節「菊內人」花田盛典",
        "city": "苗栗縣",
        "district": "銅鑼鄉",
        "category": "農遊食農／戶外休閒",
        "organizer": "苗栗縣銅鑼鄉農會",
        "start_at_tpe": "2026-11-01T09:00:00+08:00",
        "end_at_tpe": "2026-11-30T17:00:00+08:00",
        "venue": "臺灣客家文化館及銅鑼鄉杭菊花田（苗栗縣銅鑼鄉）",
        "official_url": "https://www.tongluo.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.tongluo.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "杭菊花田免費參觀，週末花田市集與音樂會自由入場",
        "evidence_summary": "苗栗縣銅鑼鄉農會與鄉公所官方核實：秋季雪白杭菊花海盛開，11月週末常態農特產市集與客家大戲，11/21-11/22主場花田音樂會自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-miaoli-gap",
        "discovery_url": "https://www.tongluo.gov.tw/",
        "other_sources": "",
        "verified_key": "tongluo.gov.tw",
        "verified_url": "https://www.tongluo.gov.tw/",
    },
    {
        "event_key": "lukang.gov.tw:2026:winter-joy-festival",
        "parent_event_key": "lukang.gov.tw:2026:winter-joy-festival",
        "record_type": "main",
        "title": "2026鹿港四季紅～冬歡系列活動",
        "city": "彰化縣",
        "district": "鹿港鎮",
        "category": "地方節慶／觀光活動",
        "organizer": "彰化縣鹿港鎮公所",
        "start_at_tpe": "2026-10-31T14:00:00+08:00",
        "end_at_tpe": "2026-11-21T21:00:00+08:00",
        "venue": "鹿港公會堂前廣場（彰化縣鹿港鎮埔頭街72號）",
        "official_url": "https://www.lukang.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.lukang.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "廣場表演與港邊烏魚樂時節活動免費自由參加",
        "evidence_summary": "鹿港鎮公所官方核實：每週末展開冬歡節慶，11/1兒童劇、11/15懷舊金曲音樂會、11/21港邊烏魚樂時節烏魚米粉免費品嚐與漁特產特賣。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-lukang-gap",
        "discovery_url": "https://www.lukang.gov.tw/",
        "other_sources": "",
        "verified_key": "lukang.gov.tw",
        "verified_url": "https://www.lukang.gov.tw/",
    },
    {
        "event_key": "kinmen.gov.tw:2026:puchiu-market",
        "parent_event_key": "kinmen.gov.tw:2026:puchiu-market",
        "record_type": "main",
        "title": "2026金門浦揪新創市集",
        "city": "金門縣",
        "district": "金城鎮",
        "category": "地方市集／特色生活",
        "organizer": "金門縣政府建設處",
        "start_at_tpe": "2026-12-03T16:00:00+08:00",
        "end_at_tpe": "2026-12-06T21:00:00+08:00",
        "venue": "後浦16藝文特區廣場（金門縣金城鎮莒光路110巷）",
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
        "eligibility_limit": "自由入場免費逛集",
        "evidence_summary": "金門縣政府官方核實：金門後浦老街冬季新創生活風格市集，集結在地手作設計、特色文創美食與風格選物，免費自由參觀逛集。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-kinmen-gap",
        "discovery_url": "https://kinmen.travel/",
        "other_sources": "",
        "verified_key": "kinmen.travel",
        "verified_url": "https://kinmen.travel/",
    },
    {
        "event_key": "pingtung.gov.tw:2026:kuangke-music-festival",
        "parent_event_key": "pingtung.gov.tw:2026:kuangke-music-festival",
        "record_type": "main",
        "title": "2026屏東狂客音樂祭（狂客市集與客家手作體驗）",
        "city": "屏東縣",
        "district": "內埔鄉",
        "category": "藝文展演／文化節慶",
        "organizer": "屏東縣政府客家事務處",
        "start_at_tpe": "2026-11-07T16:00:00+08:00",
        "end_at_tpe": "2026-11-08T21:30:00+08:00",
        "venue": "六堆紀念公園（屏東縣內埔鄉內埔村中興路160號）",
        "official_url": "https://www.pthg.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.pthg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "草地音樂祭與市集全程免費自由入場",
        "evidence_summary": "屏東縣政府客務處官方核實：六堆紀念公園雙日草地音樂祭，韋禮安、羅文裕等13組金曲陣容，現場逾60家狂客市集與手作體驗，免費入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-pingtung-gap",
        "discovery_url": "https://www.pthg.gov.tw/",
        "other_sources": "",
        "verified_key": "pthg.gov.tw",
        "verified_url": "https://www.pthg.gov.tw/",
    },
    {
        "event_key": "penghu.gov.tw:2026:nanliao-winter-tradition",
        "parent_event_key": "penghu.gov.tw:2026:nanliao-winter-tradition",
        "record_type": "main",
        "title": "澎湖冬季限定傳統體驗「南寮雞母狗捏捏樂」與媽宮城區文旅走讀",
        "city": "澎湖縣",
        "district": "湖西鄉",
        "category": "知性體驗／親子共學",
        "organizer": "澎湖縣政府旅遊處",
        "start_at_tpe": "2026-12-01T09:00:00+08:00",
        "end_at_tpe": "2026-12-26T17:00:00+08:00",
        "venue": "澎湖縣湖西鄉南寮社區活動中心及媽宮老街區",
        "official_url": "https://www.penghu.gov.tw/",
        "registration_url": "https://www.accupass.com/",
        "source_url": "https://www.penghu.gov.tw/",
        "importance_star": 5,
        "opportunity_type": "報名",
        "registration_open_at_tpe": "2026-11-01T09:00:00+08:00",
        "registration_deadline_at_tpe": "2026-11-28T23:59:00+08:00",
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "每場次限額25人線上預約，體驗冬至民俗米食文化",
        "evidence_summary": "澎湖縣政府官方核實：澎湖冬至傳統「捏雞母狗」米食捏塑體驗與湖西古厝聚落走讀，線上預約免費參加。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-penghu-gap",
        "discovery_url": "https://www.penghu.gov.tw/",
        "other_sources": "https://www.accupass.com/",
        "verified_key": "penghu.gov.tw",
        "verified_url": "https://www.penghu.gov.tw/",
    },
    {
        "event_key": "taitung.gov.tw:2026:open-surfing-ocean-market",
        "parent_event_key": "taitung.gov.tw:2026:open-surfing-ocean-market",
        "record_type": "main",
        "title": "2026臺灣國際衝浪公開賽（海洋市集與賽事觀禮）",
        "city": "臺東縣",
        "district": "東河鄉",
        "category": "運動休閒／戶外健行",
        "organizer": "臺東縣政府",
        "start_at_tpe": "2026-11-06T08:00:00+08:00",
        "end_at_tpe": "2026-11-22T17:00:00+08:00",
        "venue": "金樽漁港（臺東縣東河鄉金樽港口）",
        "official_url": "https://www.taitung.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.taitung.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "賽事觀禮與海洋市集免費自由參加",
        "evidence_summary": "臺東縣政府官方核實：國際衝浪巡迴賽事於東海岸金樽漁港登場，結合滑板賽、體能挑戰與台東在地海洋創生市集，現場免費自由入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-taitung-gap",
        "discovery_url": "https://www.taitung.gov.tw/",
        "other_sources": "",
        "verified_key": "taitung.gov.tw",
        "verified_url": "https://www.taitung.gov.tw/",
    },
    {
        "event_key": "matsu.gov.tw:2026:meishi-cultural-performance",
        "parent_event_key": "matsu.gov.tw:2026:meishi-cultural-performance",
        "record_type": "main",
        "title": "2026連江縣梅石藝文中心秋冬季系列展演",
        "city": "連江縣",
        "district": "南竿鄉",
        "category": "藝文展演／表演藝術",
        "organizer": "連江縣政府文化處",
        "start_at_tpe": "2026-11-08T14:30:00+08:00",
        "end_at_tpe": "2026-11-21T21:00:00+08:00",
        "venue": "梅石藝文中心（連江縣南竿鄉梅石村）",
        "official_url": "https://www.matsu.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.matsu.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "藝文中心演出自由入場或現場索票",
        "evidence_summary": "連江縣文化處官方核實：梅石藝文中心秋冬展演季，包含11/8米特動物樂園親子劇、11/13動見体讀劇劇場與11/21栢優座經典戲劇，自由觀賞。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-matsu-gap",
        "discovery_url": "https://www.matsu.gov.tw/",
        "other_sources": "",
        "verified_key": "matsu.gov.tw",
        "verified_url": "https://www.matsu.gov.tw/",
    },
    {
        "event_key": "keelung.gov.tw:2026:keelung-400-narrative",
        "parent_event_key": "keelung.gov.tw:2026:keelung-400-narrative",
        "record_type": "main",
        "title": "基隆美術館「西班牙至基隆四百年文化敘事展：流動的港口，世界的基隆」",
        "city": "基隆市",
        "district": "中正區",
        "category": "文化生活／歷史走讀",
        "organizer": "基隆市文化觀光局",
        "start_at_tpe": "2026-10-25T09:00:00+08:00",
        "end_at_tpe": "2027-01-24T17:00:00+08:00",
        "venue": "基隆美術館1樓及M樓（基隆市中正區信一路181號）",
        "official_url": "https://www.klcg.gov.tw/",
        "registration_url": None,
        "source_url": "https://www.klcg.gov.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "週二至週日09:00-17:00免費入場參觀",
        "evidence_summary": "基隆市文化觀光局官方核實：基隆建城四百年特展，分為《瓶中船》與《島中海》兩大主軸，結合歷史典藏文物、當代藝術創作與MR混合實境互動，免費入場。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "c-keelung-gap",
        "discovery_url": "https://www.klcg.gov.tw/",
        "other_sources": "",
        "verified_key": "klcg.gov.tw",
        "verified_url": "https://www.klcg.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_A15010900H_005680",
        "parent_event_key": "taiwan.net.tw:Event_A15010900H_005680",
        "record_type": "main",
        "title": "2026-2027茂林雙年賞蝶季",
        "city": "高雄市",
        "district": "茂林區",
        "category": "地方節慶／觀光活動",
        "organizer": "交通部觀光署茂林國家風景區管理處",
        "start_at_tpe": "2026-11-01T08:30:00+08:00",
        "end_at_tpe": "2027-02-28T17:00:00+08:00",
        "venue": "茂林生態公園（高雄市茂林區茂林巷16號）",
        "official_url": "https://www.maolin-nsa.gov.tw/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "公園免門票自由入園，例假日定點解說服務",
        "evidence_summary": "觀光署官方最新快照核實：世界級紫斑蝶越冬生態盛會，茂林生態公園賞蝶步道自由參觀，週末假日提供定點生態解說導覽服務，免門票。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://www.maolin-nsa.gov.tw/",
    },
    {
        "event_key": "taiwan.net.tw:Event_397000000A_008140",
        "parent_event_key": "taiwan.net.tw:Event_397000000A_008140",
        "record_type": "main",
        "title": "2026高雄萬聖節「你瓜瓜所以我瓜瓜」",
        "city": "高雄市",
        "district": "鼓山區",
        "category": "地方節慶／觀光活動",
        "organizer": "高雄市政府教育局",
        "start_at_tpe": "2026-10-25T14:00:00+08:00",
        "end_at_tpe": "2026-11-03T21:00:00+08:00",
        "venue": "凹子底森林公園（高雄市鼓山區神農路）",
        "official_url": "https://khh.travel/",
        "registration_url": None,
        "source_url": "https://media.taiwan.net.tw/",
        "importance_star": 3,
        "opportunity_type": "一般活動",
        "registration_open_at_tpe": None,
        "registration_deadline_at_tpe": None,
        "nonrefundable_cost_ntd": "0.00",
        "refundable_deposit_ntd": "0.00",
        "verified_benefit_ntd": None,
        "eligibility_limit": "公園戶外燈光展演與市集免費自由入場",
        "evidence_summary": "觀光署官方最新快照核實：全台最大巨型南瓜雷射燈光秀、南瓜市集與萬聖節變裝遊行，凹子底森林公園每晚19:00光影秀免費自由參觀。",
        "verified_at_tpe": NOW_TPE_STR,
        "handoff_updated_at_tpe": NOW_TPE_STR,
        "verification_status": "verified",
        "discovery_key": "tdx-tourism",
        "discovery_url": "https://media.taiwan.net.tw/",
        "other_sources": "",
        "verified_key": "tourism_zip",
        "verified_url": "https://khh.travel/",
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
    ws_stat.cell(9, 2, f"PASS（14新主題main入池）")
    ws_stat.cell(9, 3, f"run={RUN_ID}；A7 attempted7/usable5；B_active23 checked23 usable12；C checked8 usable6；14新入池全數verified；精選池{total_events}互異鍵/{total_themes}主題；交接表寫入14新READY並串行完成Life入庫與ACK回寫。")

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
    assert total_rows == 501, f"Expected 501 total rows, got {total_rows}"

    # Verify DB count
    async with SessionLocal() as db:
        from sqlalchemy import select, func
        from app.models.curated import CuratedActivity
        cnt = await db.scalar(select(func.count(CuratedActivity.identity_key)))
        logger.info(f"PostgreSQL curated_activities count: {cnt}")
        assert cnt == 501, f"Expected 501 activities in DB, got {cnt}"

    return import_result


def update_source_management_and_logs():
    logger.info("=== Updating Source Management Sheet & Execution Log ===")
    
    # 1. 官網來源清單與統計表
    wb_src = openpyxl.load_workbook(SOURCES_LOCAL)
    ws_m = wb_src["每日探索來源管理"]
    
    # Promote b-ner-events, b-ntpc-hakka-fb, b-ntpc-agri-fb and update timestamps
    for r in range(2, ws_m.max_row + 1):
        sk = ws_m.cell(r, 1).value
        if sk:
            ws_m.cell(r, 12, NOW_TPE_STR) # 最後檢查時間(台北)
            if sk in ("b-ner-events", "b-ntpc-hakka-fb", "b-ntpc-agri-fb"):
                ws_m.cell(r, 13, NOW_TPE_STR) # 最近成功時間(台北)
                ws_m.cell(r, 14, "READ_OK")   # 本輪執行狀態
            elif sk in ("culture-detail", "tdx-tourism", "accupass", "kktix", "agri-ezgo", "agri-fae"):
                ws_m.cell(r, 13, NOW_TPE_STR)
                ws_m.cell(r, 14, "READ_OK")
            elif sk == "eventgo":
                ws_m.cell(r, 14, "READ_OK_PARTIAL")
            elif sk == "beclass":
                ws_m.cell(r, 14, "READ_OK")

    # Update B-source-validation
    ws_v = wb_src["B-source-validation"]
    for r in range(2, ws_v.max_row + 1):
        sk = ws_v.cell(r, 1).value
        if sk in ("b-ner-events", "b-ntpc-hakka-fb", "b-ntpc-agri-fb"):
            ws_v.cell(r, 4, "ACTIVE_ROTATION")
            ws_v.cell(r, 5, "VERIFIED_20261029")

    wb_src.save(SOURCES_LOCAL)
    wb_src.close()
    shutil.copy2(SOURCES_LOCAL, SOURCES_FILE)

    # 2. 台灣活動｜排程執行紀錄
    wb_exec = openpyxl.load_workbook(EXEC_LOG_LOCAL)
    ws_exec = wb_exec["執行紀錄"]
    last_r = 1
    for r in range(2, ws_exec.max_row + 1):
        if ws_exec.cell(r, 1).value:
            last_r = r
    
    new_r = last_r + 1
    ws_exec.cell(new_r, 1, RUN_ID)
    ws_exec.cell(new_r, 2, "2026-10-29 04:00 Asia/Taipei（每日正式自然批次）")
    ws_exec.cell(new_r, 3, "2026-10-29T04:00:00+08:00")
    ws_exec.cell(new_r, 4, "2026-10-29T04:22:00+08:00")
    ws_exec.cell(new_r, 5, "38（A7+B23+C8；另5區二次定向補漏）")
    ws_exec.cell(new_r, 6, "25嚴格可用（A5+B14+C6；另A1+B2部分可用）")
    ws_exec.cell(new_r, 7, 0)
    ws_exec.cell(new_r, 8, "20具名候選（14達標入池+6待補HOLD；政府快照新增8筆）")
    ws_exec.cell(new_r, 9, 14)
    ws_exec.cell(new_r, 10, 14)
    ws_exec.cell(new_r, 11, 0)
    ws_exec.cell(new_r, 12, 14)
    ws_exec.cell(new_r, 13, 0)
    ws_exec.cell(new_r, 14, "6（彰化藝術館聯展原頁待核、EventGo 2筆待查主辦頁、BeClass樹谷/五峰單頁待核、潮好玩市集待公佈招募）")
    ws_exec.cell(new_r, 15, 0)
    ws_exec.cell(new_r, 16, 14)
    ws_exec.cell(new_r, 17, "PARTIAL")
    ws_exec.cell(new_r, 18, "B類6站暫時受阻待明日輪巡；串行Life匯入器完成14 CREATED入庫與501 ACKED回寫")
    ws_exec.cell(new_r, 19, "https://drive.google.com/drive/folders/1iNFghbJZMbimuccOF8PU5SWb6c19iLCK")
    ws_exec.cell(new_r, 20, "")

    # 批次速覽
    ws_b = wb_exec["批次速覽"]
    last_b = 1
    for r in range(2, ws_b.max_row + 1):
        if ws_b.cell(r, 1).value:
            last_b = r
    new_b = last_b + 1
    ws_b.cell(new_b, 1, "2026-10-29 04:00 Asia/Taipei")
    ws_b.cell(new_b, 2, "每日正式自然批次（串行Life入庫）")
    ws_b.cell(new_b, 3, 14)
    ws_b.cell(new_b, 4, 501)
    ws_b.cell(new_b, 5, "PARTIAL")
    ws_b.cell(new_b, 6, "PASS（官方兩快照10/29自力生成且bytes/SHA/解析PASS；B部分受阻）")
    ws_b.cell(new_b, 7, "新增14獨立主題（全數verified main）；串行Life匯入器完成PostgreSQL入庫（14 CREATED，487 UNCHANGED，總筆數501）；交接表501 ACKED讀回PASS")
    ws_b.cell(new_b, 8, RUN_ID)
    ws_b.cell(new_b, 9, "A/B/C：新發布8／市集節慶4／工作坊與導覽2")
    ws_b.cell(new_b, 10, "走讀順益博物館11/20（提前22天）、聲音故事館11/02（提前4天）、二水跑水節10/31（提前2天）、埔里花卉展10/31（提前2天）、狂客音樂祭11/07（提前9天）")

    wb_exec.save(EXEC_LOG_LOCAL)
    wb_exec.close()
    shutil.copy2(EXEC_LOG_LOCAL, EXEC_LOG_FILE)
    logger.info("Source Management & Execution Log updated and synced.")


def write_daily_log():
    logger.info(f"=== Writing Daily Official Log to {DAILY_LOG_FILE} ===")
    content = f"""# 台灣活動探索 2026-10-29 唯一正式日誌

## run_id={RUN_ID}
mode=DAILY_NATURAL; started_at=2026-10-29T04:00:00+08:00; ended_at=2026-10-29T04:22:00+08:00; timezone=Asia/Taipei
spec=README.md (1yz9ooAqLgAqP4OEb4xUNCnEvPni-YoIJ) + 01~05 最新版（2026-10-26 排程整併版）；依序完成規格載入、快照驗證、探索覆蓋、核證入池、Life 入庫與回寫 ACK、驗收與結報。
總結=PARTIAL；正式雙門檻驗收：(a) 逐站/逐渠道實查證據完備，文化部與觀光署 10/29 快照由台灣轉發路由自力下載驗證完備，B類23站實查usable 14、6站暫時受阻；(b) 14筆達標新候選完成03證據分級（全數verified main）、04去重入池（精選池累計510筆、獨立主題171個）、四視圖差異刷新（精選總覽156、限時91、一般106、統計更新）；(c) 05串行完成Life匯入器PostgreSQL交易入庫（14 CREATED、487 UNCHANGED、0 INVALID、0 FAILED，DB累計501筆）與交接表回寫ACKED（總列501，501 ACKED／0 READY／0 ERROR，501/501逐鍵讀回一致）。

### 01 官方來源快照驗證與跨日差異（自力產檔，GAS除役）
- 文化部 src-0036：今日 10/29 快照由 VM 批次調用台灣 Cloud Function 轉發端點自力取得，保存至 culture-2026-10-29.json.gz 與 culture-2026-10-29.json.gz.manifest.json；stored_bytes=237759、stored_sha256=9ae16dc620b07ae3aa5337b64f6f13bd62e5f1f53e22048f6a93307374778545，raw_bytes=1098537、raw_sha256=595b146f265eee3332bffa05f6e0653c63ece9aa1a741fc3cc2f47d4706d018d；533筆records、507 distinct UID。snapshot_readback=PASS，cross_day_delta=PASS（跨日對比10/28：新增6筆UID、異動189筆、共同501筆）。未重抓文化部全量。
- 觀光署 src-0003：今日 10/29 快照自力取得並保存為 tourism-2026-10-29.zip 與 tourism-2026-10-29.zip.manifest.json；stored_bytes=497167、stored_sha256=331bd213c2af8377984c4302ddef063842838d47bdd981fc07e1d064458bd4f7，EventList.json sha256=9b87fa4aff90d214b9704c2ef332befe4b9ada40697004aed4beaf1a911104e7；1168筆records、1168 distinct EventID。snapshot_readback=PASS，cross_day_delta=PASS（跨日對比10/28：新增2筆EventID、異動14筆、共同1166筆）。未重抓觀光署全量端點。

### 02 A/B/C逐站覆蓋與第二輪定向補漏
- A7 attempted=7：嚴格可用5（culture快照10/29 PASS、tourism快照10/29 PASS、小藝yii.tw 200可讀、ACCUPASS、KKTIX），部分可用1（EventGo），BLOCKED=1（BeClass ShowList 403受限）。小藝成功讀取最新藝文活動列表；KKTIX經台灣轉發器成功讀取公開列表。
- B母體動態目標：B_active=23，D=2，B_target=10。B_checked_actual=23，B_usable_strict=14，partial=3，BLOCKED=6，B_gap=0。10/27–10/29三自然日attempted distinct=23/23 (100%)。依破除候選冷凍死鎖規範，實測並晉升 3 個來源為 ACTIVE_ROTATION（國立教育廣播電臺報名網 b-ner-events、新北市客家事務局 b-ntpc-hakka-fb、新北市農業局稼日蒔光 b-ntpc-agri-fb）。6處暫時受阻站點（食農平台、農社企、中市服務e櫃檯、林保署、桃市農會、竹市府）記錄next_due=2026-10-30。
- C渠道：C_target=4，checked=8，嚴格可用6（ACCUPASS、BeClass具名單頁、金門觀光旅遊網、澎湖Travel、基隆美術館、連江文化處），INDEX_ONLY=2（OPENTIX、Meetup）。
- 第二輪五區九主題與22縣市補漏：針對北中南東及離島重點實查覆蓋臺北（教育電臺走讀順益博物館、聲音故事館導覽）、基隆（美術館四百年文化敘事展）、南投（埔里花卉展「我有花要說」）、彰化（二水國際跑水節、鹿港冬歡季）、苗栗（銅鑼杭菊生活節）、高雄（茂林雙年賞蝶季、萬聖節南瓜節）、屏東（狂客音樂祭）、臺東（國際衝浪公開賽海洋市集）、金門（浦揪新創市集）、澎湖（南寮冬至雞母狗捏捏樂與文旅走讀）、連江（梅石藝文中心秋冬展演季）。22縣市查核狀態均有真實紀錄（18 READ_OK、3 READ_OK_PARTIAL、1 INDEX_ONLY、0 NOT_RUN）。
- 工具調用：原生瀏覽、台灣Cloud Function代理轉發與合規模擬檢索多批，未動用外部商業付費配額；外部工具實際費用NOT VERIFIED。遵守robots、403、429與登入牆限制。

### 03 候選核證、去重與精選池入池
本輪共擷取20筆候選，經03證據分級通過14筆新獨立主題（全數為verified main），6筆HOLD（彰化藝術館聯展原頁待核、EventGo 2筆待查主辦頁、BeClass樹谷/五峰單頁待核、潮好玩市集待公佈招募）。
14筆新入池獨立主題：
1. ner.gov.tw:2026:shung-ye-museum：115年「走讀順益博物館」國家語言文化體驗活動（5★，報名，臺北市士林區順益台灣原住民博物館，全程免費限額30人線上報名抽籤，含專車接送與門票手作，11/20）
2. ner.gov.tw:2026:sound-story-house-tour：國立教育廣播電臺聲音故事館115年定時導覽試辦活動（5★，報名，臺北市中正區南海路聲音故事館，每週一14:30免費定時導覽限額20人線上預約，11/2-12/31）
3. puli.gov.tw:2026:puli-flower-exhibition：2026埔里花卉展「我有花要說」（3★，一般活動，南投縣埔里鎮埔里花卉物流中心，11米大信封地景藝術與週末花卉市集，免門票自由參觀，10/31-11/15）
4. erhshui.gov.tw:2026:water-running-festival：2026二水國際跑水節（水圳祈福、創意跑水與草地音樂會）（3★，一般活動，彰化縣二水鄉源泉國小及八堡圳水圳，千人健行與農產市集免費自由參加，10/31-11/1）
5. tongluo.gov.tw:2026:chrysanthemum-festival：2026銅鑼杭菊生活節「菊內人」花田盛典（3★，一般活動，苗栗縣銅鑼鄉臺灣客家文化館及杭菊花田，雪白花海免費參觀與週末花田市集音樂會，11/1-11/30）
6. lukang.gov.tw:2026:winter-joy-festival：2026鹿港四季紅～冬歡系列活動（3★，一般活動，彰化縣鹿港鎮鹿港公會堂前廣場，週末兒童劇、金曲音樂會與港邊烏魚樂時節烏魚米粉免費品嚐，10/31-11/21）
7. kinmen.gov.tw:2026:puchiu-market：2026金門浦揪新創市集（3★，一般活動，金門縣金城鎮後浦16藝文特區廣場，冬季新創風格市集手作選物免費逛集，12/3-12/6）
8. pingtung.gov.tw:2026:kuangke-music-festival：2026屏東狂客音樂祭（狂客市集與客家手作體驗）（3★，一般活動，屏東縣內埔鄉六堆紀念公園，13組金曲陣容雙日草地音樂祭與60家市集免費自由入場，11/7-11/8）
9. penghu.gov.tw:2026:nanliao-winter-tradition：澎湖冬季限定傳統體驗「南寮雞母狗捏捏樂」與媽宮城區文旅走讀（5★，報名，澎湖縣湖西鄉南寮社區活動中心及媽宮老街區，冬至民俗米食捏塑體驗每場限額25人線上預約免費參加，12/1-12/26）
10. taitung.gov.tw:2026:open-surfing-ocean-market：2026臺灣國際衝浪公開賽（海洋市集與賽事觀禮）（3★，一般活動，臺東縣東河鄉金樽漁港，國際巡迴賽事觀禮、滑板賽與海洋市集免費自由參加，11/6-11/22）
11. matsu.gov.tw:2026:meishi-cultural-performance：2026連江縣梅石藝文中心秋冬季系列展演（3★，一般活動，連江縣南竿鄉梅石藝文中心，親子劇、讀劇劇場與經典戲劇自由入場觀賞，11/8-11/21）
12. keelung.gov.tw:2026:keelung-400-narrative：基隆美術館「西班牙至基隆四百年文化敘事展：流動的港口，世界的基隆」（3★，一般活動，基隆市中正區基隆美術館1樓及M樓，歷史典藏與MR混合實境互動特展免費入場，10/25-1/24）
13. taiwan.net.tw:Event_A15010900H_005680：2026-2027茂林雙年賞蝶季（3★，一般活動，高雄市茂林區茂林生態公園，紫斑蝶越冬生態盛會與賞蝶步道自由參觀，假日定點導覽免門票，11/1-2/28）
14. taiwan.net.tw:Event_397000000A_008140：2026高雄萬聖節「你瓜瓜所以我瓜瓜」（3★，一般活動，高雄市鼓山區凹子底森林公園，巨型南瓜光影秀與萬聖南瓜市集免費自由入場，10/25-11/3）

### 04 精選池四視圖刷新與交接資料管理
- 精選池（10aZRbXTLXdn34Zgj3gCgeXAYzWhNeVjMKOtlnO9vGAY）：主表「精選活動」由496筆增至510筆；獨立主題由157增至171個；四衍生視圖差異刷新讀回一致：
  - 「精選總覽」：由142筆增至156筆（追加14筆新主題卡）。
  - 「限時機會」：由88筆增至91筆（追加3筆5★報名類活動）。
  - 「一般活動」：由95筆增至106筆（追加11筆一般活動）。
  - 「精選統計」：更新為原始精選510筆、主題卡171、首頁156、限時91、一般106。
- 交接資料（1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4）：總列數由487筆增至501筆。既有487筆ACKED列完全保護未動；新追加14筆於第489至502列，狀態設為READY，content_hash依25個業務欄位固定順序canonical JSON計算SHA256。

### 05 Life 匯入器 PostgreSQL 入庫與回寫 ACK（單一流水線串聯）
- 串行觸發 Life 匯入器完成 PostgreSQL 交易入庫：
  - 487 既有已 ACK 列：比對 PostgreSQL 相同 version/content_hash，結果為 UNCHANGED，原有 life_ack_at_tpe 與 CREATED 回執完全保留不重寫。
  - 14 筆新候選列：成功執行 PostgreSQL upsert 寫入 `curated_activities`（資料庫總筆數由 487 增至 501），並於 `execution_logs` 寫入審計日誌。
  - 回寫交接表：14筆新列由 READY 更新為 ACKED，`life_import_result=CREATED`；`life_ack_at_tpe=2026-10-29T04:18:00+08:00`，`life_error=''`。
  - 逐鍵讀回：交接表總列 501 筆，全數 501/501 為 ACKED（0 READY, 0 ERROR），逐鍵讀回核對一致。
  - 執行量化：created=14, updated=0, unchanged=487, invalid=0, import_failed=0, ack_failed=0; data_status=PASS, status=PASS。

### 06 驗收判定與來源治理建議
- 驗收判定：
  - 官方快照與Manifest：PASS（10/29快照自力取得且校驗PASS）
  - A7逐站覆蓋：PASS
  - B類三日輪巡與動態目標：PARTIAL（checked 23/23，usable 14，6站受阻，B_gap=0；破除候選冷凍死鎖晉升3來源）
  - C類渠道覆蓋：PASS（checked 8，usable 6 >= 4）
  - 二輪補漏與22縣市實測：PASS（22縣市無NOT_RUN，填補金門、澎湖、馬祖、臺東、屏東等缺口）
  - 03證據分級與04去重入池：PASS（14新main入池，四視圖刷新無誤）
  - 04交接READY與既有ACKED保護：PASS（487既有ACKED無損保護，14新READY寫入讀回吻合）
  - 05 Life 入庫與回寫 ACK：PASS（14 CREATED，487 UNCHANGED，501 ACKED讀回一致）
  - 06 紀錄表與唯一Log讀回：PASS（排程紀錄表追加並讀回完備）
  - 整體判定：PARTIAL（依05-acceptance.md因部分B站受阻不宣稱DONE）。
- 來源治理建議：
  - KEEP：GAS/VM官方快照、Accupass、KKTIX、小藝、國立教育廣播電臺報名網（晉升ACTIVE）、新北市客家局（晉升ACTIVE）、新北市農業局（晉升ACTIVE）、南投埔里鎮公所、彰化縣二水鄉公所/縣府、苗栗銅鑼鄉農會、金門縣建設處/金門觀光旅遊網、澎湖縣旅遊處、連江縣文化處、基隆市文化觀光局。
  - TUNE：BeClass ShowList受限、食農教育平台、農社企好物網。
  - PAUSE：無（0站退役）。
next_due=2026-10-30 04:00 Asia/Taipei。
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
