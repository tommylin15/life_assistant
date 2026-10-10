"""Rollback-only verification on actual database after additive 0015 upgrade.

Do not leave synthetic activities, UI preferences, or audit entries in production.
Run as the exact release image using the existing bounded Cloud Run acceptance Job.
"""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal
from app.models.curated import CuratedActivity, UserUIPreference


async def main() -> None:
    activity_key = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    account_key = "acceptance:" + uuid.uuid4().hex
    try:
        async with SessionLocal() as db:
            try:
                revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
                if revision != "20261010_0015":
                    raise RuntimeError("curated_schema_revision_mismatch")

                initial = await db.scalar(select(func.count()).select_from(CuratedActivity))
                row = CuratedActivity(
                    identity_key=activity_key,
                    occurrence_key="integration-test",
                    title="Synthetic rollback-only activity",
                    original_url="https://example.org/curated-integration-synthetic",
                    importance=5,
                    fee_kind="unknown",
                    registration_status="unknown",
                    on_site_spending=False,
                    limited_offer=False,
                )
                db.add(row)
                db.add(UserUIPreference(
                    user_sub=account_key, revision=1,
                    nav_mode="auto", pinned=["tasks"],
                    more_order=["notes"], home_cards=["tasks"],
                ))
                await db.flush()

                statement = pg_insert(CuratedActivity).values(
                    identity_key=activity_key,
                    occurrence_key="integration-test",
                    title="Synthetic updated activity",
                    original_url="https://example.org/curated-integration-synthetic",
                    importance=5,
                    fee_kind="unknown",
                    registration_status="unknown",
                    on_site_spending=False,
                    limited_offer=False,
                    updated_at=datetime.now(timezone.utc),
                ).on_conflict_do_update(
                    index_elements=[CuratedActivity.identity_key],
                    set_={"title": "Synthetic updated activity"},
                )
                await db.execute(statement)
                item = await db.get(CuratedActivity, activity_key)
                await db.refresh(item)
                preference = await db.get(UserUIPreference, account_key)
                count = await db.scalar(select(func.count()).select_from(CuratedActivity))

                if not item or item.title != "Synthetic updated activity":
                    raise RuntimeError("curated_upsert_readback_failed")
                if not preference or preference.pinned != ["tasks"]:
                    raise RuntimeError("curated_user_ui_isolation_failed")
                if count != initial + 1:
                    raise RuntimeError("curated_idempotent_count_failed")
            finally:
                await db.rollback()

        # Separate connection confirms no test data remained.
        async with SessionLocal() as db:
            assert await db.get(CuratedActivity, activity_key) is None, "synthetic_curated_row_leaked"
            assert await db.get(UserUIPreference, account_key) is None, "synthetic_user_ui_row_leaked"
        print("curated_runtime_0015=PASS rollback_only=true identity_upsert=PASS preferences=PASS")
    except Exception:
        print("curated_runtime_0015=FAIL (no synthetic transaction committed)")
        raise


if __name__ == "__main__":
    asyncio.run(main())
