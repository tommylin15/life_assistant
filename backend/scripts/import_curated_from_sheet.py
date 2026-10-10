"""Daily fixed-Sheet handoff importer; commit first, then version-checked receipt."""
import asyncio
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import httpx
from pydantic import ValidationError
from app.db.session import SessionLocal, engine
from app.services.curated_handoff import HEADERS, BUSINESS_FIELDS, HandoffItem, upsert_handoff

SHEET_ID = "1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4"
TAB = "交接資料"
MAX_SHEET_ROWS = 1000
# shortcut: reject over 1000 outbox rows; add paged reads if 30-day cleanup exceeds this bound.


def parse_rows(values):
    if not values or tuple(values[0]) != HEADERS:
        raise ValueError("handoff_header_contract_mismatch")
    if len(values) > MAX_SHEET_ROWS + 1:
        raise ValueError("handoff_rows_exceed_limit")
    rows = []
    seen = set()
    for row in values[1:]:
        record = {key: str(row[i] if i < len(row) and row[i] is not None else "").strip()
                  for i, key in enumerate(HEADERS)}
        if not any(record.values()):
            continue
        if not record["event_key"] or record["event_key"] in seen:
            raise ValueError("missing_or_duplicate_event_key")
        seen.add(record["event_key"])
        if record["handoff_status"] not in ("READY", "ERROR", "ACKED"):
            raise ValueError("invalid_handoff_status")
        rows.append(record)
    return rows


def validate_record(record):
    # The Sheet owns canonical hashing; Life validates its version and payload.
    if not re.fullmatch(r"[a-f0-9]{64}", record["content_hash"]):
        raise ValueError("invalid_content_hash")
    return HandoffItem.model_validate({key: record[key] or None for key in BUSINESS_FIELDS + ("handoff_updated_at_tpe",)})


def acknowledged(record):
    # Only called after the database has verified this exact business version.
    return (record["handoff_status"] == "ACKED" and bool(record["life_ack_at_tpe"])
            and record["life_import_result"] in ("CREATED", "UPDATED", "UNCHANGED"))


class SheetClient:
    async def request(self, method, suffix, **kwargs):
        import google.auth
        from google.auth.transport.requests import Request
        def token():
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
            credentials.refresh(Request())
            return credentials.token
        access = await asyncio.to_thread(token)
        async with httpx.AsyncClient(timeout=25) as client:
            response = await client.request(method,
                f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/{suffix}",
                headers={"Authorization": f"Bearer {access}"}, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"sheets_http_{response.status_code}")
        return response.json()

    async def read(self):
        result = await self.request("GET", "values/" + quote(f"'{TAB}'!A1:AD1002", safe=""),
                                    params={"valueRenderOption": "FORMATTED_VALUE"})
        return result.get("values", [])

    async def receipt(self, snapshot, result, error=""):
        # Re-read by stable key, never stale row position. Do not ACK a changed
        # payload even if upstream accidentally retained its old content_hash.
        values = await self.read()
        records = parse_rows(values)
        matches = [r for r in records if r["event_key"] == snapshot["event_key"]]
        if len(matches) != 1 or any(matches[0][k] != snapshot[k] for k in BUSINESS_FIELDS + ("content_hash", "handoff_updated_at_tpe")):
            return False
        if not error and result == "UNCHANGED" and acknowledged(matches[0]):
            return True
        row_number = next(i for i, row in enumerate(values[1:], 2) if row and str(row[0]).strip() == snapshot["event_key"])
        now = datetime.now(timezone(timedelta(hours=8))).isoformat()
        await self.request("POST", "values:batchUpdate", json={"valueInputOption": "RAW", "data": [
            {"range": f"'{TAB}'!Z{row_number}", "values": [["ERROR" if error else "ACKED"]]},
            {"range": f"'{TAB}'!AB{row_number}:AD{row_number}", "values": [["" if error else now, "" if error else result, error]]},
        ]})
        readback = parse_rows(await self.read())
        current = next((r for r in readback if r["event_key"] == snapshot["event_key"]), None)
        return bool(current and all(current[k] == snapshot[k] for k in BUSINESS_FIELDS + ("content_hash",))
                    and current["life_import_result"] == ("" if error else result)
                    and current["handoff_status"] == ("ERROR" if error else "ACKED"))


async def run_import(sheet=None, sessions=SessionLocal):
    if os.environ.get("LIFE_CURATED_SHEET_ID", "") != SHEET_ID:
        raise ValueError("fixed_handoff_sheet_required")
    sheet = sheet or SheetClient()
    rows = parse_rows(await sheet.read())
    applying = os.environ.get("LIFE_CURATED_IMPORT_APPLY") == "1"
    result = {"run_id": uuid.uuid4().hex, "mode": "apply" if applying else "dry_run",
              "created": 0, "updated": 0, "unchanged": 0, "invalid": 0, "ack_failed": 0}
    for record in rows:
        # A bare Sheet receipt cannot prove which version is in PostgreSQL.
        # Recheck ACKED rows too; never skip a new version because of an old ACK.
        try:
            item = validate_record(record)
        except (ValueError, ValidationError):
            result["invalid"] += 1
            if applying and not await sheet.receipt(record, "INVALID", "invalid_handoff_record"):
                result["ack_failed"] += 1
            continue
        if not applying:
            continue
        try:
            async with sessions() as db:
                status = await upsert_handoff(db, item, record["content_hash"])
        except Exception:
            result["invalid"] += 1
            if not await sheet.receipt(record, "FAILED", "database_import_failed"):
                result["ack_failed"] += 1
            continue
        result[status.lower()] += 1
        if not await sheet.receipt(record, status):
            result["ack_failed"] += 1
    result["status"] = "PARTIAL" if result["invalid"] or result["ack_failed"] else "PASS"
    return result


async def main():
    try:
        result = await run_import()
        print("life_handoff_import " + " ".join(f"{k}={v}" for k, v in result.items()))
        if result["status"] != "PASS":
            raise RuntimeError("handoff_import_partial")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
