"""Taipei/New Taipei 41-district Food Discounts Handoff Pool & PostgreSQL ACK sync.

Implements V0.5.2 / Runbook V1.3.2 + Handoff Pool (`美食優惠｜交接資料.xlsx`):
1. Exports/reads the canonical Google Sheet from `life_assistantGPT/美食優惠探索｜試行`.
2. Verifies V1.3.2 ARRAYFORMULA anchor integrity (`總排程測試` C10 == 0).
3. Syncs candidates into the Handoff Pool (`美食優惠｜交接資料.xlsx`, tab `交接資料`, 31 columns A:AE):
   - Preserves existing `ACKED` rows when `content_hash` (Canonical SHA-256) is unchanged.
   - Marks new or modified rows as `READY`.
4. When `--sync-db` is enabled, imports Handoff Pool rows into Life PostgreSQL `food_discounts`
   and writes back `ACKED` (`CREATED` / `UPDATED` / `UNCHANGED`) or `ERROR` to `美食優惠｜交接資料.xlsx`
   with readback verification.
"""
import argparse
import asyncio
import ctypes
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from xml.sax.saxutils import escape as xml_escape
import xml.etree.ElementTree as ET
import zipfile

try:
    ctypes.CDLL("/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6", mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

TAIPEI = timezone(timedelta(hours=8))
EXCEL_EPOCH = date(1899, 12, 30)
RCLONE_BIN = "/mnt/stateful_partition/antigravity/.local/bin/rclone"
RCLONE_CONF = "/home/tommylin15_gmail_com/.config/rclone/rclone.conf"
GDRIVE_FOLDER = "gdrive:agy_workspace/life_assistantGPT/美食優惠探索｜試行"
SHEET_FILENAME = "上班族美食優惠｜台北12區試行池與20%以上精選門檻｜2026-10-30.xlsx"
HANDOFF_FILENAME = "美食優惠｜交接資料.xlsx"
HANDOFF_TAB = "交接資料"

BUSINESS_FIELDS = (
    "candidate_key",
    "city",
    "district",
    "merchant",
    "category",
    "offer_summary",
    "offer_type",
    "nominal_discount",
    "fixed_discount_ntd",
    "original_price_ntd",
    "offer_price_ntd",
    "period_text",
    "address",
    "source_url",
    "notes",
    "claim_status",
    "visibility_status",
    "first_seen_on",
    "claim_deadline_on",
    "redemption_ends_on",
    "offer_ends_on",
    "last_positive_on",
    "next_refresh_on",
    "date_basis",
    "disclosure",
)

HEADERS = (
    "candidate_key",
    "content_hash",
    *BUSINESS_FIELDS[1:],
    "handoff_status",
    "handoff_updated_at_tpe",
    "life_ack_at_tpe",
    "life_import_result",
    "life_error",
)

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


def _normalize_hash_value(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val.quantize(Decimal("0.01")))
    text_val = str(val).strip()
    return text_val if text_val else None


def canonical_food_hash(record: dict) -> str:
    payload = {k: _normalize_hash_value(record.get(k)) for k in BUSINESS_FIELDS}
    canonical_str = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def export_sheet_from_gdrive(target_dir: Path, filename: str = SHEET_FILENAME, required: bool = True) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        RCLONE_BIN,
        "copy",
        f"{GDRIVE_FOLDER}/{filename}",
        str(target_dir),
        "--config",
        RCLONE_CONF,
        "--drive-export-formats",
        "xlsx",
    ]
    res = subprocess.run(cmd, check=False, capture_output=True, text=True)
    local_path = target_dir / filename
    if required and (res.returncode != 0 or not local_path.exists()):
        raise RuntimeError(f"Failed to export {filename} from Google Drive: {res.stderr}")
    return local_path


def upload_sheet_to_gdrive(local_path: Path) -> None:
    cmd = [
        RCLONE_BIN,
        "copyto",
        str(local_path),
        f"{GDRIVE_FOLDER}/{local_path.name}",
        "--config",
        RCLONE_CONF,
    ]
    subprocess.run(cmd, check=True)


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


def _col_index_to_letters(idx_1based: int) -> str:
    out = ""
    n = idx_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _col_letters_to_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n


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
            raw_target = rel_map[rid].lstrip("/")
            target = raw_target if raw_target.startswith("xl/") else f"xl/{raw_target}"
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


def read_handoff_xlsx(xlsx_path: Path) -> list[dict[str, str]]:
    if not xlsx_path.exists():
        return []
    sheets = read_xlsx_sheets(xlsx_path)
    sheet_rows = sheets.get(HANDOFF_TAB, [])
    if not sheet_rows:
        return []
    out: list[dict[str, str]] = []
    for r in sheet_rows:
        if r.get("_row") == "1":
            continue
        row_dict: dict[str, str] = {}
        for idx, key in enumerate(HEADERS, start=1):
            col = _col_index_to_letters(idx)
            row_dict[key] = (r.get(col) or "").strip()
        if any(row_dict.values()):
            out.append(row_dict)
    return out


def write_handoff_xlsx(xlsx_path: Path, rows: list[dict[str, str]]) -> None:
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows: list[list[str]] = [list(HEADERS)]
    for r in rows:
        all_rows.append([str(r.get(k) or "") for k in HEADERS])

    try:
        import openpyxl  # type: ignore

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = HANDOFF_TAB
        for row_vals in all_rows:
            ws.append(row_vals)
        wb.save(xlsx_path)
        wb.close()
        return
    except ImportError:
        pass

    sheet_rows_xml: list[str] = []
    for r_idx, row_vals in enumerate(all_rows, start=1):
        cells_xml: list[str] = []
        for c_idx, val in enumerate(row_vals, start=1):
            if val == "":
                continue
            col_ref = f"{_col_index_to_letters(c_idx)}{r_idx}"
            cells_xml.append(
                f'<c r="{col_ref}" t="inlineStr"><is><t>{xml_escape(str(val))}</t></is></c>'
            )
        sheet_rows_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows_xml)}</sheetData>'
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{HANDOFF_TAB}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    wb_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )
    with zipfile.ZipFile(xlsx_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types_xml)
        z.writestr("_rels/.rels", root_rels_xml)
        z.writestr("xl/workbook.xml", workbook_xml)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        z.writestr("xl/worksheets/sheet1.xml", worksheet_xml)


def extract_candidates(xlsx_path: Path) -> tuple[list[dict], dict]:
    sheets = read_xlsx_sheets(xlsx_path)
    candidates_sheet = sheets.get("優惠候選", [])
    qa_sheet = sheets.get("總排程測試", [])

    c10_val = None
    for r in qa_sheet:
        if r.get("_row") == "10":
            c10_val = r.get("C")

    now_tpe = datetime.now(TAIPEI)
    today_tpe = now_tpe.date()

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

        claim_status = (r.get("R") or "COLLECTED_SOURCE_CLAIM").strip()
        first_seen_on = parse_excel_date(r.get("AA")) or parse_excel_date(r.get("Q")) or parse_excel_date(r.get("T"))
        claim_deadline_on = parse_excel_date(r.get("AB"))
        redemption_ends_on = parse_excel_date(r.get("AC"))
        offer_ends_on = parse_excel_date(r.get("AD"))
        last_positive_on = parse_excel_date(r.get("AE"))
        next_refresh_on = parse_excel_date(r.get("AG"))
        date_basis = (r.get("AJ") or "").strip() or None

        # ponytail: Evaluate canonical AI2 formula deterministically under Asia/Taipei today.
        # Eliminates server export timezone lag between Google Drive (UTC) and Asia/Taipei (UTC+8).
        if claim_status == "SOURCE_EXPIRED/SOLD_OUT":
            computed_vis = "ARCHIVED_EXPIRED"
        elif claim_status != "COLLECTED_SOURCE_CLAIM":
            computed_vis = "NOT_LISTED"
        elif offer_ends_on and today_tpe > offer_ends_on:
            computed_vis = "EXPIRED"
        elif claim_deadline_on and today_tpe > claim_deadline_on:
            computed_vis = "CLAIM_CLOSED"
        elif date_basis == "DATE_UNPARSED":
            computed_vis = "HIDDEN_DATE_REVIEW"
        elif offer_ends_on:
            computed_vis = "VISIBLE_SOURCE_ONLY"
        elif not first_seen_on:
            computed_vis = "HIDDEN_DATE_REVIEW"
        else:
            anchor = last_positive_on or first_seen_on
            days_since = (today_tpe - anchor).days
            if days_since >= 30:
                computed_vis = "ARCHIVED_STALE"
            elif days_since >= 7:
                computed_vis = "HIDDEN_REFRESH_DUE"
            else:
                computed_vis = "VISIBLE_SOURCE_ONLY"

        visibility_status = computed_vis

        rec = {
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
            "claim_status": claim_status,
            "visibility_status": visibility_status,
            "first_seen_on": first_seen_on,
            "claim_deadline_on": claim_deadline_on,
            "redemption_ends_on": redemption_ends_on,
            "offer_ends_on": offer_ends_on,
            "last_positive_on": last_positive_on,
            "next_refresh_on": next_refresh_on,
            "date_basis": date_basis,
            "disclosure": (r.get("U") or "公開來源宣稱，未逐項核實，不保證到店可使用").strip(),
        }
        rec["content_hash"] = canonical_food_hash(rec)
        records.append(rec)

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


def stage_handoff_sheet(
    candidates: list[dict], handoff_path: Path, now_tpe_iso: str
) -> dict:
    existing_rows = read_handoff_xlsx(handoff_path)
    existing_map = {r["candidate_key"]: r for r in existing_rows if r.get("candidate_key")}

    merged_rows: list[dict[str, str]] = []
    preserved_acked = 0
    staged_ready = 0

    for cand in candidates:
        ck = cand["candidate_key"]
        chash = cand["content_hash"]
        prev = existing_map.get(ck)
        row_str: dict[str, str] = {"candidate_key": ck, "content_hash": chash}
        for bf in BUSINESS_FIELDS[1:]:
            norm = _normalize_hash_value(cand.get(bf))
            row_str[bf] = norm if norm is not None else ""

        if (
            prev is not None
            and prev.get("content_hash") == chash
            and prev.get("handoff_status") == "ACKED"
            and prev.get("life_ack_at_tpe")
            and prev.get("life_import_result") in ("CREATED", "UPDATED", "UNCHANGED")
        ):
            row_str["handoff_status"] = "ACKED"
            row_str["handoff_updated_at_tpe"] = prev.get("handoff_updated_at_tpe") or now_tpe_iso
            row_str["life_ack_at_tpe"] = prev["life_ack_at_tpe"]
            row_str["life_import_result"] = prev["life_import_result"]
            row_str["life_error"] = ""
            preserved_acked += 1
        else:
            row_str["handoff_status"] = "READY"
            row_str["handoff_updated_at_tpe"] = now_tpe_iso
            row_str["life_ack_at_tpe"] = ""
            row_str["life_import_result"] = ""
            row_str["life_error"] = ""
            staged_ready += 1

        merged_rows.append(row_str)

    write_handoff_xlsx(handoff_path, merged_rows)
    return {
        "handoff_total_rows": len(merged_rows),
        "preserved_acked": preserved_acked,
        "staged_ready": staged_ready,
    }


async def execute_handoff_import_and_ack(handoff_path: Path, now_tpe_iso: str) -> dict:
    from app.db.session import SessionLocal
    from app.services.food_discount_handoff import (
        food_record_acknowledged,
        parse_food_handoff_rows,
        upsert_food_handoff,
        validate_food_handoff_record,
    )

    raw_rows = read_handoff_xlsx(handoff_path)
    matrix = [list(HEADERS)] + [[r.get(k, "") for k in HEADERS] for r in raw_rows]
    records = parse_food_handoff_rows(matrix)

    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "invalid": 0,
        "import_failed": 0,
    }

    async with SessionLocal() as db:
        for rec in records:
            try:
                item = validate_food_handoff_record(rec)
            except Exception as exc:
                counts["invalid"] += 1
                rec["handoff_status"] = "ERROR"
                rec["life_ack_at_tpe"] = now_tpe_iso
                rec["life_import_result"] = "FAILED"
                rec["life_error"] = f"validation_error:{type(exc).__name__}"[:180]
                continue

            try:
                result = await upsert_food_handoff(db, item, rec["content_hash"])
                counts[result.lower()] += 1
                if not (result == "UNCHANGED" and food_record_acknowledged(rec)):
                    rec["handoff_status"] = "ACKED"
                    rec["life_ack_at_tpe"] = now_tpe_iso
                    rec["life_import_result"] = result
                    rec["life_error"] = ""
            except Exception as exc:
                await db.rollback()
                counts["import_failed"] += 1
                rec["handoff_status"] = "ERROR"
                rec["life_ack_at_tpe"] = now_tpe_iso
                rec["life_import_result"] = "FAILED"
                rec["life_error"] = f"import_error:{type(exc).__name__}"[:180]

    write_handoff_xlsx(handoff_path, records)

    readback = read_handoff_xlsx(handoff_path)
    acked = sum(1 for r in readback if r.get("handoff_status") == "ACKED")
    ready = sum(1 for r in readback if r.get("handoff_status") == "READY")
    errors = sum(1 for r in readback if r.get("handoff_status") == "ERROR")

    return {
        **counts,
        "readback_total": len(readback),
        "readback_acked": acked,
        "readback_ready": ready,
        "readback_error": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-path", type=Path, default=None)
    parser.add_argument("--handoff-path", type=Path, default=None)
    parser.add_argument("--export-dir", type=Path, default=Path("/tmp/food_discounts_sync"))
    parser.add_argument("--stage-handoff", action="store_true")
    parser.add_argument("--sync-db", action="store_true")
    parser.add_argument("--upload-gdrive", action="store_true")
    args = parser.parse_args()

    xlsx_path = args.xlsx_path or export_sheet_from_gdrive(args.export_dir, SHEET_FILENAME, required=True)
    handoff_path = args.handoff_path or (args.export_dir / HANDOFF_FILENAME)
    if args.handoff_path is None and not handoff_path.exists():
        export_sheet_from_gdrive(args.export_dir, HANDOFF_FILENAME, required=False)

    records, diag = extract_candidates(xlsx_path)
    if diag.get("qa_c10_missing_formulas") not in (0, None):
        print(f"food_discounts_qa_c10=FAIL missing={diag['qa_c10_missing_formulas']}", file=sys.stderr)
        return 1

    now_tpe_iso = datetime.now(TAIPEI).replace(microsecond=0).isoformat()

    if args.stage_handoff or args.sync_db:
        stage_res = stage_handoff_sheet(records, handoff_path, now_tpe_iso)
        diag["handoff_stage"] = stage_res

    if args.sync_db:
        sync_res = asyncio.run(execute_handoff_import_and_ack(handoff_path, now_tpe_iso))
        diag["handoff_import"] = sync_res
        if sync_res["readback_ready"] != 0 or sync_res["readback_error"] != 0:
            print(f"food_discounts_handoff_ack=FAIL {sync_res}", file=sys.stderr)
            return 1

    if args.upload_gdrive and handoff_path.exists():
        upload_sheet_to_gdrive(handoff_path)
        diag["gdrive_handoff_uploaded"] = f"{GDRIVE_FOLDER}/{HANDOFF_FILENAME}"

    print(json.dumps(diag, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
