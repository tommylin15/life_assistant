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
from sqlalchemy import case, func, select, or_
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
        # Omitted optional fields must not erase prior evidence on retry.
        changed_fields = item.model_fields_set | {"updated_at"}
        statement = statement.on_conflict_do_update(
            index_elements=[CuratedActivity.identity_key],
            set_={k: v for k, v in row.items() if k in changed_fields and k != "identity_key"},
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



# V3 browse is a PostgreSQL GROUP query. Each page contains main event groups,
# never a partial page of child offers; no Flutter-side DB-wide filtering.
from zoneinfo import ZoneInfo
from datetime import timedelta
import re
from sqlalchemy import and_, cast, Date, desc, literal
from app.models.curated_actions import CuratedPersonalAction

TAIPEI = ZoneInfo("Asia/Taipei")
REGIONS = {
    "north": ("臺北市", "台北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"),
    "central": ("苗栗縣", "臺中市", "台中市", "彰化縣", "南投縣", "雲林縣"),
    "south": ("嘉義市", "嘉義縣", "臺南市", "台南市", "高雄市", "屏東縣"),
    "east": ("花蓮縣", "臺東縣", "台東縣"),
    "islands": ("澎湖縣", "金門縣", "連江縣"),
}

def _group_key(model=CuratedActivity):
    parent = func.coalesce(model.parent_event_key, model.handoff_event_key)
    return case(
        (parent.is_not(None), func.concat("handoff:", parent)),
        else_=func.concat("legacy:", model.identity_key),
    )

def _registration_open_date():
    raw = CuratedActivity.handoff_details["registration_open_at_tpe"].as_string()
    # Avoid cast errors when optional upstream time is missing or malformed.
    return cast(case(
        (raw.op("~")(r"^\d{4}-\d{2}-\d{2}"), func.left(raw, 10)),
        else_=None,
    ), Date)

def _taipei_deadline_date():
    return cast(func.timezone("Asia/Taipei", CuratedActivity.registration_deadline), Date)

def _active_activity_predicate(today: date, entry: str):
    """Hide expired events from all views, including saved and grouped offers.

    A missing end date does not prove an older event continues today. Fully
    undated entries stay visible until verified. No row is deleted.
    """
    start, end = CuratedActivity.starts_on, CuratedActivity.ends_on
    current_date = or_(
        end >= today,
        and_(end.is_(None), or_(start.is_(None), start >= today)),
    )
    current_status = CuratedActivity.registration_status.notin_(
        ["cancelled", "canceled"]
    )
    if entry == "opportunities":
        deadline = _taipei_deadline_date()
        return and_(current_date, current_status,
                    CuratedActivity.registration_status.notin_(["closed", "full"]),
                    or_(deadline.is_(None), deadline >= today))
    return and_(current_date, current_status)


def _activity_filters(statement, *, entry, quick, keyword, region, city, district,
                      category, fee_kind, starts_from, today, saved_only, user_sub):
    start = CuratedActivity.starts_on
    end = CuratedActivity.ends_on
    opening = _registration_open_date()
    deadline = _taipei_deadline_date()
    if entry == "opportunities":
        statement = statement.where(or_(CuratedActivity.registration_required.is_(True),
                                         CuratedActivity.limited_offer.is_(True)))
    # A bookmark does not reintroduce expired or cancelled content.
    statement = statement.where(_active_activity_predicate(today, entry))
    if keyword:
        normalized = re.sub(r"\s+", " ", keyword).strip()
        if normalized:
            pattern = "%" + normalized.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
            fields = [
                CuratedActivity.title, CuratedActivity.city, CuratedActivity.summary,
                CuratedActivity.handoff_details["organizer"].as_string(),
                CuratedActivity.handoff_details["venue"].as_string(),
                CuratedActivity.handoff_details["district"].as_string(),
                CuratedActivity.handoff_details["evidence_summary"].as_string(),
            ]
            statement = statement.where(or_(*(f.ilike(pattern, escape="\\") for f in fields)))
    if city:
        statement = statement.where(CuratedActivity.city == city)
    if region:
        statement = statement.where(CuratedActivity.city.in_(REGIONS[region]))
    if district:
        statement = statement.where(CuratedActivity.handoff_details["district"].as_string() == district)
    if category:
        statement = statement.where(CuratedActivity.category == category)
    if fee_kind:
        statement = statement.where(CuratedActivity.fee_kind == fee_kind)
    if starts_from:
        statement = statement.where(or_(end >= starts_from, and_(end.is_(None), start >= starts_from)))
    if quick == "latest" or not quick:
        return statement
    if quick in ("opening_soon", "opening_today", "closing_soon", "limited", "unknown_time"):
        if quick == "opening_soon":
            statement = statement.where(opening.between(today, today + timedelta(days=7)))
        elif quick == "opening_today":
            statement = statement.where(opening == today)
        elif quick == "closing_soon":
            statement = statement.where(deadline.between(today, today + timedelta(days=3)))
        elif quick == "limited":
            statement = statement.where(CuratedActivity.limited_offer.is_(True))
        elif quick == "unknown_time":
            statement = statement.where(opening.is_(None), deadline.is_(None))
    else:
        if quick == "ongoing":
            statement = statement.where(start <= today,
                or_(end >= today, and_(end.is_(None), start == today)))
        elif quick == "weekend":
            saturday = today + timedelta(days=(5 - today.weekday()) % 7)
            sunday = saturday + timedelta(days=1)
            statement = statement.where(start <= sunday,
                or_(end >= saturday, and_(end.is_(None), start >= saturday)))
        elif quick in ("next_7", "next_30"):
            # A multi-day event that began earlier but overlaps the requested
            # window must remain discoverable. Unknown end dates alone are not
            # evidence that a past event continues through today.
            horizon = today + timedelta(days=7 if quick == "next_7" else 30)
            statement = statement.where(or_(
                start.between(today, horizon),
                and_(start < today, end >= today),
            ))
        elif quick == "free":
            statement = statement.where(CuratedActivity.fee_kind == "free")
    return statement

@router.get("/curated")
async def list_curated(
    response: Response,
    limit: int = Query(5, ge=1, le=50),
    offset: int = Query(0, ge=0, le=50000),
    city: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=100),
    starts_from: date | None = None,
    min_importance: int = Query(1, ge=1, le=5),  # legacy connector compatibility only
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    entry: Literal["all", "opportunities", "explore"] = "all",
    keyword: str | None = Query(None, max_length=120),
    quick: str | None = Query(None, max_length=24),
    region: Literal["north", "central", "south", "east", "islands"] | None = None,
    district: str | None = Query(None, max_length=100),
    fee_kind: Literal["free", "paid", "conditional_free", "unknown"] | None = None,
    saved_only: bool = False,
    verification_status: Literal["unknown", "pending_review", "verified"] | None = None,
    as_of: datetime | None = Query(None, description="UTC snapshot from first page"),
):
    if _user and isinstance(db, AsyncSession):
        if entry == "explore":
            # Unified activity listing inherits either legacy activity entitlement.
            from app.api.ui_policies import effective_features
            features = await effective_features(db, _user)
            if not any(x["available"] for x in features
                       if x["key"] in ("explore", "opportunities")):
                raise HTTPException(403, "Activity features unavailable")
        else:
            await feature_gate("events" if entry == "all" else entry)(user=_user, db=db)
    # Direct callers in connector/integration tests bypass FastAPI's Query coercion.
    # Normalize omitted Query descriptors without changing HTTP validation.
    if not isinstance(quick, (str, type(None))): quick = None
    if not isinstance(keyword, (str, type(None))): keyword = None
    if not isinstance(district, (str, type(None))): district = None
    if not isinstance(as_of, (datetime, type(None))): as_of = None
    if verification_status not in (None, "unknown", "pending_review", "verified"):
        verification_status = None
    if as_of is not None and (as_of.tzinfo is None or as_of.utcoffset() is None):
        raise HTTPException(422, "as_of must include timezone")
    # An immutable page anchor prevents new imports from moving offset pages.
    # Existing records changed after this time can still move; clients also
    # reset all accumulated pages after personal actions or manual refresh.
    snapshot = as_of or datetime.now(timezone.utc)
    today = datetime.now(TAIPEI).date()
    if quick and quick not in (
        {"latest", "opening_soon", "opening_today", "closing_soon", "limited", "unknown_time"}
        if entry == "opportunities"
        else {"latest", "ongoing", "weekend", "next_7", "next_30", "free",
              "opening_soon", "opening_today", "closing_soon", "limited", "unknown_time"}
    ):
        raise HTTPException(422, "Unsupported quick filter")
    group = _group_key()
    statement = _activity_filters(
        select(CuratedActivity), entry=entry, quick=quick,
        keyword=keyword, region=region, city=city, district=district,
        category=category, fee_kind=fee_kind, starts_from=starts_from,
        today=today, saved_only=saved_only, user_sub=_user.get("sub"),
    )
    if verification_status:
        # JSON metadata is additive: no table migration or v1 30-column break.
        stored_verification = func.coalesce(
            CuratedActivity.handoff_details["verification_status"].as_string(),
            literal("unknown"),
        )
        statement = statement.where(stored_verification == verification_status)
    statement = statement.where(CuratedActivity.created_at <= snapshot)
    # Legacy child saves and newer main saves both make the whole group saved.
    saves = (select(group.label("g"))
             .select_from(CuratedActivity)
             .join(CuratedPersonalAction, and_(
                 CuratedPersonalAction.kind == "save",
                 CuratedPersonalAction.active.is_(True),
                 CuratedPersonalAction.user_sub == _user.get("sub", ""),
                 or_(
                     # Legacy child saves remain visible until the next toggle.
                     CuratedPersonalAction.activity_id == CuratedActivity.identity_key,
                     # V3 stable parent saves survive canonical URL changes.
                     CuratedPersonalAction.payload["parent_group"].as_string() == group,
                 ),
             ))
             .distinct().subquery())
    if saved_only:
        statement = statement.where(group.in_(select(saves.c.g)))
    opening = _registration_open_date()
    deadline = _taipei_deadline_date()
    # Registration dates are not interchangeable with activity dates.
    # Past opening dates should not outrank upcoming deadlines; unknown
    # registration dates sort last instead of being invented from starts_on.
    future_opening = case((opening >= today, opening), else_=None)
    future_deadline = case((deadline >= today, deadline), else_=None)
    actionable_today = case(
        (CuratedActivity.registration_status == "open", literal(today)),
        else_=None,
    )
    order_day = (
        func.min(func.least(future_opening, future_deadline, actionable_today))
        if entry == "opportunities"
        else func.min(case(
            (CuratedActivity.starts_on <= today,
             case((CuratedActivity.ends_on >= today, literal(today)),
                  else_=CuratedActivity.starts_on)),
            else_=CuratedActivity.starts_on,
        ))
    )
    grouped = statement.with_only_columns(
        group.label("g"), order_day.label("day"),
        func.min(CuratedActivity.created_at).label("created"),
    ).group_by(group).subquery()
    if quick == "latest":
        sorting = (grouped.c.created.desc(), grouped.c.g.asc())
    else:
        sorting = (grouped.c.day.asc().nulls_last(), grouped.c.g.asc())
    selected = (await db.execute(
        select(grouped.c.g, grouped.c.day, grouped.c.created)
        .order_by(*sorting).offset(offset).limit(limit + 1)
    )).all()
    page = selected[:limit]
    keys = [r.g for r in page]
    rows = []
    if keys:
        rows = (await db.execute(
            select(CuratedActivity).where(
                _group_key().in_(keys),
                CuratedActivity.created_at <= snapshot,
                _active_activity_predicate(today, entry),
            ).order_by(CuratedActivity.created_at, CuratedActivity.identity_key)
        )).scalars().all()
    lookup = {key: idx for idx, key in enumerate(keys)}
    rows.sort(key=lambda item: (lookup.get(
        ("handoff:" + (item.parent_event_key or item.handoff_event_key))
        if item.parent_event_key or item.handoff_event_key else "legacy:" + item.identity_key,
        100000),
        0 if (item.handoff_details or {}).get("record_type") == "main" else 1,
        item.identity_key,
    ))
    saved_page = set()
    if keys:
        saved_page = set((await db.scalars(select(saves.c.g).where(saves.c.g.in_(keys)))).all())
    response.headers["Cache-Control"] = "no-store"
    return {"items": [
        {
            **{field: getattr(row, field) for field in (
                "identity_key", "title", "original_url", "occurrence_key",
                "summary", "city", "category", "starts_on", "ends_on", "fee_kind",
                "fee_amount", "benefit_value", "on_site_spending",
                "registration_required", "registration_status", "limited_offer",
                "registration_deadline", "created_at", "updated_at",
                "handoff_event_key", "parent_event_key", "handoff_details",
            )},
            "verification_status": (row.handoff_details or {}).get(
                "verification_status", "unknown"),
            "saved": ((_group_key_value(row)) in saved_page),
        }
        for row in rows
    ], "returned": len(page), "has_more": len(selected) > limit,
       "next_cursor": str(offset + len(page)) if len(selected) > limit else None,
       "snapshot": snapshot.isoformat(), "policy": "v3_source_unverified"}

def _group_key_value(row: CuratedActivity) -> str:
    key = row.parent_event_key or row.handoff_event_key
    return "handoff:" + key if key else "legacy:" + row.identity_key

@router.get("/curated/filters")
async def curated_filters(
    response: Response,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # Only existing DB values become filter options; no predicted places.
    if _user and isinstance(db, AsyncSession):
        from app.api.ui_policies import effective_features
        features = await effective_features(db, _user)
        if not any(x['available'] for x in features if x['key'] in ('explore', 'opportunities')):
            raise HTTPException(403, 'Activity features unavailable')
    cities = (await db.scalars(select(CuratedActivity.city).distinct()
        .where(CuratedActivity.city.is_not(None))
        .order_by(CuratedActivity.city))).all()
    categories = (await db.scalars(select(CuratedActivity.category).distinct()
        .where(CuratedActivity.category.is_not(None))
        .order_by(CuratedActivity.category))).all()
    response.headers["Cache-Control"] = "no-store"
    return {"cities": cities, "categories": categories}

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

# Machine-to-machine readback for the Cloud Run MCP adapter. The browser
# owner routes above retain their signed-in feature and owner checks.
@router.get("/curated:connector", dependencies=[Depends(require_curator)])
async def connector_list_curated(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=5000),
    city: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=100),
    starts_from: date | None = None,
    min_importance: int = Query(1, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
):
    return await list_curated(response, limit=limit, offset=offset, city=city,
                              category=category, starts_from=starts_from,
                              min_importance=min_importance, _user={}, db=db)


@router.get("/curated:connector/status", dependencies=[Depends(require_curator)])
async def connector_curated_status(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    count = await db.scalar(select(func.count()).select_from(CuratedActivity))
    newest = await db.scalar(select(func.max(CuratedActivity.updated_at)))
    response.headers["Cache-Control"] = "no-store"
    return {"items": count or 0, "last_updated_at": newest}
