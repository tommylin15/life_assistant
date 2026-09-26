#!/usr/bin/env python3
"""Apply and verify the additive Cloud Domain Parity migration in dev-test.

This runner deliberately fails closed when target tables were pre-created while
Alembic is still at the previous revision. It never stamps, drops, truncates, or
rewrites data to hide migration drift.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import re
import subprocess
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings


PREVIOUS_REVISION = "20260925_0003"
TARGET_REVISION = "20260926_0004"
TARGET_TABLES = (
    "notes",
    "note_links",
    "habits",
    "habit_completions",
    "shopping_lists",
    "shopping_items",
    "templates",
)

EXPECTED_COLUMNS = {
    "notes": {
        "id": ("character varying", 36, False),
        "title": ("text", None, True),
        "body": ("text", None, True),
        "project_id": ("character varying", 36, True),
        "created_at": ("timestamp with time zone", None, False),
        "updated_at": ("timestamp with time zone", None, False),
    },
    "note_links": {
        "source_note_id": ("character varying", 36, False),
        "target_note_id": ("character varying", 36, False),
    },
    "habits": {
        "id": ("character varying", 36, False),
        "title": ("character varying", 500, False),
        "recurrence_rule": ("text", None, False),
        "reminder_time": ("character varying", 16, True),
        "is_active": ("boolean", None, False),
        "created_at": ("timestamp with time zone", None, False),
    },
    "habit_completions": {
        "id": ("character varying", 36, False),
        "habit_id": ("character varying", 36, False),
        "completed_at": ("timestamp with time zone", None, False),
    },
    "shopping_lists": {
        "id": ("character varying", 36, False),
        "name": ("character varying", 500, False),
        "project_id": ("character varying", 36, True),
        "created_at": ("timestamp with time zone", None, False),
    },
    "shopping_items": {
        "id": ("character varying", 36, False),
        "list_id": ("character varying", 36, False),
        "name": ("character varying", 500, False),
        "category": ("character varying", 255, True),
        "is_done": ("boolean", None, False),
        "sort_order": ("integer", None, False),
    },
    "templates": {
        "id": ("character varying", 36, False),
        "name": ("character varying", 500, False),
        "template_type": ("character varying", 64, False),
        "payload_json": ("text", None, False),
        "created_at": ("timestamp with time zone", None, False),
        "updated_at": ("timestamp with time zone", None, False),
    },
}

EXPECTED_PRIMARY_KEYS = {
    "notes": ("id",),
    "note_links": ("source_note_id", "target_note_id"),
    "habits": ("id",),
    "habit_completions": ("id",),
    "shopping_lists": ("id",),
    "shopping_items": ("id",),
    "templates": ("id",),
}

EXPECTED_FOREIGN_KEYS = {
    "note_links": {
        ("source_note_id", "notes", "id"),
        ("target_note_id", "notes", "id"),
    },
    "habit_completions": {("habit_id", "habits", "id")},
    "shopping_items": {("list_id", "shopping_lists", "id")},
}

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Cloud Run execution describe exposes the container exit code even when the
# deploy service account cannot read Cloud Logging. Keep these stable and
# non-secret so deployment evidence can distinguish failure classes.
EXIT_DATABASE = 20
EXIT_CONTRACT = 21
EXIT_ALEMBIC = 22
EXIT_UNEXPECTED = 29


def classify_failure(exc: BaseException) -> int:
    if isinstance(exc, subprocess.CalledProcessError):
        return EXIT_ALEMBIC
    if isinstance(exc, SQLAlchemyError):
        return EXIT_DATABASE
    if isinstance(exc, RuntimeError):
        return EXIT_CONTRACT
    return EXIT_UNEXPECTED


def decide_migration_action(current_revision: str, target_tables_present: set[str]) -> str:
    present = set(target_tables_present)
    expected = set(TARGET_TABLES)
    if current_revision == PREVIOUS_REVISION:
        if present:
            names = ",".join(sorted(present))
            raise RuntimeError(
                "migration drift: target tables already exist before Alembic "
                f"{TARGET_REVISION}: {names}"
            )
        return "upgrade"
    if current_revision == TARGET_REVISION:
        missing = expected - present
        if missing:
            raise RuntimeError(
                "missing target tables at applied revision "
                f"{TARGET_REVISION}: {','.join(sorted(missing))}"
            )
        return "verify"
    raise RuntimeError(
        f"unexpected alembic revision: {current_revision or '<missing>'}; "
        f"expected {PREVIOUS_REVISION} or {TARGET_REVISION}"
    )


async def _current_revision(conn: AsyncConnection) -> str:
    exists = await conn.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
    if not exists:
        raise RuntimeError("alembic_version table is missing")
    rows = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalars().all()
    if len(rows) != 1:
        raise RuntimeError(f"expected one alembic_version row, found {len(rows)}")
    return str(rows[0])


async def _public_tables(conn: AsyncConnection) -> set[str]:
    rows = (
        await conn.execute(
            text(
                "SELECT tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname = 'public' ORDER BY tablename"
            )
        )
    ).scalars().all()
    return {str(row) for row in rows}


async def _row_counts(conn: AsyncConnection, tables: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in sorted(tables):
        if not _SAFE_IDENTIFIER.fullmatch(table):
            raise RuntimeError(f"unsafe table identifier in catalog: {table!r}")
        value = await conn.scalar(text(f'SELECT count(*) FROM "{table}"'))
        counts[table] = int(value or 0)
    return counts


async def _verify_columns(conn: AsyncConnection, table: str) -> None:
    result = await conn.execute(
        text(
            "SELECT column_name, data_type, character_maximum_length, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table "
            "ORDER BY ordinal_position"
        ),
        {"table": table},
    )
    actual = {
        str(row.column_name): (
            str(row.data_type),
            int(row.character_maximum_length) if row.character_maximum_length is not None else None,
            str(row.is_nullable) == "YES",
        )
        for row in result
    }
    expected = EXPECTED_COLUMNS[table]
    if actual != expected:
        raise RuntimeError(f"schema mismatch for {table}: columns/nullability/type differ")


async def _primary_key(conn: AsyncConnection, table: str) -> tuple[str, ...]:
    result = await conn.execute(
        text(
            "SELECT a.attname AS column_name "
            "FROM pg_constraint c "
            "JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS u(attnum, ordinality) ON true "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = u.attnum "
            "WHERE c.conrelid = to_regclass(:qualified_table) AND c.contype = 'p' "
            "ORDER BY u.ordinality"
        ),
        {"qualified_table": f"public.{table}"},
    )
    return tuple(str(row.column_name) for row in result)


async def _foreign_keys(conn: AsyncConnection, table: str) -> set[tuple[str, str, str]]:
    result = await conn.execute(
        text(
            "SELECT la.attname AS local_column, ft.relname AS foreign_table, "
            "fa.attname AS foreign_column "
            "FROM pg_constraint c "
            "JOIN LATERAL unnest(c.conkey, c.confkey) "
            "AS k(local_attnum, foreign_attnum) ON true "
            "JOIN pg_attribute la ON la.attrelid = c.conrelid AND la.attnum = k.local_attnum "
            "JOIN pg_class ft ON ft.oid = c.confrelid "
            "JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = k.foreign_attnum "
            "WHERE c.conrelid = to_regclass(:qualified_table) AND c.contype = 'f'"
        ),
        {"qualified_table": f"public.{table}"},
    )
    return {
        (str(row.local_column), str(row.foreign_table), str(row.foreign_column))
        for row in result
    }


async def _verify_schema(conn: AsyncConnection) -> None:
    tables = await _public_tables(conn)
    missing = set(TARGET_TABLES) - tables
    if missing:
        raise RuntimeError(f"missing target tables: {','.join(sorted(missing))}")

    for table in TARGET_TABLES:
        await _verify_columns(conn, table)
        actual_pk = await _primary_key(conn, table)
        if actual_pk != EXPECTED_PRIMARY_KEYS[table]:
            raise RuntimeError(f"primary key mismatch for {table}: {actual_pk}")

    for table, expected in EXPECTED_FOREIGN_KEYS.items():
        actual = await _foreign_keys(conn, table)
        if actual != expected:
            raise RuntimeError(f"foreign key mismatch for {table}: {sorted(actual)}")

    index_def = await conn.scalar(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = 'habit_completions' "
            "AND indexname = 'ix_habit_completions_habit_id_completed_at'"
        )
    )
    normalized = " ".join(str(index_def or "").lower().split())
    if "(habit_id, completed_at desc)" not in normalized:
        raise RuntimeError("habit completion descending index is missing or mismatched")


async def _inspect_before(engine) -> tuple[str, set[str], set[str], dict[str, int]]:
    async with engine.connect() as conn:
        revision = await _current_revision(conn)
        tables = await _public_tables(conn)
        target_present = set(TARGET_TABLES) & tables
        preserved_tables = tables - set(TARGET_TABLES) - {"alembic_version"}
        counts = await _row_counts(conn, preserved_tables)
        return revision, target_present, preserved_tables, counts


async def _verify_after(
    engine,
    preserved_tables: set[str],
    baseline_counts: dict[str, int],
) -> None:
    async with engine.connect() as conn:
        revision = await _current_revision(conn)
        if revision != TARGET_REVISION:
            raise RuntimeError(
                f"post-migration revision mismatch: {revision}; expected {TARGET_REVISION}"
            )
        await _verify_schema(conn)
        tables = await _public_tables(conn)
        missing_preserved = preserved_tables - tables
        if missing_preserved:
            raise RuntimeError(
                "pre-existing tables disappeared: " + ",".join(sorted(missing_preserved))
            )
        after_counts = await _row_counts(conn, preserved_tables)
        if after_counts != baseline_counts:
            changed = sorted(
                table
                for table in preserved_tables
                if after_counts.get(table) != baseline_counts.get(table)
            )
            raise RuntimeError(
                "pre-existing row counts changed during migration: " + ",".join(changed)
            )


async def main() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        revision, target_present, preserved_tables, baseline_counts = await _inspect_before(engine)
        print(f"migration_pre_revision={revision}")
        print(
            "migration_pre_target_tables="
            + (",".join(sorted(target_present)) if target_present else "none")
        )
        print(f"migration_preserved_tables={len(preserved_tables)}")
        action = decide_migration_action(revision, target_present)
        print(f"migration_action={action}")

        if action == "upgrade":
            await engine.dispose()
            subprocess.run(
                ["alembic", "upgrade", TARGET_REVISION],
                cwd=BACKEND_ROOT,
                check=True,
            )
            engine = create_async_engine(settings.database_url, pool_pre_ping=True)

        await _verify_after(engine, preserved_tables, baseline_counts)
        print(f"migration_post_revision={TARGET_REVISION}")
        print("migration_schema=verified")
        print("migration_existing_data_counts=unchanged")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        exit_code = classify_failure(exc)
        print(f"migration_failure_exit_code={exit_code}", file=sys.stderr)
        raise SystemExit(exit_code) from exc
