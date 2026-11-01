"""Versioned Drive handoff validation and ACK writeback for Taipei/New Taipei food discounts."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, text

from app.api.curated import normalize_url
from app.errors import current_request_id
from app.models.execution_log import ExecutionLog
from app.models.food_discount import FoodDiscount

TAIPEI = timezone(timedelta(hours=8))

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


class FoodHandoffItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    candidate_key: str = Field(min_length=2, max_length=200, pattern=r"^[A-Za-z0-9_:./-]+$")
    city: str | None = Field(default=None, max_length=50)
    district: str | None = Field(default=None, max_length=100)
    merchant: str = Field(min_length=1, max_length=300)
    category: str | None = Field(default=None, max_length=100)
    offer_summary: str = Field(min_length=2, max_length=1000)
    offer_type: str | None = Field(default=None, max_length=100)
    nominal_discount: str | None = Field(default=None, max_length=120)
    fixed_discount_ntd: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)
    original_price_ntd: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)
    offer_price_ntd: Decimal | None = Field(default=None, ge=0, le=1000000, decimal_places=2)
    period_text: str | None = Field(default=None, max_length=400)
    address: str | None = Field(default=None, max_length=600)
    source_url: str = Field(min_length=10, max_length=2048)
    notes: str | None = Field(default=None, max_length=1200)
    claim_status: str = Field(default="COLLECTED_SOURCE_CLAIM", max_length=64)
    visibility_status: str = Field(default="VISIBLE_SOURCE_ONLY", max_length=64)
    first_seen_on: date | None = None
    claim_deadline_on: date | None = None
    redemption_ends_on: date | None = None
    offer_ends_on: date | None = None
    last_positive_on: date | None = None
    next_refresh_on: date | None = None
    date_basis: str | None = Field(default=None, max_length=64)
    disclosure: str = Field(
        default="公開來源宣稱，未逐項核實，不保證到店可使用", max_length=300
    )
    handoff_updated_at_tpe: datetime

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return normalize_url(value)

    @model_validator(mode="after")
    def verify_taipei_offset(self):
        offset = self.handoff_updated_at_tpe.utcoffset()
        if offset is None or offset.total_seconds() != 28800:
            raise ValueError("handoff_time_requires_taipei_offset")
        return self


def parse_food_handoff_rows(values: list[list[str]]) -> list[dict]:
    if not values or tuple(values[0]) != HEADERS:
        raise ValueError("food_handoff_header_contract_mismatch")
    rows: list[dict] = []
    seen: set[str] = set()
    for row in values[1:]:
        record = {
            key: str(row[i] if i < len(row) and row[i] is not None else "").strip()
            for i, key in enumerate(HEADERS)
        }
        if not any(record.values()):
            continue
        ck = record["candidate_key"]
        if not ck or ck in seen:
            raise ValueError("missing_or_duplicate_candidate_key")
        seen.add(ck)
        if record["handoff_status"] not in ("READY", "ERROR", "ACKED"):
            raise ValueError("invalid_handoff_status")
        rows.append(record)
    return rows


def validate_food_handoff_record(record: dict) -> FoodHandoffItem:
    if not re.fullmatch(r"[a-f0-9]{64}", record.get("content_hash", "")):
        raise ValueError("invalid_content_hash")
    payload = {
        key: (record.get(key) or None)
        for key in BUSINESS_FIELDS + ("handoff_updated_at_tpe",)
    }
    if not payload.get("claim_status"):
        payload["claim_status"] = "COLLECTED_SOURCE_CLAIM"
    if not payload.get("visibility_status"):
        payload["visibility_status"] = "VISIBLE_SOURCE_ONLY"
    if not payload.get("disclosure"):
        payload["disclosure"] = "公開來源宣稱，未逐項核實，不保證到店可使用"
    return FoodHandoffItem.model_validate(payload)


def food_record_acknowledged(record: dict) -> bool:
    return (
        record.get("handoff_status") == "ACKED"
        and bool(record.get("life_ack_at_tpe"))
        and record.get("life_import_result") in ("CREATED", "UPDATED", "UNCHANGED")
    )


async def upsert_food_handoff(db, item: FoodHandoffItem, version: str) -> str:
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "postgresql":
        lock = int.from_bytes(
            hashlib.sha256(f"food_discount:{item.candidate_key}".encode()).digest()[:8],
            "big",
            signed=True,
        )
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})

    row = await db.scalar(
        select(FoodDiscount).where(FoodDiscount.candidate_key == item.candidate_key)
    )
    result = "CREATED" if row is None else "UNCHANGED" if row.content_hash == version else "UPDATED"

    if row is not None and row.details:
        previous_version = row.details.get("handoff_updated_at_tpe")
        if previous_version:
            previous = datetime.fromisoformat(previous_version)
            if previous > item.handoff_updated_at_tpe or (
                previous == item.handoff_updated_at_tpe and row.content_hash != version
            ):
                raise ValueError("superseded_or_conflicting_handoff_version")

    if result == "UNCHANGED":
        row.details = {
            **(row.details or {}),
            "handoff_updated_at_tpe": item.handoff_updated_at_tpe.isoformat(),
        }
        await db.commit()
        return result

    if row is None:
        row = FoodDiscount(candidate_key=item.candidate_key)
        db.add(row)

    dumped = item.model_dump(exclude={"handoff_updated_at_tpe"})
    for key, value in dumped.items():
        setattr(row, key, value)
    row.content_hash = version
    row.details = {
        **(row.details or {}),
        "handoff_updated_at_tpe": item.handoff_updated_at_tpe.isoformat(),
    }
    row.updated_at = datetime.now(timezone.utc)

    db.add(
        ExecutionLog(
            id=str(uuid.uuid4()),
            request_id=current_request_id(),
            user_sub="job:food-discounts-handoff",
            action_type="food_discounts.handoff",
            provider="google_sheets",
            status="success",
            result=result.lower(),
            entity_type="food_discounts",
            entity_id=item.candidate_key,
            summary=item.merchant[:200],
            finished_at=row.updated_at,
        )
    )
    await db.commit()
    return result
