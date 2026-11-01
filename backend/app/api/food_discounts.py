"""Independent Taipei/New Taipei 41-district food discounts API and batch upsert."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import re
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.curated import normalize_url, require_curator
from app.api.ui_policies import feature_gate
from app.db.session import get_db
from app.errors import current_request_id
from app.models.execution_log import ExecutionLog
from app.models.food_discount import FoodDiscount

router = APIRouter(prefix="/food-discounts", tags=["food-discounts"])
TAIPEI = timezone(timedelta(hours=8))

FOOD_MACRO_CATEGORIES: dict[str, list[str]] = {
    "手搖飲": ["手搖", "茶飲", "奶茶", "珍奶", "果茶", "純茶", "飲料"],
    "國民美食": ["國民美食", "早餐", "便當", "自助餐", "滷肉飯", "雞肉飯", "麵", "水餃", "鍋貼", "滷味", "雞排", "炸物", "小吃", "豆花", "甜湯", "餐盒"],
    "咖啡甜點": ["咖啡", "甜點", "蛋糕", "點心", "烘焙", "下午茶"],
    "餐飲聚餐": ["餐飲", "午餐", "晚餐", "聚餐", "餐廳", "壽司"],
}


class FoodDiscountIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    candidate_key: str = Field(min_length=2, max_length=200, pattern=r"^[A-Za-z0-9_:./-]+$")
    content_hash: str | None = Field(default=None, max_length=64)
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
    details: dict | None = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return normalize_url(value)


class FoodDiscountBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[FoodDiscountIn] = Field(min_length=1, max_length=200)


async def upsert_food_discounts_batch(
    db: AsyncSession, items: list[FoodDiscountIn], *, actor: str = "connector:food-discounts"
) -> dict:
    now = datetime.now(timezone.utc)
    unique = {item.candidate_key: item for item in items}
    for key, item in unique.items():
        row = {
            **item.model_dump(),
            "candidate_key": key,
            "updated_at": now,
        }
        stmt = pg_insert(FoodDiscount).values(**row)
        changed = item.model_fields_set | {"updated_at"}
        stmt = stmt.on_conflict_do_update(
            index_elements=[FoodDiscount.candidate_key],
            set_={k: v for k, v in row.items() if k in changed and k != "candidate_key"},
        )
        await db.execute(stmt)
    db.add(
        ExecutionLog(
            id=str(uuid.uuid4()),
            request_id=current_request_id(),
            user_sub=actor,
            action_type="food_discounts.batch_upsert",
            entity_type="food_discounts",
            provider="life_assistant",
            status="success",
            result="upserted",
            summary=f"accepted={len(unique)}",
            finished_at=now,
        )
    )
    await db.commit()
    return {"accepted": len(unique), "duplicates_within_batch": len(items) - len(unique)}


@router.post(":batch", dependencies=[Depends(require_curator)])
async def ingest_food_discounts_batch(
    body: FoodDiscountBatchIn,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await upsert_food_discounts_batch(db, body.items)
    response.headers["Cache-Control"] = "no-store"
    return result


def _active_discount_predicate(today: date):
    return and_(
        FoodDiscount.claim_status == "COLLECTED_SOURCE_CLAIM",
        FoodDiscount.visibility_status == "VISIBLE_SOURCE_ONLY",
        or_(FoodDiscount.offer_ends_on.is_(None), FoodDiscount.offer_ends_on >= today),
        or_(FoodDiscount.claim_deadline_on.is_(None), FoodDiscount.claim_deadline_on >= today),
    )


def _serialize_discount(row: FoodDiscount) -> dict:
    return {
        field: getattr(row, field)
        for field in (
            "candidate_key",
            "content_hash",
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
            "details",
            "created_at",
            "updated_at",
        )
    }


@router.get("")
async def list_food_discounts(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0, le=10000),
    keyword: str | None = Query(None, max_length=120),
    city: str | None = Query(None, max_length=50),
    district: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=100),
    offer_type: Literal["bogo", "second_cup", "percent"] | None = None,
    include_expired: bool = False,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if _user and isinstance(db, AsyncSession):
        await feature_gate("food_discounts")(user=_user, db=db)
    if not isinstance(keyword, (str, type(None))):
        keyword = None
    if not isinstance(city, (str, type(None))):
        city = None
    if not isinstance(district, (str, type(None))):
        district = None
    if not isinstance(category, (str, type(None))):
        category = None

    today = datetime.now(TAIPEI).date()
    stmt = select(FoodDiscount)
    if not include_expired:
        stmt = stmt.where(_active_discount_predicate(today))

    if keyword:
        normalized = re.sub(r"\s+", " ", keyword).strip()
        if normalized:
            pattern = "%" + normalized.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
            stmt = stmt.where(
                or_(
                    FoodDiscount.merchant.ilike(pattern, escape="\\"),
                    FoodDiscount.offer_summary.ilike(pattern, escape="\\"),
                    FoodDiscount.district.ilike(pattern, escape="\\"),
                    FoodDiscount.address.ilike(pattern, escape="\\"),
                    FoodDiscount.notes.ilike(pattern, escape="\\"),
                    FoodDiscount.category.ilike(pattern, escape="\\"),
                )
            )
    if city:
        if city == "雙北通用":
            stmt = stmt.where(
                or_(
                    FoodDiscount.city == "雙北",
                    FoodDiscount.city.is_(None),
                    FoodDiscount.district.ilike("%未指定%"),
                    FoodDiscount.district.ilike("%未分區%"),
                    FoodDiscount.district.ilike("%雙北%"),
                )
            )
        else:
            stmt = stmt.where(
                or_(
                    FoodDiscount.city == city,
                    FoodDiscount.district.ilike(f"%{city}%"),
                )
            )
    if district:
        stmt = stmt.where(FoodDiscount.district.ilike(f"%{district}%"))
    if category:
        if category in FOOD_MACRO_CATEGORIES:
            kws = FOOD_MACRO_CATEGORIES[category]
            stmt = stmt.where(or_(*(FoodDiscount.category.ilike(f"%{kw}%") for kw in kws)))
        else:
            stmt = stmt.where(FoodDiscount.category == category)
    if offer_type == "bogo":
        stmt = stmt.where(
            or_(
                FoodDiscount.offer_type.ilike("%買%送%"),
                FoodDiscount.offer_summary.ilike("%買一送一%"),
                FoodDiscount.offer_summary.ilike("%買2送2%"),
                FoodDiscount.offer_summary.ilike("%買7送7%"),
            )
        )
    elif offer_type == "second_cup":
        stmt = stmt.where(
            or_(
                FoodDiscount.offer_type.ilike("%第二%"),
                FoodDiscount.offer_summary.ilike("%第二杯%"),
                FoodDiscount.offer_summary.ilike("%第二件%"),
            )
        )
    elif offer_type == "percent":
        stmt = stmt.where(
            or_(
                FoodDiscount.offer_type.ilike("%百分比%"),
                FoodDiscount.offer_type.ilike("%票券%"),
                FoodDiscount.offer_summary.ilike("%折%"),
            )
        )

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = (
        await db.execute(
            stmt.order_by(
                FoodDiscount.first_seen_on.desc().nulls_last(),
                FoodDiscount.updated_at.desc(),
                FoodDiscount.candidate_key.asc(),
            )
            .offset(offset)
            .limit(limit + 1)
        )
    ).scalars().all()
    page = rows[:limit]
    response.headers["Cache-Control"] = "no-store"
    return {
        "items": [_serialize_discount(row) for row in page],
        "total": total,
        "returned": len(page),
        "has_more": len(rows) > limit,
        "next_cursor": str(offset + len(page)) if len(rows) > limit else None,
        "policy": "v052_source_claim_unverified",
    }


@router.get("/filters")
async def food_discount_filters(
    response: Response,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if _user and isinstance(db, AsyncSession):
        await feature_gate("food_discounts")(user=_user, db=db)
    today = datetime.now(TAIPEI).date()
    districts = (
        await db.scalars(
            select(FoodDiscount.district)
            .distinct()
            .where(_active_discount_predicate(today), FoodDiscount.district.is_not(None))
            .order_by(FoodDiscount.district)
        )
    ).all()
    response.headers["Cache-Control"] = "no-store"
    return {
        "cities": ["台北市", "新北市", "雙北通用"],
        "districts": districts,
        "categories": list(FOOD_MACRO_CATEGORIES.keys()),
    }
