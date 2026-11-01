"""Taipei/New Taipei 41-district Food Discounts batch helper & PostgreSQL sync.

Implements V0.5.2 / Runbook V1.3.2:
1. Exports/reads the canonical Google Sheet from `life_assistantGPT/美食優惠探索｜試行`.
2. Verifies V1.3.2 ARRAYFORMULA anchor integrity (`總排程測試` C10 == 0).
3. Parses `優惠候選` (A:AL) including Excel serial dates and visibility status.
4. Upserts records into Life PostgreSQL `food_discounts` table.
"""
import argparse
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

TAIPEI = ZoneInfo("Asia/Taipei")
EXCEL_EPOCH = date(1899, 12, 30)
RCLONE_BIN = "/mnt/stateful_partition/antigravity/.local/bin/rclone"
RCLONE_CONF = "/home/tommylin15_gmail_com/.config/rclone/rclone.conf"
GDRIVE_FOLDER = "gdrive:life_assistantGPT/美食優惠探索｜試行"
SHEET_FILENAME = "上班族美食優惠｜台北12區試行池與20%以上精選門檻｜2026-10-30.xlsx"

ROTATION_DISTRICTS: dict[int, list[str]] = {
    0: [  # Monday (14)
        "台北市中正區", "台北市中山區", "台北市松山區", "台北市大安區", "台北市信義區",
        "新北市板橋區", "新北市中和區", "新北市永和區", "新北市新莊區", "新北市三重區",
        "新北市新店區", "新北市汐止區", "新北市林口區", "新北市蘆洲區",
    ],
    2: [  # Wednesday (14)
        "台北市大同區", "台北市萬華區", "台北市文山區", "台北市南港區",
        "新北市土城區", "新北市樹林區", "新北市鶯歌區", "新北市三峽區", "新北市淡水區",
        "新北市五股區", "新北市泰山區", "新北市瑞芳區", "新北市深坑區", "新北市八里區",
    ],
    4: [  # Friday (13)
        "台北市內湖區", "台北市士林區", "台北市北投區",
        "新北市石碇區", "新北市坪林區", "新北市三芝區", "新北市石門區", "新北市平溪區",
        "新北市雙溪區", "新北市貢寮區", "新北市金山區", "新北市萬里區", "新北市烏來區",
    ],
}

TAIPEI_12 = {
    "中正", "大同", "中山", "松山", "大安", "信義",
    "萬華", "文山", "南港", "內湖", "士林", "北投",
}
NEW_TAIPEI_29 = {
    "板橋", "三重", "中和", "永和", "新莊", "新店", "土城", "蘆洲", "樹林", "鶯歌",
    "三峽", "淡水", "汐止", "瑞芳", "五股", "泰山", "林口", "深坑", "石碇", "坪林",
    "三芝", "石門", "八里", "平溪", "雙溪", "貢寮", "金山", "萬里", "烏來",
}


def export_sheet_from_gdrive(target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        RCLONE_BIN,
        "copy",
        f"{GDRIVE_FOLDER}/{SHEET_FILENAME}",
        str(target_dir),
        "--config",
        RCLONE_CONF,
        "--drive-export-formats",
        "xlsx",
    ]
    subprocess.run(cmd, check=True)
    return target_dir / SHEET_FILENAME


def parse_excel_date(raw: str | None) -> date | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text or text == "None":
        return None
    if re.fullmatch(r"\d+(\.\d+)?", text):
        days = int(float(text))
        if 30000 <= days <= 70000:
            return EXCEL_EPOCH + timedelta(days=days)
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def parse_decimal(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text or text == "None":
        return None
    try:
        val = Decimal(text)
        return val.quantize(Decimal("0.01")) if val >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def infer_city(district_raw: str | None) -> str:
    if not district_raw:
        return "雙北"
    d = district_raw.strip()
    if d.startswith(("台北市", "臺北市")):
        return "台北市"
    if d.startswith("新北市"):
        return "新北市"
    short = d.removesuffix("區")
    if short in TAIPEI_12:
        return "台北市"
    if short in NEW_TAIPEI_29:
        return "新北市"
    return "雙北"


def read_xlsx_sheets(xlsx_path: Path) -> dict[str, list[dict[str, str]]]:
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    out: dict[str, list[dict[str, str]]] = {}
    with zipfile.ZipFile(xlsx_path) as z:
        sst: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            sst_xml = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sst_xml.findall("s:si", ns):
                sst.append("".join(t.text or "" for t in si.findall(".//s:t", ns)))

        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {el.attrib["Id"]: el.attrib["Target"] for el in rels}

        for sh in wb.findall(".//s:sheet", ns):
            name = sh.attrib["name"]
            rid = sh.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = "xl/" + rel_map[rid].lstrip("/")
            ws = ET.fromstring(z.read(target))
            rows_list: list[dict[str, str]] = []
            for r in ws.findall(".//s:row", ns):
                vals: dict[str, str] = {"_row": r.attrib.get("r", "")}
                for c in r.findall("s:c", ns):
                    col = "".join(ch for ch in c.attrib.get("r", "") if ch.isalpha())
                    t = c.attrib.get("t")
                    v_el = c.find("s:v", ns)
                    is_el = c.find("s:is", ns)
                    val: str | None = None
                    if t == "s" and v_el is not None and v_el.text is not None:
                        val = sst[int(v_el.text)]
                    elif t == "inlineStr" and is_el is not None:
                        val = "".join(x.text or "" for x in is_el.findall(".//s:t", ns))
                    elif v_el is not None and v_el.text is not None:
                        val = v_el.text
                    if val is not None and val != "":
                        vals[col] = val
                rows_list.append(vals)
            out[name] = rows_list
    return out


def extract_candidates(xlsx_path: Path) -> tuple[list[dict], dict]:
    sheets = read_xlsx_sheets(xlsx_path)
    candidates_sheet = sheets.get("優惠候選", [])
    qa_sheet = sheets.get("總排程測試", [])

    c10_val = None
    for r in qa_sheet:
        if r.get("_row") == "10":
            c10_val = r.get("C")

    records: list[dict] = []
    for r in candidates_sheet:
        if r.get("_row") == "1":
            continue
        key = (r.get("A") or "").strip()
        if not key:
            continue
        source_url = (r.get("N") or "").strip()
        merchant = (r.get("C") or "").strip()
        summary = (r.get("E") or "").strip()
        if not source_url or not merchant or not summary:
            continue
        district = (r.get("B") or "").strip() or None
        city = infer_city(district)
        note_parts = [p.strip() for p in (r.get("P"), r.get("S")) if p and p.strip()]
        records.append({
            "candidate_key": key,
            "city": city,
            "district": district,
            "merchant": merchant,
            "category": (r.get("D") or "").strip() or None,
            "offer_summary": summary,
            "offer_type": (r.get("F") or "").strip() or None,
            "nominal_discount": (r.get("G") or "").strip() or None,
            "fixed_discount_ntd": parse_decimal(r.get("H")),
            "original_price_ntd": parse_decimal(r.get("I")),
            "offer_price_ntd": parse_decimal(r.get("J")),
            "period_text": (r.get("L") or "").strip() or None,
            "address": (r.get("M") or "").strip() or None,
            "source_url": source_url,
            "notes": "；".join(note_parts) if note_parts else None,
            "claim_status": (r.get("R") or "COLLECTED_SOURCE_CLAIM").strip(),
            "visibility_status": (r.get("AI") or "NOT_LISTED").strip(),
            "first_seen_on": parse_excel_date(r.get("AA")) or parse_excel_date(r.get("Q")) or parse_excel_date(r.get("T")),
            "claim_deadline_on": parse_excel_date(r.get("AB")),
            "redemption_ends_on": parse_excel_date(r.get("AC")),
            "offer_ends_on": parse_excel_date(r.get("AD")),
            "last_positive_on": parse_excel_date(r.get("AE")),
            "next_refresh_on": parse_excel_date(r.get("AG")),
            "date_basis": (r.get("AJ") or "").strip() or None,
            "disclosure": (r.get("U") or "公開來源宣稱，未逐項核實，不保證到店可使用").strip(),
            "details": {
                "legacy_rule_status": r.get("O"),
                "source_kind": r.get("Y"),
                "dedupe_key": r.get("Z"),
                "refresh_outcome": r.get("AK"),
            },
        })

    now_tpe = datetime.now(TAIPEI)
    today_tpe = now_tpe.date()
    batch_id = f"FOOD-UNIFIED-{today_tpe.strftime('%Y%m%d')}"
    rotation = ROTATION_DISTRICTS.get(today_tpe.weekday(), [])
    diagnostics = {
        "batch_id": batch_id,
        "date_tpe": today_tpe.isoformat(),
        "weekday": today_tpe.strftime("%a").upper(),
        "is_search_day": bool(rotation),
        "scheduled_districts_count": len(rotation),
        "scheduled_queries_target": len(rotation) * 2,
        "total_candidates_in_sheet": len(records),
        "visible_source_only_count": sum(
            1 for x in records
            if x["claim_status"] == "COLLECTED_SOURCE_CLAIM"
            and x["visibility_status"] == "VISIBLE_SOURCE_ONLY"
        ),
        "qa_c10_missing_formulas": int(float(c10_val)) if c10_val is not None else None,
    }
    return records, diagnostics


async def sync_to_database(records: list[dict], batch_id: str) -> dict:
    from app.api.food_discounts import FoodDiscountIn, upsert_food_discounts_batch
    from app.db.session import SessionLocal

    validated: list[FoodDiscountIn] = []
    skipped = 0
    for raw in records:
        try:
            validated.append(FoodDiscountIn.model_validate(raw))
        except Exception:
            skipped += 1
    if not validated:
        return {"accepted": 0, "skipped": skipped}
    async with SessionLocal() as db:
        res = await upsert_food_discounts_batch(
            db, validated, actor=f"batch:{batch_id}"
        )
        return {**res, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-path", type=Path, default=None)
    parser.add_argument("--export-dir", type=Path, default=Path("/tmp/food_discounts_sync"))
    parser.add_argument("--sync-db", action="store_true")
    args = parser.parse_args()

    xlsx_path = args.xlsx_path or export_sheet_from_gdrive(args.export_dir)
    records, diag = extract_candidates(xlsx_path)
    if diag.get("qa_c10_missing_formulas") not in (0, None):
        print(f"food_discounts_qa_c10=FAIL missing={diag['qa_c10_missing_formulas']}", file=sys.stderr)
        return 1

    if args.sync_db:
        sync_res = asyncio.run(sync_to_database(records, diag["batch_id"]))
        diag["db_sync"] = sync_res

    print(json.dumps(diag, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
