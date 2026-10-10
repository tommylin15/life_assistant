"""Versioned Drive handoff validation and transactional, URL-independent identity."""
import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, text

from app.api.curated import CuratedItemIn, identity, normalize_url
from app.models.curated import CuratedActivity
from app.models.execution_log import ExecutionLog
from app.errors import current_request_id

BUSINESS_FIELDS = (
    "event_key", "parent_event_key", "record_type", "title", "city", "district",
    "category", "organizer", "start_at_tpe", "end_at_tpe", "venue", "official_url",
    "registration_url", "source_url", "importance_star", "opportunity_type",
    "registration_open_at_tpe", "registration_deadline_at_tpe", "nonrefundable_cost_ntd",
    "refundable_deposit_ntd", "verified_benefit_ntd", "eligibility_limit",
    "evidence_summary", "verified_at_tpe",
)
HEADERS = ("event_key", "content_hash", *BUSINESS_FIELDS[1:], "handoff_status",
           "handoff_updated_at_tpe", "life_ack_at_tpe", "life_import_result", "life_error")


def content_hash(fields: dict) -> str:
    # v1 canonical form is a sorted JSON object of all business cells as trimmed
    # strings. Empty cells are ""; receipt columns never change the version.
    canonical = {key: "" if fields.get(key) is None else str(fields[key]).strip() for key in BUSINESS_FIELDS}
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


class HandoffItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    event_key: str = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_:./-]+$")
    parent_event_key: str | None = Field(None, max_length=200, pattern=r"^[A-Za-z0-9_:./-]+$")
    record_type: Literal["main", "offer", "session"]
    title: str = Field(min_length=2, max_length=400)
    city: str | None = Field(None, max_length=100)
    district: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    organizer: str | None = Field(None, max_length=400)
    start_at_tpe: date | datetime | None = None
    end_at_tpe: date | datetime | None = None
    venue: str | None = Field(None, max_length=1000)
    official_url: str | None = Field(None, max_length=2048)
    registration_url: str | None = Field(None, max_length=2048)
    source_url: str | None = Field(None, max_length=2048)
    importance_star: int = Field(ge=1, le=5)
    opportunity_type: str | None = Field(None, max_length=100)
    registration_open_at_tpe: datetime | None = None
    registration_deadline_at_tpe: datetime | None = None
    nonrefundable_cost_ntd: Decimal | None = Field(None, ge=0, le=10000000, decimal_places=2)
    refundable_deposit_ntd: Decimal | None = Field(None, ge=0, le=10000000, decimal_places=2)
    verified_benefit_ntd: Decimal | None = Field(None, ge=0, le=10000000, decimal_places=2)
    eligibility_limit: str | None = Field(None, max_length=1200)
    evidence_summary: str | None = Field(None, max_length=1200)
    verified_at_tpe: datetime
    handoff_updated_at_tpe: datetime

    @field_validator("start_at_tpe", "end_at_tpe", mode="before")
    @classmethod
    def preserve_precision(cls, value):
        if isinstance(value, str):
            return datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
        return value

    @field_validator("official_url", "registration_url", "source_url")
    @classmethod
    def safe_url(cls, value):
        return normalize_url(value) if value else None

    @model_validator(mode="after")
    def consistent(self):
        if not (self.official_url or self.registration_url):
            raise ValueError("official_or_registration_url_required")
        for key in ("start_at_tpe", "end_at_tpe", "registration_open_at_tpe",
                    "registration_deadline_at_tpe", "verified_at_tpe", "handoff_updated_at_tpe"):
            value = getattr(self, key)
            if isinstance(value, datetime) and (value.utcoffset() is None or value.utcoffset().total_seconds() != 28800):
                raise ValueError("handoff_time_requires_taipei_offset")
        if self.start_at_tpe and self.end_at_tpe:
            start = self.start_at_tpe.date() if isinstance(self.start_at_tpe, datetime) else self.start_at_tpe
            end = self.end_at_tpe.date() if isinstance(self.end_at_tpe, datetime) else self.end_at_tpe
            if end < start or (isinstance(self.start_at_tpe, datetime) and isinstance(self.end_at_tpe, datetime) and self.end_at_tpe < self.start_at_tpe):
                raise ValueError("activity_end_before_start")
        if self.registration_open_at_tpe and self.registration_deadline_at_tpe and self.registration_deadline_at_tpe < self.registration_open_at_tpe:
            raise ValueError("registration_deadline_before_open")
        if self.parent_event_key == self.event_key:
            raise ValueError("self_parent_not_allowed")
        if self.record_type != "main" and not self.parent_event_key:
            raise ValueError("child_requires_parent")
        return self

    def curated(self) -> CuratedItemIn:
        def day(value):
            return value.date() if isinstance(value, datetime) else value
        return CuratedItemIn(
            title=self.title, original_url=self.official_url or self.registration_url,
            occurrence_key="sheet_" + hashlib.sha256(self.event_key.encode()).hexdigest()[:24],
            summary=self.evidence_summary, city=self.city, category=self.category,
            starts_on=day(self.start_at_tpe), ends_on=day(self.end_at_tpe),
            fee_kind="free" if self.nonrefundable_cost_ntd == 0 and not self.eligibility_limit else
                     "conditional_free" if self.nonrefundable_cost_ntd == 0 else
                     "paid" if self.nonrefundable_cost_ntd is not None else "unknown",
            fee_amount=self.nonrefundable_cost_ntd, benefit_value=self.verified_benefit_ntd,
            importance=self.importance_star, registration_deadline=self.registration_deadline_at_tpe,
            registration_required=True if self.registration_url else None,
            limited_offer=bool(self.opportunity_type),
        )


async def upsert_handoff(db, item: HandoffItem, version: str) -> str:
    # Lock one stable key across all Job processes. Unique DB key is a second guard.
    lock = int.from_bytes(hashlib.sha256(item.event_key.encode()).digest()[:8], "big", signed=True)
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
    row = await db.scalar(select(CuratedActivity).where(CuratedActivity.handoff_event_key == item.event_key))
    incoming = item.curated()
    if row is None:
        # Adopt an existing earlier Sheet importer row only on exact URL+key
        # identity; never guess from titles or merge distinct sessions.
        row = await db.get(CuratedActivity, identity(incoming))
        if row is not None and row.handoff_event_key not in (None, item.event_key):
            raise ValueError("legacy_identity_conflict")
    result = "CREATED" if row is None else "UNCHANGED" if row.content_hash == version else "UPDATED"
    if row is not None and row.handoff_details:
        previous_version = row.handoff_details.get("handoff_updated_at_tpe")
        if previous_version:
            previous = datetime.fromisoformat(previous_version)
            if previous > item.handoff_updated_at_tpe or (previous == item.handoff_updated_at_tpe and row.content_hash != version):
                raise ValueError("superseded_or_conflicting_handoff_version")
    if result == "UNCHANGED":
        row.handoff_details = {**row.handoff_details, "handoff_updated_at_tpe": item.handoff_updated_at_tpe.isoformat()}
        await db.commit()
        return result
    if row is None:
        row = CuratedActivity(identity_key=hashlib.sha256(("chatgpt_drive_handoff\n" + item.event_key).encode()).hexdigest())
        db.add(row)
    for key, value in incoming.model_dump().items():
        setattr(row, key, value)
    row.handoff_event_key = item.event_key
    row.parent_event_key = item.parent_event_key
    row.content_hash = version
    row.handoff_details = item.model_dump(mode="json")
    row.updated_at = datetime.now(timezone.utc)
    db.add(ExecutionLog(id=str(uuid.uuid4()), request_id=current_request_id(), user_sub="job:curated-handoff",
        action_type="curated.handoff", provider="google_sheets", status="success",
        result=result, summary="Validated handoff committed", entity_type="curated_activities",
        entity_id=row.identity_key, finished_at=row.updated_at))
    await db.commit()
    return result
