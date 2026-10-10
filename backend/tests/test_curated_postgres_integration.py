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
            feed = await list_curated(Response(), _user={"sub": "test"},
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


if __name__ == "__main__":
    unittest.main()
