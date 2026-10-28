"""Read-only post-migration Gmail V2 DB evidence in the existing Cloud Run Job.

No Gmail OAuth, message read, user identifiers, user counts, data changes or AI.
Nonzero exit on a missing column/head/unique user-message isolation constraint.
"""
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

EXPECTED_HEAD = "20261028_0024"
EXPECTED_COLUMNS = {
    "gmail_radar_items": {
        "classifier_version", "classification_source", "reason_code",
        "due_date", "due_text", "user_sub", "gmail_message_id", "status",
    },
    "gmail_radar_seen": {
        "classifier_version", "user_sub", "gmail_message_id", "checked_at",
    },
    "gmail_radar_scan_states": {
        "seven_day_count", "seven_day_remaining", "seven_day_complete",
        "user_sub", "three_day_complete",
    },
}


async def run_acceptance() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as db:
            await db.execute(text("SET TRANSACTION READ ONLY"))
            revisions = (await db.execute(text(
                "SELECT version_num FROM alembic_version"
            ))).scalars().all()
            if revisions != [EXPECTED_HEAD]:
                raise RuntimeError("gmail_v2_unexpected_db_revision")
            for table, needed in EXPECTED_COLUMNS.items():
                names = set((await db.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:table"
                ), {"table": table})).scalars().all())
                if not needed.issubset(names):
                    raise RuntimeError("gmail_v2_missing_schema_columns:" + table)
            constraint = await db.scalar(text(
                "SELECT 1 FROM pg_constraint "
                "WHERE conrelid='public.gmail_radar_items'::regclass "
                "AND conname='uq_gmail_radar_user_message' AND contype='u'"
            ))
            if constraint != 1:
                raise RuntimeError("gmail_v2_missing_per_user_unique_constraint")
            print("gmail_v2_live_db_readback=PASS alembic=" + EXPECTED_HEAD)
            print("gmail_v2_schema_columns=PASS checked_tables=" +
                  str(len(EXPECTED_COLUMNS)))
            print("gmail_v2_user_message_unique_constraint=PASS")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_acceptance())

