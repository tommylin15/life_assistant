"""Daily fixed-Sheet handoff importer; commit first, then version-checked receipt."""
import asyncio
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import httpx
from pydantic import ValidationError
from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.services.curated_handoff import HEADERS, BUSINESS_FIELDS, HandoffItem, upsert_handoff

SHEET_ID = "1OZdQPmypZ1zwB65K4oQOr3VBGP2GAFMmBnZsqAW5ob4"
TAB = "交接資料"
MAX_SHEET_ROWS = 1000
RECEIPT_BATCH_ROWS = 100
SHEETS_RETRYABLE = {429, 500, 502, 503, 504}
SHEETS_MAX_ATTEMPTS = 6
# Cross-process exclusion for GAS and manual fallback. Hold a dedicated
# transaction lock during the entire import; releases on error/container exit.
IMPORT_LOCK_KEY = 57926471020261015
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
    async def _access_token(self):
        import google.auth
        from google.auth.transport.requests import Request

        def token():
            credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
            credentials.refresh(Request())
            return credentials.token

        return await asyncio.to_thread(token)

    async def request(self, method, suffix, **kwargs):
        # Sheets has a per-minute quota. Batches reduce normal usage; bounded
        # backoff handles competing writers or temporary service throttling.
        access = await self._access_token()
        async with httpx.AsyncClient(timeout=25) as client:
            for attempt in range(SHEETS_MAX_ATTEMPTS):
                response = await client.request(
                    method, f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/{suffix}",
                    headers={"Authorization": f"Bearer {access}"}, **kwargs,
                )
                if response.status_code in SHEETS_RETRYABLE and attempt < SHEETS_MAX_ATTEMPTS - 1:
                    retry_after = response.headers.get("Retry-After", "")
                    try:
                        delay = min(60.0, max(1.0, float(retry_after)))
                    except ValueError:
                        delay = min(60.0, 2.0 * (2 ** attempt))
                    await asyncio.sleep(delay)
                    continue
                if response.status_code >= 400:
                    # Do not include response text: it can contain Sheet data.
                    raise RuntimeError(f"sheets_http_{response.status_code}")
                return response.json()

    async def read(self):
        result = await self.request("GET", "values/" + quote(f"'{TAB}'!A1:AD1002", safe=""),
                                    params={"valueRenderOption": "FORMATTED_VALUE"})
        return result.get("values", [])

    async def receipt(self, snapshot, result, error=""):
        # Compatibility helper for callers needing a single receipt.
        return (await self.receipts([(snapshot, result, error)]))[0]

    async def receipts(self, pending):
        if not pending:
            return []
        # One preflight read resolves current row numbers and fences business
        # versions. DB commits have already happened in run_import().
        values = await self.read()
        records = parse_rows(values)
        by_key = {row["event_key"]: (index, row)
                  for index, row in enumerate(records)}
        # The physical row number must come from the original Sheet, which can
        # include blank rows; the normalized records list is not a row index.
        row_numbers = {str(row[0]).strip(): i for i, row in enumerate(values[1:], 2)
                       if row and str(row[0]).strip()}
        outcomes = [False] * len(pending)
        writes = []
        expected = {}
        compare_fields = BUSINESS_FIELDS + ("content_hash", "handoff_updated_at_tpe")
        now = datetime.now(timezone(timedelta(hours=8))).isoformat()
        for i, (snapshot, result, error) in enumerate(pending):
            current_entry = by_key.get(snapshot["event_key"])
            if current_entry is None:
                continue
            current = current_entry[1]
            if any(current[k] != snapshot[k] for k in compare_fields):
                continue
            if not error and result == "UNCHANGED" and acknowledged(current):
                outcomes[i] = True
                continue
            number = row_numbers[snapshot["event_key"]]
            status = "ERROR" if error else "ACKED"
            ack_at = "" if error else now
            import_result = "" if error else result
            writes.append((i, [
                {"range": f"'{TAB}'!Z{number}", "values": [[status]]},
                {"range": f"'{TAB}'!AB{number}:AD{number}",
                 "values": [[ack_at, import_result, error]]},
            ]))
            expected[i] = (status, ack_at, import_result, error)

        # Send many independent cell ranges in bounded requests instead of
        # the previous 1 write + 2 full-Sheet reads for EACH record.
        for start in range(0, len(writes), RECEIPT_BATCH_ROWS):
            batch = writes[start:start + RECEIPT_BATCH_ROWS]
            await self.request("POST", "values:batchUpdate",
                               json={"valueInputOption": "RAW",
                                     "data": [r for _, ranges in batch for r in ranges]})

        if not writes:
            return outcomes
        # One readback verifies the exact version and receipt after the writes.
        verified = {r["event_key"]: r for r in parse_rows(await self.read())}
        for i, (snapshot, _, _) in enumerate(pending):
            if i not in expected:
                continue
            row = verified.get(snapshot["event_key"])
            status, ack_at, import_result, error = expected[i]
            outcomes[i] = bool(row and all(row[k] == snapshot[k] for k in compare_fields)
                               and row["handoff_status"] == status
                               and row["life_ack_at_tpe"] == ack_at
                               and row["life_import_result"] == import_result
                               and row["life_error"] == error)
        return outcomes

async def run_import(sheet=None, sessions=SessionLocal):
    if os.environ.get("LIFE_CURATED_SHEET_ID", "") != SHEET_ID:
        raise ValueError("fixed_handoff_sheet_required")
    sheet = sheet or SheetClient()
    rows = parse_rows(await sheet.read())
    applying = os.environ.get("LIFE_CURATED_IMPORT_APPLY") == "1"
    result = {"run_id": uuid.uuid4().hex, "mode": "apply" if applying else "dry_run",
              "created": 0, "updated": 0, "unchanged": 0, "invalid": 0, "import_failed": 0, "ack_failed": 0}
    pending_receipts = []
    for record in rows:
        # A bare Sheet receipt cannot prove which version is in PostgreSQL.
        # Recheck ACKED rows too; never skip a new version because of an old ACK.
        try:
            item = validate_record(record)
        except (ValueError, ValidationError) as exc:
            result["invalid"] += 1
            # Log only failed field paths/types, never source field values.
            fields = (",".join(".".join(map(str, e["loc"])) + ":" + e["type"]
                               for e in exc.errors()) if isinstance(exc, ValidationError)
                      else "content_hash")
            print(f"life_handoff_invalid event_key={record['event_key'][:100]} fields={fields}")
            if applying:
                pending_receipts.append((record, "INVALID", "invalid_handoff_record"))
            continue
        if not applying:
            continue
        try:
            async with sessions() as db:
                status = await upsert_handoff(db, item, record["content_hash"])
        except Exception:
            # A database/import failure is an infrastructure fault, not source data quality.
            result["import_failed"] += 1
            pending_receipts.append((record, "FAILED", "database_import_failed"))
            continue
        result[status.lower()] += 1
        pending_receipts.append((record, status, ""))
    if applying and pending_receipts:
        outcomes = await sheet.receipts(pending_receipts)
        if len(outcomes) != len(pending_receipts):
            raise RuntimeError("handoff_receipt_outcome_count_mismatch")
        result["ack_failed"] = sum(not success for success in outcomes)
    # Source-schema errors are row-level findings handled by the exploration batch.
    # Only failed DB operations or unverified receipts fail this technical Job.
    result["data_status"] = "PARTIAL" if result["invalid"] else "PASS"
    result["status"] = "FAIL" if result["import_failed"] or result["ack_failed"] else "PASS"
    return result


async def run_exclusive_import(connection, sheet=None, sessions=SessionLocal):
    locked = await connection.scalar(
        text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": IMPORT_LOCK_KEY})
    if locked is not True:
        # Never let a second GAS/manual run overwrite the first run's receipt.
        raise RuntimeError("handoff_concurrent_execution")
    return await run_import(sheet, sessions)


async def main():
    try:
        # A separate transaction keeps the lock until DB commits and Sheet ACK
        # readback finish; row-level DB connections remain independently short.
        async with engine.begin() as guard:
            result = await run_exclusive_import(guard)
            print("life_handoff_import " + " ".join(f"{k}={v}" for k, v in result.items()))
            if result["status"] != "PASS":
                raise RuntimeError("handoff_import_system_failure")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
