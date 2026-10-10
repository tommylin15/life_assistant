"""Real ephemeral PostgreSQL integration for curated identities, transactions and private UI."""
import os
import uuid
import unittest
from datetime import date

from fastapi import Response
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.curated import CuratedBatchIn, identity, ingest_curated_batch, list_curated
from app.api.ui_policies import UIPreferencesWrite, put_my_preferences, get_my_preferences
from app.models.curated import CuratedActivity


def _test_dsn():
    url = os.environ.get("FREE_EVENTS_INTEGRATION_DATABASE_URL")
    if not url:
        return None
    parsed = make_url(url)
    if parsed.host not in ("localhost", "127.0.0.1") or parsed.database != "free_events_ci" or parsed.username != "postgres":
        raise RuntimeError("Refusing to use a non-test database")
    return url


@unittest.skipUnless(os.getenv("FREE_EVENTS_INTEGRATION_DATABASE_URL"), "CI PostgreSQL sidecar required")
class CuratedPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(_test_dsn())
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.url = f"https://example.org/events/{uuid.uuid4().hex}"

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_idempotent_retry_and_distinct_occurrences_and_readback(self):
        first = CuratedBatchIn.model_validate({"items": [
            {"title": "Session 1", "original_url": self.url,
             "occurrence_key": "day1", "importance": 5, "fee_kind": "unknown"},
            {"title": "Session 2", "original_url": self.url,
             "occurrence_key": "day2", "importance": 3, "fee_kind": "paid",
             "fee_amount": 100, "benefit_value": 300}
        ]})
        async with self.sessions() as db:
            result = await ingest_curated_batch(first, Response(), db=db)
            self.assertEqual(result["accepted"], 2)
        retry = CuratedBatchIn.model_validate({"items": [
            {"title": "Updated 1", "original_url": self.url + "?utm_source=x",
             "occurrence_key": "day1", "importance": 5},
        ]})
        async with self.sessions() as db:
            await ingest_curated_batch(retry, Response(), db=db)
            count = await db.scalar(select(func.count()).select_from(CuratedActivity)
                                    .where(CuratedActivity.original_url == self.url))
            self.assertEqual(count, 2)
            row = await db.get(CuratedActivity, identity(retry.items[0]))
            self.assertEqual(row.title, "Updated 1")
            feed = await list_curated(Response(), _user={},
                                      db=db, min_importance=5, limit=20, offset=0,
                                      city=None, category=None, starts_from=None)
            self.assertTrue(any(x["title"] == "Updated 1" for x in feed["items"]))

    async def test_owner_release_and_ai_policy_races_are_rejected(self):
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.api.ui_policies import (
            FeatureWrite, AIPolicyWrite, put_rollout, update_ai_policy,
            get_rollouts, get_my_preferences,
        )
        owner = {"sub": f"ci-policy-{uuid.uuid4().hex}", "email": "ci-owner@example.org"}
        with patch.dict(os.environ, {"ALLOWED_GOOGLE_EMAIL": "ci-owner@example.org"}):
            async with self.sessions() as db:
                flag = FeatureWrite(key="notes", expected_revision=0,
                                    status="beta", audience="owner")
                saved = await put_rollout(flag, user=owner, db=db)
                self.assertEqual(saved["revision"], 1)
                readback = await get_rollouts(Response(), _owner=owner, db=db)
                note = next(item for item in readback["features"] if item["key"] == "notes")
                self.assertEqual(note["status"], "beta")
                with self.assertRaises(HTTPException) as conflict:
                    await put_rollout(flag, user=owner, db=db)
                self.assertEqual(conflict.exception.status_code, 409)
                ai = AIPolicyWrite(expected_revision=0, enabled=False,
                                   allowed_providers=["gemini"])
                result = await update_ai_policy(ai, user=owner, db=db)
                self.assertFalse(result["enabled"])
                with self.assertRaises(HTTPException) as ai_conflict:
                    await update_ai_policy(ai, user=owner, db=db)
                self.assertEqual(ai_conflict.exception.status_code, 409)

    async def test_ui_preferences_revisions_and_account_isolation(self):
        owner = {"sub": f"ci-owner-{uuid.uuid4().hex}"}
        other = {"sub": f"ci-other-{uuid.uuid4().hex}"}
        first = UIPreferencesWrite(expected_revision=0, pinned=["tasks"],
                                   more_order=["notes"], home_cards=["tasks"])
        async with self.sessions() as db:
            updated = await put_my_preferences(first, user=owner, db=db)
            self.assertEqual(updated["revision"], 1)
            mine = await get_my_preferences(Response(), user=owner, db=db)
            other_view = await get_my_preferences(Response(), user=other, db=db)
            self.assertEqual(mine["pinned"], ["tasks"])
            self.assertEqual(other_view["revision"], 0)
            from fastapi import HTTPException
            with self.assertRaises(HTTPException) as ex:
                await put_my_preferences(first, user=owner, db=db)
            self.assertEqual(ex.exception.status_code, 409)

    async def test_handoff_concurrent_retry_url_change_and_stale_version(self):
        import asyncio
        from app.services.curated_handoff import HandoffItem, upsert_handoff
        key = "ci:" + uuid.uuid4().hex
        item = HandoffItem(event_key=key, record_type="main", title="穩定鍵活動",
            official_url=self.url, importance_star=5,
            verified_at_tpe="2026-10-10T09:00:00+08:00",
            handoff_updated_at_tpe="2026-10-10T09:00:00+08:00")
        async def apply(value, version):
            async with self.sessions() as db:
                return await upsert_handoff(db, value, version)
        result = await asyncio.gather(*[apply(item, "a"*64) for _ in range(6)])
        self.assertEqual(result.count("CREATED"), 1)
        self.assertEqual(result.count("UNCHANGED"), 5)
        updated = HandoffItem.model_validate({**item.model_dump(),
            "official_url": self.url + "/new", "handoff_updated_at_tpe": "2026-10-10T10:00:00+08:00"})
        self.assertEqual(await apply(updated, "b"*64), "UPDATED")
        with self.assertRaisesRegex(ValueError, "superseded"):
            await apply(item, "a"*64)
        async with self.sessions() as db:
            rows = (await db.execute(select(CuratedActivity).where(CuratedActivity.handoff_event_key == key))).scalars().all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].original_url, self.url + "/new")

    async def test_personal_task_retry_cancel_and_account_isolation(self):
        from app.api.curated_actions import ActionWrite, set_action, my_actions
        from app.api.tasks import _require_task
        from app.models.task import Task
        from fastapi import HTTPException
        batch = CuratedBatchIn.model_validate({"items":[{"title":"個人動作活動", "original_url":self.url}]})
        async with self.sessions() as db:
            await ingest_curated_batch(batch, Response(), db=db)
        activity_id = identity(batch.items[0])
        owner = {"sub":"action-owner:" + uuid.uuid4().hex}
        other = {"sub":"action-other:" + uuid.uuid4().hex}
        async with self.sessions() as db:
            first = await set_action(activity_id, "task", ActionWrite(active=True), owner, db)
            retry = await set_action(activity_id, "task", ActionWrite(active=True), owner, db)
            self.assertEqual(first["entity_id"], retry["entity_id"])
            self.assertTrue(retry["unchanged"])
            hidden = await my_actions(Response(), other, db)
            self.assertEqual(hidden["items"], [])
            with self.assertRaises(HTTPException) as ctx:
                await _require_task(db, first["entity_id"], other)
            self.assertEqual(ctx.exception.status_code, 404)
            await set_action(activity_id, "task", ActionWrite(active=False), owner, db)
            task = await db.get(Task, first["entity_id"])
            self.assertEqual(task.status, "cancelled")

    async def test_parent_pagination_keeps_all_distinct_offers_on_one_card(self):
        from app.services.curated_handoff import HandoffItem, upsert_handoff
        key = "ci:" + uuid.uuid4().hex
        city = uuid.uuid4().hex
        main = HandoffItem(event_key=key, record_type="main", title="主活動",
            city=city, official_url=self.url, importance_star=3,
            verified_at_tpe="2026-10-10T09:00:00+08:00",
            handoff_updated_at_tpe="2026-10-10T09:00:00+08:00")
        offer = HandoffItem.model_validate({**main.model_dump(), "event_key":key+":offer",
            "parent_event_key":key, "record_type":"offer", "title":"不同優惠",
            "registration_url": self.url+"/register", "importance_star":5})
        async with self.sessions() as db:
            db.add(CuratedActivity(identity_key=key, occurrence_key="legacy", title="不同的舊版活動",
                original_url=self.url+"/legacy", city=city+":other", importance=1,
                fee_kind="unknown", registration_status="unknown", on_site_spending=False,
                limited_offer=False))
            await upsert_handoff(db, main, "c"*64)
            await upsert_handoff(db, offer, "d"*64)
            feed = await list_curated(Response(), _user={}, db=db, min_importance=5,
                limit=1, offset=0, city=city, category=None, starts_from=None)
            self.assertEqual(feed["returned"], 1)
            self.assertEqual(len(feed["items"]), 2)
            self.assertEqual({r["title"] for r in feed["items"]}, {"主活動", "不同優惠"})


if __name__ == "__main__":
    unittest.main()
