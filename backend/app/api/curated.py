"""Curated activities: bounded connector write, stable upsert and signed-in browse.

No crawling, Queue, secondary model, or claims about verified availability.
"""
import hashlib
import ipaddress
import os
import secrets
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.ui_policies import feature_gate
from app.db.session import get_db
from app.errors import current_request_id
from app.models.curated import CuratedActivity
from app.models.execution_log import ExecutionLog

router = APIRouter(prefix="/free-events", tags=["curated-activities"])
_TRACKING = {"fbclid", "gclid", "mc_cid", "mc_eid", "_ga"}


def normalize_url(raw: str) -> str:
    try:
        parsed = urlsplit(raw.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
        ipaddress.ip_address(host)  # Literal IP hosts are not valid external source URLs.
    except ValueError as exc:
        # ValueError from ipaddress means host is not an IP; the other
        # parse/port errors are rejected by the explicit checks below.
        if "port" in str(exc).lower() or "bracket" in str(exc).lower():
            raise ValueError("Invalid source URL") from exc
    if parsed.scheme != "https" or not host or "." not in host:
        raise ValueError("Only public HTTPS source URLs are allowed")
    if parsed.username or parsed.password or port not in (None, 443):
        raise ValueError("Credentials and nonstandard ports are not allowed")
    if host in {"localhost", "metadata.google.internal"} or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Private source host is not allowed")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP address sources are not allowed")
    if any(ch.isspace() for ch in raw) or len(raw) > 2048:
        raise ValueError("Invalid source URL")
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
               if k.lower() not in _TRACKING and not k.lower().startswith("utm_")),
        doseq=True,
    )
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(("https", host, path, query, ""))


class CuratedItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=2, max_length=400)
    original_url: str = Field(min_length=10, max_length=2048)
    occurrence_key: str = Field(default="main", pattern=r"^[A-Za-z0-9_-]{1,80}$")
    summary: str | None = Field(default=None, max_length=1200)
    city: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    starts_on: date | None = None
    ends_on: date | None = None
    fee_kind: Literal["free", "paid", "conditional_free", "unknown"] = "unknown"
    fee_amount: Decimal | None = Field(default=None, ge=0, le=10000000, decimal_places=2)
    benefit_value: Decimal | None = Field(default=None, ge=0, le=10000000, decimal_places=2)
    on_site_spending: bool = False
    importance: int = Field(default=1, ge=1, le=5)
    registration_required: bool | None = None
    registration_status: Literal["unknown", "upcoming", "open", "full", "closed"] = "unknown"
    limited_offer: bool = False
    registration_deadline: datetime | None = None

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return normalize_url(value)

    @model_validator(mode="after")
    def check_consistency(self):
        if self.ends_on and self.starts_on and self.ends_on < self.starts_on:
            raise ValueError("End date cannot precede start")
        if self.fee_kind == "free" and self.fee_amount not in (None, 0):
            raise ValueError("Free admission cannot carry a fee")
        if self.registration_deadline and self.registration_deadline.utcoffset() is None:
            raise ValueError("Registration deadline requires timezone")
        return self


class CuratedBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CuratedItemIn] = Field(min_length=1, max_length=40)


def require_curator(authorization: str | None = Header(default=None)) -> None:
    token = os.environ.get("LIFE_CURATED_INGEST_TOKEN", "")
    if not token or len(token) < 32:
        raise HTTPException(503, "Curated connector not configured")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not authorization or not authorization.startswith("Bearer ") or not secrets.compare_digest(token, supplied):
        raise HTTPException(401, "Invalid curator credentials")


def identity(item: CuratedItemIn) -> str:
    return hashlib.sha256(f"{item.original_url}\n{item.occurrence_key}".encode()).hexdigest()


@router.post("/curated:batch", dependencies=[Depends(require_curator)])
async def ingest_curated_batch(
    body: CuratedBatchIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    unique = {identity(item): item for item in body.items}
    for key, item in unique.items():
        row = {
            **item.model_dump(exclude={"original_url"}),
            "identity_key": key,
            "original_url": item.original_url,
            "updated_at": now,
        }
        statement = pg_insert(CuratedActivity).values(**row)
        # Never change canonical unique identity or the original creation time.
        statement = statement.on_conflict_do_update(
            index_elements=[CuratedActivity.identity_key],
            set_={k: v for k, v in row.items() if k != "identity_key"},
        )
        await db.execute(statement)
    db.add(ExecutionLog(
        id=str(uuid.uuid4()), request_id=current_request_id(),
        user_sub="connector:chatgpt-curator", action_type="curated.batch_upsert",
        entity_type="curated_activities", provider="chatgpt",
        status="success", result="upserted",
        summary=f"accepted={len(unique)}", finished_at=now,
    ))
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"accepted": len(unique), "duplicates_within_batch": len(body.items) - len(unique)}


@router.get("/curated", dependencies=[Depends(feature_gate("events"))])
async def list_curated(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=5000),
    city: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=100),
    starts_from: date | None = None,
    min_importance: int = Query(1, ge=1, le=5),
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    statement = select(CuratedActivity).where(CuratedActivity.importance >= min_importance)
    if city:
        statement = statement.where(CuratedActivity.city == city)
    if category:
        statement = statement.where(CuratedActivity.category == category)
    if starts_from:
        statement = statement.where(
            (CuratedActivity.starts_on.is_(None)) | (CuratedActivity.starts_on >= starts_from)
        )
    statement = statement.order_by(
        CuratedActivity.importance.desc(),
        CuratedActivity.starts_on.asc().nulls_last(),
        CuratedActivity.updated_at.desc(),
    ).offset(offset).limit(limit)
    rows = (await db.execute(statement)).scalars().all()
    response.headers["Cache-Control"] = "no-store"
    return {"items": [
        {
            **{field: getattr(row, field) for field in (
                "identity_key", "title", "original_url", "occurrence_key",
                "summary", "city", "category", "starts_on", "ends_on", "fee_kind",
                "fee_amount", "benefit_value", "on_site_spending", "importance",
                "registration_required", "registration_status", "limited_offer",
                "registration_deadline", "updated_at",
            )}
        }
        for row in rows
    ], "returned": len(rows), "policy": "chatgpt_curated_unverified"}


@router.get("/curated/status")
async def curated_owner_status(
    response: Response,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    owner = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().lower()
    if not owner or str(user.get("email", "")).strip().lower() != owner:
        raise HTTPException(403, "Owner access required")
    count = await db.scalar(select(func.count()).select_from(CuratedActivity))
    newest = await db.scalar(select(func.max(CuratedActivity.updated_at)))
    response.headers["Cache-Control"] = "no-store"
    return {"items": count or 0, "last_updated_at": newest}
