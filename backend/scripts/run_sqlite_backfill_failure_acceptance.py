#!/usr/bin/env python3
"""Dev-test runtime acceptance for SQLite backfill failure semantics.

This intentionally creates a target collision with random acceptance-only IDs,
then proves the PostgreSQL import rolls back, emits failure audit evidence, and
leaves the read-only SQLite source unchanged.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sqlite3
import tempfile
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from scripts.sqlite_postgres_backfill import (
    TargetCollisionError,
    export_bundle,
    import_bundle,
)

ACCEPTANCE_LABEL = "[ACCEPTANCE TEST] SQLite backfill failure"


def _create_fixture(path: Path, *, project_id: str, task_id: str) -> None:
    now = 1_790_000_000
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA user_version = 3")
        connection.execute(
            "CREATE TABLE projects ("
            "id TEXT PRIMARY KEY, name TEXT NOT NULL, summary TEXT, "
            "status TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)"
        )
        connection.execute(
            "CREATE TABLE items ("
            "id TEXT PRIMARY KEY, title TEXT NOT NULL, note TEXT, status TEXT NOT NULL, "
            "priority TEXT NOT NULL, due_at INTEGER, reminder_at INTEGER, project_id TEXT, "
            "source_type TEXT, source_ref TEXT, created_at INTEGER NOT NULL, "
            "updated_at INTEGER NOT NULL, completed_at INTEGER, deleted_at INTEGER)"
        )
        connection.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?)",
            (project_id, ACCEPTANCE_LABEL, "source fixture", "active", now, now + 1),
        )
        connection.execute(
            "INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                task_id,
                ACCEPTANCE_LABEL,
                "must roll back",
                "pending",
                "normal",
                None,
                None,
                project_id,
                "legacy_test",
                "failure-source",
                now,
                now + 1,
                None,
                None,
            ),
        )
        connection.commit()
    finally:
        connection.close()


async def _prepare_collision(project_id: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            exists = await conn.scalar(
                text("SELECT count(*) FROM projects WHERE id=:id"),
                {"id": project_id},
            )
            assert int(exists or 0) == 0
            await conn.execute(
                text(
                    "INSERT INTO projects (id, name, summary, status) "
                    "VALUES (:id, :name, :summary, 'active')"
                ),
                {
                    "id": project_id,
                    "name": f"{ACCEPTANCE_LABEL} collision",
                    "summary": "pre-existing collision row",
                },
            )
    finally:
        await engine.dispose()


async def _verify_failure(
    *,
    project_id: str,
    task_id: str,
    fingerprint: str,
    user_sub: str,
) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            project_name = await conn.scalar(
                text("SELECT name FROM projects WHERE id=:id"),
                {"id": project_id},
            )
            assert project_name == f"{ACCEPTANCE_LABEL} collision"

            task_count = await conn.scalar(
                text("SELECT count(*) FROM tasks WHERE id=:id"),
                {"id": task_id},
            )
            assert int(task_count or 0) == 0

            ledger_count = await conn.scalar(
                text(
                    "SELECT count(*) FROM legacy_migration_rows "
                    "WHERE source_fingerprint=:fingerprint"
                ),
                {"fingerprint": fingerprint},
            )
            assert int(ledger_count or 0) == 0

            row = (
                await conn.execute(
                    text(
                        "SELECT status, result, summary FROM execution_logs "
                        "WHERE user_sub=:user_sub "
                        "AND action_type='migration.sqlite_postgres' "
                        "ORDER BY started_at DESC LIMIT 1"
                    ),
                    {"user_sub": user_sub},
                )
            ).mappings().one()
            assert row["status"] == "failure"
            assert row["result"] == "failed"
            summary = json.loads(row["summary"])
            assert summary["error_category"] == "TargetCollisionError"
    finally:
        await engine.dispose()


async def _cleanup(*, project_id: str, task_id: str, fingerprint: str, user_sub: str) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "DELETE FROM legacy_migration_rows "
                    "WHERE source_fingerprint=:fingerprint"
                ),
                {"fingerprint": fingerprint},
            )
            await conn.execute(
                text(
                    "DELETE FROM execution_logs WHERE user_sub=:user_sub "
                    "AND action_type='migration.sqlite_postgres'"
                ),
                {"user_sub": user_sub},
            )
            await conn.execute(
                text("DELETE FROM tasks WHERE id=:id"),
                {"id": task_id},
            )
            await conn.execute(
                text("DELETE FROM projects WHERE id=:id"),
                {"id": project_id},
            )
        async with engine.connect() as conn:
            remaining = int(
                await conn.scalar(
                    text("SELECT count(*) FROM projects WHERE id=:id"),
                    {"id": project_id},
                )
                or 0
            ) + int(
                await conn.scalar(
                    text("SELECT count(*) FROM tasks WHERE id=:id"),
                    {"id": task_id},
                )
                or 0
            )
            assert remaining == 0
    finally:
        await engine.dispose()


async def main() -> None:
    project_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())
    user_sub = f"acceptance-sqlite-backfill-failure-{uuid.uuid4()}"
    fingerprint = ""

    with tempfile.TemporaryDirectory(prefix="life-assistant-sqlite-backfill-failure-") as tmp:
        sqlite_path = Path(tmp) / "life_assistant.db"
        _create_fixture(sqlite_path, project_id=project_id, task_id=task_id)
        source_before = export_bundle(sqlite_path)
        fingerprint = source_before["source_fingerprint"]

        await _prepare_collision(project_id)
        try:
            try:
                await import_bundle(source_before, user_sub=user_sub)
            except TargetCollisionError:
                pass
            else:
                raise AssertionError("expected TargetCollisionError")

            source_after = export_bundle(sqlite_path)
            assert source_after == source_before
            await _verify_failure(
                project_id=project_id,
                task_id=task_id,
                fingerprint=fingerprint,
                user_sub=user_sub,
            )
            print(f"sqlite_backfill_failure_acceptance_fingerprint={fingerprint}")
            print("sqlite_backfill_failure_source_preserved=PASS")
            print("sqlite_backfill_failure_transaction_rollback=PASS")
            print("sqlite_backfill_failure_audit=PASS")
            print("sqlite_backfill_failure_acceptance=PASS")
        finally:
            await _cleanup(
                project_id=project_id,
                task_id=task_id,
                fingerprint=fingerprint,
                user_sub=user_sub,
            )
            print("sqlite_backfill_failure_acceptance_cleanup=PASS")


if __name__ == "__main__":
    asyncio.run(main())
