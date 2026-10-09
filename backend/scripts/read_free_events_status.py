"""Read-only production acceptance: factual source/catalog counters only.

Run inside an already-configured Cloud Run DB job via a transient
`python -c` override. It does not ingest, review or publish any event.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models.free_events import FreeEvent
from app.services.free_events_discovery import verified_catalog_query

READBACK_MARKER = "FREE_EVENTS_READBACK_V1"
SOURCE_ID = "moc_events_all"
EXPECTED_REVISION = "20261009_0014"


async def readback() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            # Must be the first statement in the connection transaction.
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            await conn.execute(text("SET LOCAL statement_timeout = '20s'"))
            revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != EXPECTED_REVISION:
                raise ValueError("unexpected database revision")

            observations = (await conn.execute(text("""
                SELECT count(*) AS runs,
                       COALESCE(sum(accepted_count), 0) AS attempts,
                       COALESCE(sum(rejected_count), 0) AS rejects,
                       min(observed_at) AS first_at,
                       max(observed_at) AS last_at
                FROM free_event_source_observations
                WHERE source_id = :source
            """), {"source": SOURCE_ID})).mappings().one()

            latest = (await conn.execute(text("""
                SELECT observed_at, record_count, accepted_count,
                       rejected_count, fee_unknown_count,
                       registration_start_unknown_count, complete_source
                FROM free_event_source_observations
                WHERE source_id = :source
                ORDER BY observed_at DESC, id DESC LIMIT 1
            """), {"source": SOURCE_ID})).mappings().first()

            daily = (await conn.execute(text("""
                SELECT DISTINCT (observed_at AT TIME ZONE 'Asia/Taipei')::date AS day
                FROM free_event_source_observations
                WHERE source_id = :source ORDER BY day
            """), {"source": SOURCE_ID})).scalars().all()
            observed_days = {d.isoformat() for d in daily}
            # The 14-day gate requires real distinct calendar dates and no missing days.
            today = now.astimezone(ZoneInfo("Asia/Taipei")).date()
            required_days = [
                (today - timedelta(days=offset)).isoformat()
                for offset in range(13, -1, -1)
            ]
            days_missing = [d for d in required_days if d not in observed_days]

            events = (await conn.execute(text("""
                SELECT count(*) AS total,
                       count(DISTINCT canonical_key) AS unique_keys,
                       count(*) FILTER (WHERE verification_status = 'unverified') AS unverified,
                       count(*) FILTER (WHERE verification_status = 'verified') AS verified,
                       count(*) FILTER (WHERE verification_status = 'stale') AS stale,
                       count(*) FILTER (WHERE verification_status = 'invalid') AS invalid
                FROM free_events WHERE source_id = :source
            """), {"source": SOURCE_ID})).mappings().one()
            session_count = await conn.scalar(text("""
                SELECT count(*) FROM free_event_sessions s
                JOIN free_events e ON s.event_id=e.id
                WHERE e.source_id=:source
            """), {"source": SOURCE_ID})
            opportunity_count = await conn.scalar(text("""
                SELECT count(*) FROM free_event_registration_opportunities r
                JOIN free_event_sessions s ON r.session_id=s.id
                JOIN free_events e ON s.event_id=e.id
                WHERE e.source_id=:source
            """), {"source": SOURCE_ID})

            queue_states = (await conn.execute(text("""
                SELECT state, count(*) FROM free_event_candidate_queue
                WHERE source_id = :source GROUP BY state
            """), {"source": SOURCE_ID})).all()
            queue_counts = {str(state): int(count) for state, count in queue_states}
            # Count rows under the exact production API predicate; do not
            # substitute "fee=free" or non-verified source candidates.
            live_query = verified_catalog_query(now=now, limit=50, offset=0)
            unrestricted = live_query.limit(None).offset(None).order_by(None)
            ui_opportunity_rows = await conn.scalar(
                select(func.count()).select_from(unrestricted.subquery())
            )
            visible_events = await conn.scalar(
                select(func.count()).select_from(
                    unrestricted.with_only_columns(FreeEvent.id)
                    .distinct().subquery()
                )
            )

            # "attempts - unique" signals reprocessing but is NOT a
            # confirmed collision count; the DB constraint alone
            # cannot prove how many upserts were deduplicated.
            total = int(events["total"])
            attempts = int(observations["attempts"])
            return {
                "status": "PASS_READ_ONLY",
                "as_of_utc": now.isoformat(),
                "alembic_revision": revision,
                "source_id": SOURCE_ID,
                "observation_runs": int(observations["runs"]),
                "observed_distinct_days": len(observed_days),
                "first_observation_utc": observations["first_at"].isoformat()
                    if observations["first_at"] else None,
                "last_observation_utc": observations["last_at"].isoformat()
                    if observations["last_at"] else None,
                "missing_days_in_last_14_taipei": days_missing,
                "last_14_days_coverage_pass": len(days_missing) == 0,
                "accepted_attempts_sum": attempts,
                "rejected_attempts_sum": int(observations["rejects"]),
                "latest_observation": ({
                    "observed_at_utc": latest["observed_at"].isoformat(),
                    "source_records": int(latest["record_count"]),
                    "accepted": int(latest["accepted_count"]),
                    "rejected": int(latest["rejected_count"]),
                    "unknown_fee": int(latest["fee_unknown_count"]),
                    "unknown_registration_start": int(latest["registration_start_unknown_count"]),
                    "complete_source": bool(latest["complete_source"]),
                } if latest else None),
                "current_source_events": total,
                "queue_source_counts": queue_counts,
                "queue_source_total": sum(queue_counts.values()),
                "queue_source_done": queue_counts.get("done", 0),
                "queue_source_failed": queue_counts.get("failed", 0),
                "current_unique_canonical_keys": int(events["unique_keys"]),
                "current_duplicate_canonical_keys": total - int(events["unique_keys"]),
                "current_source_sessions": int(session_count or 0),
                "current_source_opportunities": int(opportunity_count or 0),
                "source_events_unverified": int(events["unverified"]),
                "source_events_verified": int(events["verified"]),
                "source_events_stale": int(events["stale"]),
                "source_events_invalid": int(events["invalid"]),
                "attempts_minus_current_unique_not_exact_dedup":
                    max(0, attempts - total),
                "ui_verified_opportunity_rows": int(ui_opportunity_rows or 0),
                "ui_unique_visible_events": int(visible_events or 0),
                "strict_ui_gate": "same_predicate_as_GET_free_events",
                "full_14_day_quality_acceptance": "NOT_VERIFIED",
            }
    finally:
        await engine.dispose()


def main() -> None:
    try:
        result = asyncio.run(readback())
    except Exception:
        # No connection strings, SQL bind values or secret material in logs.
        print("FREE_EVENTS_READBACK_ERROR: read_only_query_failed", flush=True)
        raise SystemExit(2) from None
    print(READBACK_MARKER + " " +
          json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
