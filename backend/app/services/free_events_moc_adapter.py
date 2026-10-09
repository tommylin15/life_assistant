"""Offline adapter for licensed MoC '藝文活動-所有類別' public JSON.

Use only with a locally supplied, lawfully acquired official JSON export.
No network access, no price inference from onSales and no user-calendar writes.
Official dataset keys: UID, title/titile, showinfo, time, endTime,
locationName, onSales, price, sourceWebPromote and webSales.
"""
from __future__ import annotations

from datetime import date, datetime
from hashlib import sha256
import json
import re
from typing import Any
from zoneinfo import ZoneInfo

from app.services.free_events_normalization import (
    CandidateOpportunity, CandidateSession, EventCandidate, safe_provenance_url,
)

DATASET_URL = "https://data.gov.tw/dataset/6478"
SOURCE_ID = "moc_events_all"
TAIPEI = ZoneInfo("Asia/Taipei")
DATE_ONLY = re.compile(r"^\d{4}[/-]\d{1,2}[/-]\d{1,2}$")


def _source_str(value: Any, maximum: int) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()[:maximum]
    return None


def _safe_optional_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return safe_provenance_url(value)
    except ValueError:
        # Never upgrade HTTP automatically or transform an unknown site link.
        return None


def _moc_time(value: Any) -> tuple[datetime | None, date | None]:
    """Convert explicit source-local clock time; do not guess date-only hours."""
    if not isinstance(value, str) or not value.strip():
        return None, None
    raw = value.strip()
    normalized = raw.replace("/", "-")
    if DATE_ONLY.fullmatch(raw):
        return None, date.fromisoformat(normalized)
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("unrecognized official time") from exc
    if parsed.tzinfo is None:
        # MoC dataset convention: performances in Taiwan use Asia/Taipei.
        parsed = parsed.replace(tzinfo=TAIPEI)
    return parsed, None


def normalize_moc_record(item: dict[str, Any]) -> EventCandidate:
    """Deterministically map one MoC record, preserving unknown fees/window."""
    uid = item.get("UID")
    if not isinstance(uid, (str, int)) or not str(uid).strip():
        raise ValueError("missing MoC UID")
    title = _source_str(item.get("title") or item.get("titile"), 500)
    if not title:
        raise ValueError("missing MoC event title")
    advertised_url = _safe_optional_url(item.get("sourceWebPromote"))
    sale_url = _safe_optional_url(item.get("webSales"))
    organizer_value = item.get("masterUnit")
    if isinstance(organizer_value, list):
        organizer = next(
            (name.strip() for name in organizer_value if isinstance(name, str) and name.strip()),
            None,
        )
    else:
        organizer = _source_str(organizer_value, 500)
    # Organizer claims from a dataset are not sufficient to assert official
    # registration verification. A direct organizer/registration page review
    # is required in later ingestion and publication gates.
    showinfo = item.get("showinfo") or []
    if not isinstance(showinfo, list):
        raise ValueError("invalid showinfo array")
    sessions = []
    seen = set()
    for raw in showinfo:
        if not isinstance(raw, dict):
            raise ValueError("invalid showinfo item")
        start_time, start_day = _moc_time(raw.get("time"))
        end_time, end_day = _moc_time(raw.get("endTime"))
        if start_day is not None:
            # The source's endDate/on-page endTime inclusivity has not been
            # verified; do not convert into an invented exclusive end.
            end_day = None
        else:
            end_day = None
        if start_time is None:
            end_time = None
        venue = _source_str(raw.get("locationName"), 300)
        identity_parts = {
            "time": raw.get("time"), "endTime": raw.get("endTime"),
            "locationName": raw.get("locationName"),
        }
        session_key = sha256(
            json.dumps(identity_parts, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:32]
        if session_key in seen:
            continue
        seen.add(session_key)
        opportunities = [CandidateOpportunity(
            opportunity_key="general",
            registration_url=sale_url,
            # Neither onSales=false nor an unstructured price string can
            # prove genuine free entry / eligibility / registration opening.
            fee_kind="unknown",
            registration_status="unannounced",
            official_verified=False,
        )]
        sessions.append(CandidateSession(
            session_key=session_key,
            starts_at=start_time,
            ends_at=end_time,
            starts_on=start_day,
            ends_on_exclusive=end_day,
            timezone_name="Asia/Taipei" if start_time is not None else None,
            venue=venue,
            opportunities=opportunities,
        ))
    category = item.get("category")
    if isinstance(category, list):
        category = str(category[0]) if category else None
    if not isinstance(category, str):
        category = None
    return EventCandidate(
        source_id=SOURCE_ID,
        external_event_key=str(uid).strip()[:255],
        title=title,
        category=category[:80] if category else None,
        source_url=advertised_url or DATASET_URL,
        official_url=None,
        organizer_name=organizer[:500] if organizer else None,
        official_verified=False,
        sessions=sessions,
    )
