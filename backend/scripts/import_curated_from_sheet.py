"""Deterministic import of ChatGPT-selected native Google Sheet rows into Life.

Cloud Scheduler -> Cloud Run Job -> Google Sheets read-only -> existing Pydantic /
PostgreSQL upsert. No AI calls, web crawler, direct MCP, or user browser cookies.
Run with no write unless LIFE_CURATED_IMPORT_APPLY=1.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from fastapi import Response
from pydantic import ValidationError
from sqlalchemy import select

from app.api.curated import CuratedBatchIn, CuratedItemIn, identity, ingest_curated_batch
from app.db.session import SessionLocal, engine
from app.models.curated import CuratedActivity

GOOGLE_SHEETS_ENDPOINT = "https://sheets.googleapis.com/v4/spreadsheets"
TAB = "精選活動"
MAX_SHEET_ROWS = 1000
ALLOWED_STATES = frozenset(("selected", "changed"))
FIELDS = (
    "event_key", "活動名稱", "主辦官方活動網址", "報名網址",
    "pool狀態", "重要性星等",
)


def _text(row: list, indexes: dict[str, int], name: str) -> str:
    idx = indexes.get(name)
    return str(row[idx]).strip() if idx is not None and idx < len(row) and row[idx] is not None else ""


def _date(raw: str) -> date | None:
    if not raw:
        return None
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?:\s+\d{2}:\d{2}(?::\d{2})?)?", raw)
    if not match:
        # Commentary like "registration opens 10/14, event TBC" is not
        # a verified activity date. Preserve the activity without a date.
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _amount(raw: str) -> Decimal | None:
    if not raw:
        return None
    value = raw.replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        raise ValueError("unverified_amount")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid_amount") from exc
    if amount > 10000000:
        raise ValueError("amount_exceeds_limit")
    return amount


def parse_rows(values: list[list]) -> tuple[list[CuratedItemIn], list[int], int]:
    """Reject bad approved rows individually; fail duplicate IDs before any DB writes.

    Row numbers, not personal Google Drive content, are suitable for job logs.
    """
    if not values:
        raise ValueError("empty_curated_sheet")
    headers = [str(v).strip() for v in values[0]]
    if len(headers) != len(set(headers)):
        raise ValueError("duplicate_headers")
    indexes = {name: index for index, name in enumerate(headers)}
    if not set(FIELDS).issubset(indexes):
        raise ValueError("missing_required_curated_headers")
    if len(values) > MAX_SHEET_ROWS:
        raise ValueError("curated_sheet_rows_exceed_limit")

    by_event_key: dict[str, CuratedItemIn] = {}
    invalid_rows: list[int] = []
    filtered = 0
    for row_number, row in enumerate(values[1:], start=2):
        state = _text(row, indexes, "pool狀態").lower()
        if state not in ALLOWED_STATES:
            filtered += 1
            continue
        key = _text(row, indexes, "event_key")
        title = _text(row, indexes, "活動名稱")
        official_url = _text(row, indexes, "主辦官方活動網址")
        signup_url = _text(row, indexes, "報名網址")
        if not key or not title or not (official_url or signup_url):
            invalid_rows.append(row_number)
            continue
        if key in by_event_key:
            raise ValueError("duplicate_approved_event_key")
        try:
            start = _date(_text(row, indexes, "開始時間(台北)"))
            end = _date(_text(row, indexes, "結束時間(台北)"))
            fee = _amount(_text(row, indexes, "不可退實付C(NTD)"))
            benefit = _amount(_text(row, indexes, "可驗證福利V(NTD)"))
            stars = int(_text(row, indexes, "重要性星等"))
            fee_evidence = _text(row, indexes, "主會場入場費狀態")
            registration_text = _text(row, indexes, "報名需求")
            status_text = _text(row, indexes, "報名狀態")
            payload = {
                "title": title,
                "original_url": official_url or signup_url,
                # Keep distinct sub-events with the same URL while preserving
                # a stable identity on retries. URL changes require review.
                "occurrence_key": "sheet_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24],
                "importance": stars,
            }
            optional = (
                ("summary", _text(row, indexes, "精選理由")),
                ("city", _text(row, indexes, "縣市")),
                ("category", _text(row, indexes, "分類")),
            )
            for target, raw in optional:
                if raw:
                    payload[target] = raw
            if start:
                payload["starts_on"] = start
            if end:
                payload["ends_on"] = end
            if fee is not None:
                payload["fee_amount"] = fee
                payload["fee_kind"] = ("free" if fee == 0 and "免費" in fee_evidence else
                                       "paid" if fee > 0 else "unknown")
            if benefit is not None:
                payload["benefit_value"] = benefit
            if "免報名" in registration_text or "不需報名" in registration_text:
                payload["registration_required"] = False
            elif "需報名" in registration_text or "要報名" in registration_text:
                payload["registration_required"] = True
            if "已額滿" in status_text:
                payload["registration_status"] = "full"
            elif "已截止" in status_text or "報名截止" in status_text:
                payload["registration_status"] = "closed"
            elif "尚未開放" in status_text or "即將開放" in status_text:
                payload["registration_status"] = "upcoming"
            elif "開放報名" in status_text:
                payload["registration_status"] = "open"
            if _text(row, indexes, "限量優惠狀態") in ("已確認限量", "confirmed_limited"):
                payload["limited_offer"] = True
            by_event_key[key] = CuratedItemIn.model_validate(payload)
        except (ValueError, ValidationError):
            invalid_rows.append(row_number)

    result = list(by_event_key.values())
    if len({identity(item) for item in result}) != len(result):
        raise ValueError("distinct_sheet_keys_collide_on_curated_identity")
    return result, invalid_rows, filtered


def _get_google_access_token() -> str:
    """Use job's attached service account ADC; no new API keys."""
    import google.auth
    from google.auth.transport.requests import Request
    credentials, _project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    credentials.refresh(Request())
    return credentials.token


async def read_sheet_values(file_id: str) -> list[list]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{15,120}", file_id):
        raise ValueError("invalid_sheet_id")
    token = await asyncio.to_thread(_get_google_access_token)
    url = f"{GOOGLE_SHEETS_ENDPOINT}/{file_id}/values/%27%E7%B2%BE%E9%81%B8%E6%B4%BB%E5%8B%95%27!A1:AS1001"
    async with httpx.AsyncClient(timeout=25.0) as client:
        res = await client.get(url, headers={"Authorization": f"Bearer {token}"},
                               params={"valueRenderOption": "FORMATTED_VALUE"})
    if res.status_code != 200:
        # Avoid logging the provider's response text or OAuth credentials.
        raise RuntimeError(f"google_sheets_read_failed_http_{res.status_code}")
    values = res.json().get("values")
    if not isinstance(values, list):
        raise ValueError("invalid_sheets_values")
    return values


async def run_import() -> dict[str, int | str]:
    file_id = os.environ.get("LIFE_CURATED_SHEET_ID", "").strip()
    values = await read_sheet_values(file_id)
    items, invalid_rows, filtered = parse_rows(values)
    applying = os.environ.get("LIFE_CURATED_IMPORT_APPLY") == "1"
    result: dict[str, int | str] = {
        "mode": "apply" if applying else "dry_run",
        "selected": len(items), "filtered": filtered,
        "invalid": len(invalid_rows), "unchanged": 0, "upserted": 0,
    }
    if not applying or not items:
        return result

    # Compare only supplied fields: a replay must not rewrite updated_at or
    # generate misleading execution logs when the sheet has not changed.
    async with SessionLocal() as db:
        stored = (await db.execute(select(CuratedActivity).where(
            CuratedActivity.identity_key.in_([identity(item) for item in items])
        ))).scalars().all()
        existing = {entry.identity_key: entry for entry in stored}
        pending = []
        for item in items:
            old = existing.get(identity(item))
            expected = item.model_dump(exclude_unset=True, exclude={"original_url"})
            if old and old.original_url == item.original_url and all(
                getattr(old, name) == value for name, value in expected.items()
            ):
                result["unchanged"] += 1
            else:
                pending.append(item)

    for pos in range(0, len(pending), 40):
        batch = CuratedBatchIn(items=pending[pos:pos + 40])
        async with SessionLocal() as db:
            await ingest_curated_batch(batch, Response(), db=db)
        result["upserted"] += len(batch.items)
    return result


async def main() -> None:
    try:
        results = await run_import()
        print("life_sheet_curated_import " + " ".join(
            f"{name}={value}" for name, value in results.items()
        ))
        if results["invalid"]:
            raise RuntimeError("curated_sheet_has_invalid_selected_rows")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
