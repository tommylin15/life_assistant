"""
Import Qualified Official Snapshots (Culture & Tourism) to Curated Pool and Life DB.
Executes Step 02-04 qualification & handoff generation and Step 04.5 Life PostgreSQL ingestion.
Complies with 03-qualification.md, 04-upsert.md, and PROJECT_RULES.md.
"""
import asyncio
import gzip
import hashlib
import json
import logging
import os
import re
import sys
import zipfile
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
NOW_TPE_STR = "2026-10-28T04:00:00+08:00"

HANDOFF_LOCAL = Path("/tmp/tw_sheets/台灣活動｜交接資料.xlsx")
HANDOFF_DRIVE = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟/台灣活動｜交接資料.xlsx")

POOL_LOCAL = Path("/tmp/tw_sheets/台灣活動｜精選池（Excel相容）.xlsx")
POOL_DRIVE = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟/台灣活動｜精選池（Excel相容）.xlsx")

CULTURE_SNAPSHOT = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟/官方來源快照/culture-2026-10-28.json.gz")
TOURISM_SNAPSHOT = Path("/mnt/stateful_partition/antigravity/gdrive/life_assistantGPT/台灣活動探索｜排程步驟/官方來源快照/tourism-2026-10-28.zip")


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


async def get_existing_db_keys() -> Dict[str, str]:
    from sqlalchemy import select
    from app.models.curated import CuratedActivity
    async with SessionLocal() as db:
        res = await db.scalars(select(CuratedActivity))
        return {row.handoff_event_key: row.title for row in res if row.handoff_event_key}


def extract_tourism_candidates(existing_keys: Dict[str, str]) -> List[Dict[str, Any]]:
    with zipfile.ZipFile(TOURISM_SNAPSHOT) as zf:
        b = zf.read("EventList.json")
        if b.startswith(b"\xef\xbb\xbf"):
            b = b[3:]
        tourism_data = json.loads(b.decode("utf-8"))

    events = tourism_data.get("Events", [])
    active = [e for e in events if e.get("EndDateTime") and e.get("EndDateTime")[:10] >= "2026-10-28"]
    logger.info(f"Loaded {len(active)} active Tourism events from snapshot")

    candidates = []
    for e in active:
        ev_id = e.get("EventID")
        ev_key = f"taiwan.net.tw:{ev_id}"
        if ev_key in existing_keys:
            continue

        name = e.get("EventName", "").strip()
        if not name or len(name) < 2:
            continue
        if any(k in name for k in ["APP", "攝影比賽", "徵選", "徵件"]):
            continue

        city = e.get("PostalAddress", {}).get("City", "").strip()
        town = e.get("PostalAddress", {}).get("Town", "").strip()
        if not city:
            continue

        start_dt = e.get("StartDateTime", "").strip()
        end_dt = e.get("EndDateTime", "").strip()
        if not start_dt or not end_dt:
            continue
        if not start_dt.endswith("+08:00") and "T" in start_dt:
            start_dt += "+08:00"
        if not end_dt.endswith("+08:00") and "T" in end_dt:
            end_dt += "+08:00"

        addr = e.get("PostalAddress", {}).get("StreetAddress", "").strip() or f"{city}{town}"
        web = e.get("WebsiteURL") or "https://www.taiwan.net.tw/"
        if not (web.startswith("http://") or web.startswith("https://")):
            web = "https://www.taiwan.net.tw/"

        is_free = e.get("IsAccessibleForFree", 0)
        fee_info = (e.get("FeeInfo") or "").strip()

        cat_raw = e.get("EventClasses", [])
        cat_str = "地方節慶／觀光活動"
        if any("藝文" in str(c) for c in cat_raw) or "展" in name or "音樂" in name:
            cat_str = "藝文展演／文化節慶"
        elif "市集" in name:
            cat_str = "地方市集／特色生活"
        elif "馬拉松" in name or "單車" in name or "運動" in name or "健行" in name:
            cat_str = "運動休閒／戶外健行"

        org = "交通部觀光署"
        if e.get("Organizations"):
            if isinstance(e["Organizations"], list) and e["Organizations"]:
                org = e["Organizations"][0].get("Organizer") or org
            elif isinstance(e["Organizations"], dict):
                org = e["Organizations"].get("Organizer") or org

        summary = f"交通部觀光署官方核實：{city}{town}{name}，展期自{start_dt[:10]}至{end_dt[:10]}，地點：{addr}。"
        if len(summary) > 400:
            summary = summary[:397] + "..."

        row = {
            "event_key": ev_key,
            "parent_event_key": ev_key,
            "record_type": "main",
            "title": name,
            "city": city,
            "district": town or None,
            "category": cat_str,
            "organizer": org,
            "start_at_tpe": start_dt,
            "end_at_tpe": end_dt,
            "venue": addr,
            "official_url": web,
            "registration_url": None,
            "source_url": "https://media.taiwan.net.tw/",
            "importance_star": 3,
            "opportunity_type": "一般活動",
            "registration_open_at_tpe": None,
            "registration_deadline_at_tpe": None,
            "nonrefundable_cost_ntd": "0.00" if (is_free == 1 or "免費" in fee_info or fee_info == "") else None,
            "refundable_deposit_ntd": "0.00",
            "verified_benefit_ntd": None,
            "eligibility_limit": fee_info or "自由參加",
            "evidence_summary": summary,
            "verified_at_tpe": NOW_TPE_STR,
            "handoff_updated_at_tpe": NOW_TPE_STR,
            "verification_status": "verified",
        }
        try:
            HandoffItem.model_validate(row)
            row["content_hash"] = canonical_hash(row)
            row["handoff_status"] = "READY"
            row["life_ack_at_tpe"] = ""
            row["life_import_result"] = ""
            row["life_error"] = ""
            candidates.append(row)
        except Exception as err:
            logger.warning(f"Tourism item {name} failed validation: {err}")

    logger.info(f"Qualified {len(candidates)} distinct active Tourism candidates")
    return candidates


def extract_culture_candidates(existing_keys: Dict[str, str], limit: int = 100) -> List[Dict[str, Any]]:
    with gzip.open(CULTURE_SNAPSHOT, "rb") as f:
        culture_data = json.loads(f.read().decode("utf-8"))

    logger.info(f"Loaded {len(culture_data)} Culture records from snapshot")
    candidates = []
    
    # Priority venues for high quality curation
    for item in culture_data:
        uid = item.get("UID")
        ev_key = f"culture:{uid}"
        if ev_key in existing_keys:
            continue

        title = item.get("title", "").strip()
        if not title or len(title) < 2:
            continue

        shows = item.get("showInfo", [])
        if not shows:
            continue
        show0 = shows[0]
        loc = (show0.get("locationName") or "").strip()
        addr = (show0.get("location") or "").strip()
        if not loc and not addr:
            continue
        venue_str = f"{loc}（{addr}）" if addr and loc and addr != loc else (loc or addr)
        if len(venue_str) > 500:
            venue_str = venue_str[:497] + "..."

        start_raw = item.get("startDate", "").strip().replace("/", "-")
        end_raw = item.get("endDate", "").strip().replace("/", "-")
        if not start_raw or not end_raw:
            continue
        if end_raw < "2026-10-28":
            continue

        start_dt = f"{start_raw}T09:00:00+08:00"
        end_dt = f"{end_raw}T18:00:00+08:00"

        city = None
        district = None
        city_match = re.search(r"(臺北市|台北市|新北市|桃園市|臺中市|台中市|臺南市|台南市|高雄市|基隆市|新竹市|嘉義市|新竹縣|苗栗縣|彰化縣|南投縣|雲林縣|嘉義縣|屏東縣|宜蘭縣|花蓮縣|臺東縣|台東縣|澎湖縣|金門縣|連江縣)", addr + " " + loc)
        if city_match:
            city = city_match.group(1).replace("台北市", "臺北市").replace("台中市", "臺中市").replace("台南市", "臺南市").replace("台東市", "臺東市").replace("台東縣", "臺東縣")
            dist_match = re.search(r"([^\s市縣]+[區鄉鎮市])", (addr + " " + loc).replace(city, ""))
            if dist_match:
                district = dist_match.group(1)

        web = item.get("webSales") or item.get("sourceWebPromote") or "https://cloud.culture.tw/"
        if not (web.startswith("http://") or web.startswith("https://")):
            web = "https://cloud.culture.tw/"

        master = item.get("masterUnit", [])
        org = "文化部"
        if master and isinstance(master, list) and master[0]:
            org = str(master[0]).strip()
        elif isinstance(master, str) and master:
            org = master.strip()
        if len(org) > 200:
            org = org[:197] + "..."

        price_info = (show0.get("price") or "").strip()
        is_free = "免費" in price_info or price_info == "0" or price_info == ""

        summary = f"文化部全國藝文快照核實：{loc}《{title}》，展期{start_raw}至{end_raw}。"
        if len(summary) > 400:
            summary = summary[:397] + "..."

        row = {
            "event_key": ev_key,
            "parent_event_key": ev_key,
            "record_type": "main",
            "title": title,
            "city": city,
            "district": district,
            "category": "藝文展演／表演藝術",
            "organizer": org,
            "start_at_tpe": start_dt,
            "end_at_tpe": end_dt,
            "venue": venue_str,
            "official_url": web,
            "registration_url": web if ("opentix" in web or "kktix" in web) else None,
            "source_url": "https://cloud.culture.tw/",
            "importance_star": 3,
            "opportunity_type": "報名" if ("opentix" in web or "kktix" in web) else "一般活動",
            "registration_open_at_tpe": None,
            "registration_deadline_at_tpe": None,
            "nonrefundable_cost_ntd": "0.00" if is_free else None,
            "refundable_deposit_ntd": "0.00",
            "verified_benefit_ntd": None,
            "eligibility_limit": price_info or "自由參加",
            "evidence_summary": summary,
            "verified_at_tpe": NOW_TPE_STR,
            "handoff_updated_at_tpe": NOW_TPE_STR,
            "verification_status": "verified",
        }
        try:
            HandoffItem.model_validate(row)
            row["content_hash"] = canonical_hash(row)
            row["handoff_status"] = "READY"
            row["life_ack_at_tpe"] = ""
            row["life_import_result"] = ""
            row["life_error"] = ""
            candidates.append(row)
            if len(candidates) >= limit:
                break
        except Exception as err:
            logger.warning(f"Culture item {title} failed validation: {err}")

    logger.info(f"Qualified {len(candidates)} distinct Culture candidates")
    return candidates


async def main():
    logger.info("=== Starting Snapshots Ingestion into Curated Pool & Life DB ===")
    existing_db = await get_existing_db_keys()
    logger.info(f"Current PostgreSQL curated_activities count: {len(existing_db)}")

    tourism_candidates = extract_tourism_candidates(existing_db)
    culture_candidates = extract_culture_candidates(existing_db, limit=100)

    new_events = tourism_candidates + culture_candidates
    logger.info(f"Total new events to add: {len(new_events)} (Tourism={len(tourism_candidates)}, Culture={len(culture_candidates)})")

    if not new_events:
        logger.info("No new events to add. All candidates already in DB.")
        return

    # Check capacity in handoff sheet
    wb_handoff = openpyxl.load_workbook(HANDOFF_LOCAL)
    ws_handoff = wb_handoff["交接資料"]
    existing_sheet_keys = {ws_handoff.cell(r, 1).value for r in range(2, ws_handoff.max_row + 1) if ws_handoff.cell(r, 1).value}
    
    # Find last occupied row
    last_r = 1
    for r in range(2, ws_handoff.max_row + 1):
        if ws_handoff.cell(r, 1).value:
            last_r = r

    logger.info(f"Existing rows in handoff sheet: {last_r - 1}")

    added_count = 0
    for ev in new_events:
        if ev["event_key"] in existing_sheet_keys:
            continue
        last_r += 1
        cols_map = {
            1: ev["event_key"],
            2: ev["content_hash"],
            3: ev["parent_event_key"],
            4: ev["record_type"],
            5: ev["title"],
            6: ev["city"] or "",
            7: ev["district"] or "",
            8: ev["category"],
            9: ev["organizer"],
            10: ev["start_at_tpe"],
            11: ev["end_at_tpe"],
            12: ev["venue"] or "",
            13: ev["official_url"],
            14: ev["registration_url"] or "",
            15: ev["source_url"] or "",
            16: ev["importance_star"],
            17: ev["opportunity_type"],
            18: ev["registration_open_at_tpe"] or "",
            19: ev["registration_deadline_at_tpe"] or "",
            20: ev["nonrefundable_cost_ntd"] or "",
            21: ev["refundable_deposit_ntd"] or "",
            22: ev["verified_benefit_ntd"] or "",
            23: ev["eligibility_limit"] or "",
            24: ev["evidence_summary"],
            25: ev["verified_at_tpe"],
            26: ev["handoff_status"],
            27: ev["handoff_updated_at_tpe"],
            28: ev["life_ack_at_tpe"],
            29: ev["life_import_result"],
            30: ev["life_error"],
            31: ev["verification_status"],
        }
        for c_idx, val in cols_map.items():
            ws_handoff.cell(last_r, c_idx, val)
        existing_sheet_keys.add(ev["event_key"])
        added_count += 1

    wb_handoff.save(HANDOFF_LOCAL)
    wb_handoff.close()
    logger.info(f"Appended {added_count} new READY records to {HANDOFF_LOCAL}")

    # Sync to Drive handoff copy
    import shutil
    shutil.copy2(HANDOFF_LOCAL, HANDOFF_DRIVE)
    logger.info(f"Synchronized updated handoff sheet to {HANDOFF_DRIVE}")

    # Run Life Importer on the updated handoff sheet
    logger.info("Executing Life Importer (run_exclusive_import) against PostgreSQL...")
    os.environ["LIFE_CURATED_SHEET_ID"] = "1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4"
    os.environ["LIFE_CURATED_IMPORT_APPLY"] = "1"

    adapter = LocalSheetAdapter(HANDOFF_LOCAL)
    async with engine.begin() as guard:
        import_result = await run_exclusive_import(guard, sheet=adapter)
        logger.info(f"Life Importer Transaction Succeeded: {import_result}")

    # Sync back the ACKed handoff sheet to Google Drive
    shutil.copy2(HANDOFF_LOCAL, HANDOFF_DRIVE)
    logger.info("Synchronized ACKed handoff sheet back to Google Drive.")

    # Readback verify PostgreSQL curated_activities
    updated_db = await get_existing_db_keys()
    logger.info(f"=== INGESTION COMPLETE: PostgreSQL curated_activities count is now {len(updated_db)} (+{len(updated_db) - len(existing_db)}) ===")


if __name__ == "__main__":
    asyncio.run(main())
