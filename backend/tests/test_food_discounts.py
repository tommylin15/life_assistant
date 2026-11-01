"""Unit, handoff contract, and SQLite/PostgreSQL query tests for food_discounts."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.food_discounts import (
    FoodDiscountIn,
    _active_discount_predicate,
    food_discount_filters,
    list_food_discounts,
    upsert_food_discounts_batch,
)
from app.db.session import Base
from app.models.curated import FeatureRollout
from app.models.execution_log import ExecutionLog  # noqa: F401
from app.models.food_discount import FoodDiscount
from app.services.food_discount_handoff import (
    HEADERS,
    canonical_food_hash,
    parse_food_handoff_rows,
    upsert_food_handoff,
    validate_food_handoff_record,
)

TAIPEI = timezone(timedelta(hours=8))

try:
    import aiosqlite  # noqa: F401
    import sqlite3  # noqa: F401

    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False


class FoodDiscountsPureContractTests(IsolatedAsyncioTestCase):
    def test_active_predicate_compiles_for_postgres(self):
        stmt = select(FoodDiscount).where(_active_discount_predicate(date(2026, 11, 1)))
        sql = str(stmt.compile(dialect=postgresql.dialect()))
        self.assertIn("visibility_status", sql)
        self.assertIn("claim_status", sql)
        self.assertIn("offer_ends_on", sql)
        self.assertIn("claim_deadline_on", sql)

    async def test_handoff_contract_and_mocked_upsert_lifecycle(self):
        today = date(2026, 11, 1)
        base_rec = {
            "candidate_key": "TPE-DA-001",
            "city": "台北市",
            "district": "台北市大安區",
            "merchant": "50嵐",
            "category": "手搖飲",
            "offer_summary": "大杯純茶買一送一",
            "offer_type": "買一送一",
            "nominal_discount": "50%",
            "fixed_discount_ntd": "",
            "original_price_ntd": "40.00",
            "offer_price_ntd": "20.00",
            "period_text": "即日起",
            "address": "台北市大安區復興南路",
            "source_url": "https://example.com/50lan",
            "notes": "",
            "claim_status": "COLLECTED_SOURCE_CLAIM",
            "visibility_status": "VISIBLE_SOURCE_ONLY",
            "first_seen_on": today.isoformat(),
            "claim_deadline_on": "",
            "redemption_ends_on": "",
            "offer_ends_on": "",
            "last_positive_on": today.isoformat(),
            "next_refresh_on": (today + timedelta(days=7)).isoformat(),
            "date_basis": "NO_END_DATE_7D_REFRESH",
            "disclosure": "公開來源宣稱，未逐項核實，不保證到店可使用",
            "handoff_status": "READY",
            "handoff_updated_at_tpe": datetime(2026, 11, 1, 4, 45, tzinfo=TAIPEI).isoformat(),
            "life_ack_at_tpe": "",
            "life_import_result": "",
            "life_error": "",
        }
        base_rec["content_hash"] = canonical_food_hash(base_rec)
        matrix = [list(HEADERS), [base_rec[k] for k in HEADERS]]
        parsed = parse_food_handoff_rows(matrix)
        self.assertEqual(len(parsed), 1)
        item = validate_food_handoff_record(parsed[0])

        db = AsyncMock()
        db.add = MagicMock()
        db.get_bind = lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
        db.scalar.return_value = None

        r1 = await upsert_food_handoff(db, item, parsed[0]["content_hash"])
        self.assertEqual(r1, "CREATED")

        existing = FoodDiscount(
            candidate_key="TPE-DA-001",
            content_hash=parsed[0]["content_hash"],
            merchant="50嵐",
            offer_summary="大杯純茶買一送一",
            source_url="https://example.com/50lan",
            details={"handoff_updated_at_tpe": base_rec["handoff_updated_at_tpe"]},
        )
        db.scalar.return_value = existing
        r2 = await upsert_food_handoff(db, item, parsed[0]["content_hash"])
        self.assertEqual(r2, "UNCHANGED")

        updated_rec = {
            **base_rec,
            "visibility_status": "HIDDEN_REFRESH_DUE",
            "handoff_updated_at_tpe": datetime(2026, 11, 8, 4, 45, tzinfo=TAIPEI).isoformat(),
        }
        updated_rec["content_hash"] = canonical_food_hash(updated_rec)
        item_updated = validate_food_handoff_record(updated_rec)
        r3 = await upsert_food_handoff(db, item_updated, updated_rec["content_hash"])
        self.assertEqual(r3, "UPDATED")
        self.assertEqual(existing.visibility_status, "HIDDEN_REFRESH_DUE")


@unittest.skipUnless(HAS_AIOSQLITE, "aiosqlite + sqlite3 required")
class FoodDiscountsSqliteIntegrationTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_batch_upsert_and_filtering_respects_v052_visibility(self):
        today = date.today()
        items = [
            FoodDiscountIn(
                candidate_key="FOOD-INTEL-20261031-STARBUCKS-2NDHALF",
                city="雙北",
                district="未指定（雙北 foodpanda 合作門市）",
                merchant="星巴克（foodpanda 外送）",
                category="咖啡／茶飲",
                offer_summary="指定大杯以上三款飲品，購買兩杯第二杯半價",
                offer_type="第二杯半價",
                nominal_discount="25%（同價假設）",
                source_url="https://www.starbucks.com.tw/stores/allevent/show.jspx?n=5423",
                claim_status="COLLECTED_SOURCE_CLAIM",
                visibility_status="VISIBLE_SOURCE_ONLY",
                first_seen_on=today,
                offer_ends_on=today + timedelta(days=3),
            ),
            FoodDiscountIn(
                candidate_key="FOOD-INTEL-20261030-COCO-BOGO",
                city="台北市",
                district="台北市大安區",
                merchant="CoCo都可",
                category="一般手搖飲",
                offer_summary="指定飲品同品項買一送一",
                offer_type="買一送一",
                nominal_discount="50%（兩杯同價）",
                source_url="https://www.coco-tea.com/news/bogo",
                claim_status="COLLECTED_SOURCE_CLAIM",
                visibility_status="VISIBLE_SOURCE_ONLY",
                first_seen_on=today,
            ),
            FoodDiscountIn(
                candidate_key="FOOD-INTEL-EXPIRED-ITEM",
                city="新北市",
                district="新北市板橋區",
                merchant="過期茶飲店",
                category="一般手搖飲",
                offer_summary="買一送一已過期",
                offer_type="買一送一",
                source_url="https://example.com/expired",
                claim_status="COLLECTED_SOURCE_CLAIM",
                visibility_status="EXPIRED",
                offer_ends_on=today - timedelta(days=1),
            ),
        ]
        async with self.Session() as db:
            db.add(FeatureRollout(feature_key="food_discounts", status="enabled", audience="all", revision=1))
            await db.commit()
            res = await upsert_food_discounts_batch(db, items)
            self.assertEqual(res["accepted"], 3)

            listing = await list_food_discounts(
                Response(),
                limit=20,
                offset=0,
                keyword=None,
                city=None,
                district=None,
                category=None,
                offer_type=None,
                include_expired=False,
                _user={"sub": "u-1", "email": "user@example.com"},
                db=db,
            )
            self.assertEqual(listing["total"], 2)
            keys = [x["candidate_key"] for x in listing["items"]]
            self.assertIn("FOOD-INTEL-20261031-STARBUCKS-2NDHALF", keys)
            self.assertIn("FOOD-INTEL-20261030-COCO-BOGO", keys)
            self.assertNotIn("FOOD-INTEL-EXPIRED-ITEM", keys)

            bogo_only = await list_food_discounts(
                Response(),
                limit=20,
                offset=0,
                keyword=None,
                city=None,
                district=None,
                category="手搖飲",
                offer_type="bogo",
                include_expired=False,
                _user={"sub": "u-1", "email": "user@example.com"},
                db=db,
            )
            self.assertEqual(bogo_only["total"], 1)
            self.assertEqual(bogo_only["items"][0]["merchant"], "CoCo都可")

            opts = await food_discount_filters(
                Response(),
                _user={"sub": "u-1", "email": "user@example.com"},
                db=db,
            )
            self.assertIn("手搖飲", opts["categories"])
            self.assertIn("國民美食", opts["categories"])
