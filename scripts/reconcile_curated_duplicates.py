"""
Non-destructive Reconciliation of Historical Curated Activity Duplicates in PostgreSQL.

Identifies duplicate physical event entities created across different daily discovery batches
(e.g., when the same festival was discovered under multiple domains or modified slugs)
and nests them under a canonical parent_event_key, in compliance with 04-upsert.md.

Does NOT delete any record.
"""
import argparse
import asyncio
import ctypes
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

# Preload libstdc++ for greenlet/async SQLAlchemy
try:
    ctypes.cdll.LoadLibrary("/mnt/stateful_partition/antigravity/.local/lib/libstdc++.so.6")
except Exception:
    pass

sys.path.append("backend")
from app.db.session import engine, SessionLocal
from app.models.curated import CuratedActivity
from app.services.curated_dedup import normalize_title, is_entity_match, calculate_date_overlap_ratio
from sqlalchemy import select, text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reconcile_curated")


async def run_reconciliation(dry_run: bool = True):
    logger.info(f"Starting Curated Duplicates Reconciliation (dry_run={dry_run})...")

    async with SessionLocal() as db:
        stmt = select(CuratedActivity).order_by(CuratedActivity.created_at.asc())
        activities = (await db.scalars(stmt)).all()
        logger.info(f"Loaded {len(activities)} total activities from PostgreSQL.")

        by_city = defaultdict(list)
        for act in activities:
            city = (act.city or "").strip()
            by_city[city].append(act)

        updates_planned = {}

        # Scan each city's activities chronologically
        for city, city_acts in by_city.items():
            for i, a1 in enumerate(city_acts):
                for a2 in city_acts[i + 1:]:
                    # Skip if already assigned to same parent
                    p1 = a1.parent_event_key or a1.handoff_event_key
                    p2 = a2.parent_event_key or a2.handoff_event_key
                    if p1 and p1 == p2:
                        continue

                    matched, reason = is_entity_match(
                        a1.title, a1.city, a1.starts_on, a1.ends_on,
                        a2.title, a2.city, a2.starts_on, a2.ends_on,
                    )
                    if matched:
                        # a1 is earlier (canonical)
                        canonical_key = a1.parent_event_key or a1.handoff_event_key or a1.identity_key
                        if a2.identity_key not in updates_planned and a2.parent_event_key != canonical_key:
                            updates_planned[a2.identity_key] = {
                                "member_id": a2.identity_key,
                                "title": a2.title,
                                "created_at": a2.created_at,
                                "old_parent": a2.parent_event_key,
                                "new_parent": canonical_key,
                                "canonical_title": a1.title,
                                "canonical_key": canonical_key,
                            }

        logger.info(f"Planned updates for {len(updates_planned)} records.")
        for u in updates_planned.values():
            logger.info(f"  [RECONCILE] '{u['title'][:40]}' -> parent='{u['new_parent']}' (Canonical: '{u['canonical_title'][:40]}')")

        if dry_run:
            logger.info("DRY RUN completed. No database modifications were made.")
            return len(updates_planned)

        # Apply updates in transaction
        logger.info("Applying updates to database...")
        update_count = 0
        for u in updates_planned.values():
            act = await db.scalar(select(CuratedActivity).where(CuratedActivity.identity_key == u["member_id"]))
            if act:
                act.parent_event_key = u["new_parent"]
                if act.handoff_details:
                    details = dict(act.handoff_details)
                    details["parent_event_key"] = u["new_parent"]
                    if details.get("parent_event_key") == act.handoff_event_key:
                        details["record_type"] = "main"
                    elif details.get("record_type") == "main":
                        details["record_type"] = "session"
                    act.handoff_details = details
                act.updated_at = datetime.now(timezone.utc)
                update_count += 1

        await db.commit()
        logger.info(f"Successfully reconciled {update_count} duplicate records in PostgreSQL.")

        # Also sync local handoff sheets if they exist
        local_handoffs = [
            Path("/tmp/tw_sheets_20261105/台灣活動｜交接資料.xlsx"),
            Path("/mnt/stateful_partition/antigravity/gdrive/agy_workspace/life_assistantGPT/台灣活動探索｜排程步驟/台灣活動｜交接資料.xlsx"),
        ]
        import openpyxl
        for hf in local_handoffs:
            if not hf.exists():
                continue
            try:
                wb = openpyxl.load_workbook(str(hf))
                if "交接資料" in wb.sheetnames:
                    sheet = wb["交接資料"]
                    modified = False
                    for r in range(2, sheet.max_row + 1):
                        ek = sheet.cell(r, 1).value
                        if not ek:
                            continue
                        for u in updates_planned.values():
                            act = await db.scalar(select(CuratedActivity).where(CuratedActivity.identity_key == u["member_id"]))
                            if act and act.handoff_event_key == ek:
                                sheet.cell(r, 3, u["new_parent"])  # parent_event_key col 3
                                sheet.cell(r, 4, "session")        # record_type col 4
                                if sheet.cell(r, 29).value == "ERROR":
                                    sheet.cell(r, 29, "ACKED")
                                    sheet.cell(r, 32, "")
                                modified = True
                    if modified:
                        wb.save(str(hf))
                        logger.info(f"Synchronized reconciled parent keys to {hf}")
                wb.close()
            except Exception as e:
                logger.warning(f"Failed to sync reconciled keys to {hf}: {e}")

        return update_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile duplicate curated activities.")
    parser.add_argument("--apply", action="store_true", help="Apply updates to database (default is dry-run)")
    args = parser.parse_args()

    async def _main():
        try:
            await run_reconciliation(dry_run=not args.apply)
        finally:
            await engine.dispose()

    asyncio.run(_main())
