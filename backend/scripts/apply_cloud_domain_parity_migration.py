#!/usr/bin/env python3
"""Apply and verify the additive Cloud Domain Parity migration in dev-test.

This runner deliberately fails closed when migration metadata or schema state is
ambiguous. It never stamps, drops, truncates, or rewrites data to hide drift.
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
UNVERSIONED_TARGET_TABLE_BITS = {
    "notes": 1,
    "note_links": 2,
    "habits": 4,
    "habit_completions": 8,
    "shopping_lists": 16,
    "shopping_items": 32,
    "templates": 64,
}
EXIT_UNVERSIONED_TARGETS_BASE = 64

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

# These are the tables created by Alembic revisions 0001-0003. When an
# existing database has no alembic_version table, they are verified read-only
# before any metadata bootstrap can even be considered.
BASELINE_TABLES = (
    "google_connections",
    "google_oauth_states",
    "execution_logs",
    "projects",
)

BASELINE_EXPECTED_COLUMNS = {
    "google_connections": {
        "user_sub": ("character varying", 255, False),
        "email": ("character varying", 320, False),
        "encrypted_access_token": ("text", None, True),
        "encrypted_refresh_token": ("text", None, True),
        "scopes": ("text", None, False),
        "access_token_expires_at": ("timestamp with time zone", None, True),
        "created_at": ("timestamp with time zone", None, False),
        "updated_at": ("timestamp with time zone", None, False),
    },
    "google_oauth_states": {
        "state_hash": ("character varying", 64, False),
        "user_sub": ("character varying", 255, False),
        "email": ("character varying", 320, False),
        "services": ("character varying", 255, False),
        "expires_at": ("timestamp with time zone", None, False),
        "created_at": ("timestamp with time zone", None, False),
    },
    "execution_logs": {
        "id": ("character varying", 36, False),
        "request_id": ("character varying", 128, False),
        "action_id": ("character varying", 128, True),
        "user_sub": ("character varying", 255, False),
        "action_type": ("character varying", 128, False),
        "entity_type": ("character varying", 64, True),
        "entity_id": ("character varying", 255, True),
        "provider": ("character varying", 64, True),
        "status": ("character varying", 32, False),
        "result": ("character varying", 64, True),
        "error_category": ("character varying", 128, True),
        "summary": ("text", None, True),
        "started_at": ("timestamp with time zone", None, False),
        "finished_at": ("timestamp with time zone", None, True),
    },
    "projects": {
        "id": ("character varying", 36, False),
        "name": ("character varying", 500, False),
        "summary": ("text", None, True),
        "status": ("character varying", 32, False),
        "created_at": ("timestamp with time zone", None, False),
        "updated_at": ("timestamp with time zone", None, False),
    },
}

BASELINE_EXPECTED_PRIMARY_KEYS = {
    "google_connections": ("user_sub",),
    "google_oauth_states": ("state_hash",),
    "execution_logs": ("id",),
    "projects": ("id",),
}

BASELINE_REQUIRED_INDEXES = {
    "google_connections": {},
    "google_oauth_states": {
        "ix_google_oauth_states_user_sub": "(user_sub)",
        "ix_google_oauth_states_expires_at": "(expires_at)",
    },
    "execution_logs": {
        "ix_execution_logs_request_id": "(request_id)",
        "ix_execution_logs_action_id": "(action_id)",
        "ix_execution_logs_user_sub": "(user_sub)",
        "ix_execution_logs_action_type": "(action_type)",
        "ix_execution_logs_status": "(status)",
    },
    "projects": {
        "ix_projects_status": "(status)",
        "ix_projects_name": "(name)",
    },
}

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Cloud Run execution describe exposes the container exit code even when the
# deploy service account cannot read Cloud Logging. Keep these stable and
# non-secret so deployment evidence can distinguish failure classes.
EXIT_DATABASE = 20
EXIT_REVISION_TABLE_MISSING = 21
EXIT_ALEMBIC = 22
EXIT_PRECREATED_DRIFT = 23
EXIT_SCHEMA_MISMATCH = 24
EXIT_PRESERVED_DATA = 25
EXIT_REVISION_ROW_COUNT = 26
EXIT_UNEXPECTED_CURRENT_REVISION = 27
EXIT_POST_MIGRATION_REVISION = 28
EXIT_UNEXPECTED = 29
EXIT_BASELINE_TABLES_MISSING = 30
EXIT_BASELINE_SCHEMA_MISMATCH = 31
EXIT_BASELINE_VERIFIED_UNVERSIONED = 32
# Backward-compatible names for earlier evidence/documents.
EXIT_REVISION = EXIT_REVISION_TABLE_MISSING
EXIT_CONTRACT = EXIT_REVISION_TABLE_MISSING


class MigrationContractError(RuntimeError):
    """Base class for migration contract validation failures."""


class RevisionValidationError(MigrationContractError):
    """Base class for Alembic revision-state validation failures."""


class RevisionTableMissingError(RevisionValidationError):
    """The public alembic_version table does not exist."""


class RevisionRowCountError(RevisionValidationError):
    """The alembic_version table does not contain exactly one row."""


class UnexpectedCurrentRevisionError(RevisionValidationError):
    """The current revision is not one of the expected migration states."""


class PostMigrationRevisionMismatchError(RevisionValidationError):
    """The revision after migration is not the target revision."""


class PrecreatedDriftError(MigrationContractError):
    """Target tables exist before the migration revision that should create them."""


class UnversionedTargetTablesPresentError(PrecreatedDriftError):
    """Encode the exact target-table subset present in an unversioned database."""

    def __init__(self, tables: set[str]):
        self.tables = set(tables)
        super().__init__(
            "migration drift: target tables already exist in unversioned database: "
            + ",".join(sorted(self.tables))
        )


class SchemaMismatchError(MigrationContractError):
    """Target table, column, key, or index shape differs from the contract."""


class PreservedDataMismatchError(MigrationContractError):
    """Pre-existing tables or row counts changed during the additive migration."""


class BaselineTablesMissingError(MigrationContractError):
    """An unversioned database is missing tables required by revisions 0001-0003."""


class BaselineSchemaMismatchError(MigrationContractError):
    """An unversioned database does not match the expected 0001-0003 schema."""


class BaselineVerifiedWithoutVersionError(MigrationContractError):
    """The baseline matches, but Alembic metadata is intentionally still absent."""


def encode_unversioned_target_tables(tables: set[str]) -> int:
    present = set(tables)
    unknown = present - set(UNVERSIONED_TARGET_TABLE_BITS)
    if unknown:
        raise ValueError(f"unknown target tables for exit-code bitmap: {sorted(unknown)}")
    mask = sum(UNVERSIONED_TARGET_TABLE_BITS[table] for table in present)
    return EXIT_UNVERSIONED_TARGETS_BASE + mask


def classify_failure(exc: BaseException) -> int:
    if isinstance(exc, subprocess.CalledProcessError):
        return EXIT_ALEMBIC
    if isinstance(exc, SQLAlchemyError):
        return EXIT_DATABASE
    if isinstance(exc, BaselineTablesMissingError):
        return EXIT_BASELINE_TABLES_MISSING
    if isinstance(exc, BaselineSchemaMismatchError):
        return EXIT_BASELINE_SCHEMA_MISMATCH
    if isinstance(exc, BaselineVerifiedWithoutVersionError):
        return EXIT_BASELINE_VERIFIED_UNVERSIONED
    if isinstance(exc, RevisionTableMissingError):
        return EXIT_REVISION_TABLE_MISSING
    if isinstance(exc, RevisionRowCountError):
        return EXIT_REVISION_ROW_COUNT
    if isinstance(exc, UnexpectedCurrentRevisionError):
        return EXIT_UNEXPECTED_CURRENT_REVISION
    if isinstance(exc, PostMigrationRevisionMismatchError):
        return EXIT_POST_MIGRATION_REVISION
    if isinstance(exc, RevisionValidationError):
        return EXIT_REVISION_TABLE_MISSING
    if isinstance(exc, UnversionedTargetTablesPresentError):
        return encode_unversioned_target_tables(exc.tables)
    if isinstance(exc, PrecreatedDriftError):
        return EXIT_PRECREATED_DRIFT
    if isinstance(exc, SchemaMismatchError):
        return EXIT_SCHEMA_MISMATCH
    if isinstance(exc, PreservedDataMismatchError):
        return EXIT_PRESERVED_DATA
    return EXIT_UNEXPECTED


def validate_revision_state(table_exists: bool, rows: list[object]) -> str:
    if not table_exists:
        raise RevisionTableMissingError("alembic_version table is missing")
    if len(rows) != 1:
        raise RevisionRowCountError(f"expected one alembic_version row, found {len(rows)}")
    return str(rows[0])


def require_target_revision(revision: str) -> None:
    if revision != TARGET_REVISION:
        raise PostMigrationRevisionMismatchError(
            f"post-migration revision mismatch: {revision}; expected {TARGET_REVISION}"
        )


def validate_unversioned_baseline_tables(tables: set[str]) -> None:
    present = set(tables)
    target_present = set(TARGET_TABLES) & present
    if target_present:
        raise UnversionedTargetTablesPresentError(target_present)
    missing = set(BASELINE_TABLES) - present
    if missing:
        raise BaselineTablesMissingError(
            "missing baseline tables in unversioned database: "
            + ",".join(sorted(missing))
        )


def validate_baseline_table_shape(
    table: str,
    actual_columns: dict[str, tuple[str, int | None, bool]],
    actual_pk: tuple[str, ...],
) -> None:
    expected_columns = BASELINE_EXPECTED_COLUMNS[table]
    expected_pk = BASELINE_EXPECTED_PRIMARY_KEYS[table]
    if actual_columns != expected_columns or actual_pk != expected_pk:
        raise BaselineSchemaMismatchError(
            f"baseline schema mismatch for {table}: columns/type/nullability/primary key differ"
        )


def validate_baseline_required_indexes(
    table: str,
    actual_index_defs: dict[str, str],
) -> None:
    for index_name, required_fragment in BASELINE_REQUIRED_INDEXES[table].items():
        normalized = " ".join(actual_index_defs.get(index_name, "").lower().split())
        if required_fragment.lower() not in normalized:
            raise BaselineSchemaMismatchError(
                f"baseline index mismatch for {table}: {index_name} missing or mismatched"
            )


def decide_migration_action(current_revision: str, target_tables_present: set[str]) -> str:
    present = set(target_tables_present)
    expected = set(TARGET_TABLES)
    if current_revision == PREVIOUS_REVISION:
        if present:
            names = ",".join(sorted(present))
            raise PrecreatedDriftError(
                "migration drift: target tables already exist before Alembic "
                f"{TARGET_REVISION}: {names}"
            )
        return "upgrade"
    if current_revision == TARGET_REVISION:
        missing = expected - present
        if missing:
            raise SchemaMismatchError(
                "missing target tables at applied revision "
                f"{TARGET_REVISION}: {','.join(sorted(missing))}"
            )
        return "verify"
    raise UnexpectedCurrentRevisionError(
        f"unexpected alembic revision: {current_revision or '<missing>'}; "
        f"expected {PREVIOUS_REVISION} or {TARGET_REVISION}"
    )


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


async def _current_revision(conn: AsyncConnection) -> str:
    exists = await conn.scalar(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
    if not exists:
        return validate_revision_state(False, [])
    rows = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalars().all()
    return validate_revision_state(True, list(rows))


async def _row_counts(conn: AsyncConnection, tables: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in sorted(tables):
        if not _SAFE_IDENTIFIER.fullmatch(table):
            raise PreservedDataMismatchError(f"unsafe table identifier in catalog: {table!r}")
        value = await conn.scalar(text(f'SELECT count(*) FROM "{table}"'))
        counts[table] = int(value or 0)
    return counts


async def _table_columns(
    conn: AsyncConnection,
    table: str,
) -> dict[str, tuple[str, int | None, bool]]:
    result = await conn.execute(
        text(
            "SELECT column_name, data_type, character_maximum_length, is_nullable "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table "
            "ORDER BY ordinal_position"
        ),
        {"table": table},
    )
    return {
        str(row.column_name): (
            str(row.data_type),
            int(row.character_maximum_length) if row.character_maximum_length is not None else None,
            str(row.is_nullable) == "YES",
        )
        for row in result
    }


async def _verify_columns(conn: AsyncConnection, table: str) -> None:
    actual = await _table_columns(conn, table)
    expected = EXPECTED_COLUMNS[table]
    if actual != expected:
        raise SchemaMismatchError(f"schema mismatch for {table}: columns/nullability/type differ")


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


async def _table_indexes(conn: AsyncConnection, table: str) -> dict[str, str]:
    result = await conn.execute(
        text(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename = :table"
        ),
        {"table": table},
    )
    return {str(row.indexname): str(row.indexdef) for row in result}


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


async def _verify_unversioned_baseline_schema(conn: AsyncConnection) -> None:
    for table in BASELINE_TABLES:
        columns = await _table_columns(conn, table)
        primary_key = await _primary_key(conn, table)
        validate_baseline_table_shape(table, columns, primary_key)
        indexes = await _table_indexes(conn, table)
        validate_baseline_required_indexes(table, indexes)


async def _verify_schema(conn: AsyncConnection) -> None:
    tables = await _public_tables(conn)
    missing = set(TARGET_TABLES) - tables
    if missing:
        raise SchemaMismatchError(f"missing target tables: {','.join(sorted(missing))}")

    for table in TARGET_TABLES:
        await _verify_columns(conn, table)
        actual_pk = await _primary_key(conn, table)
        if actual_pk != EXPECTED_PRIMARY_KEYS[table]:
            raise SchemaMismatchError(f"primary key mismatch for {table}: {actual_pk}")

    for table, expected in EXPECTED_FOREIGN_KEYS.items():
        actual = await _foreign_keys(conn, table)
        if actual != expected:
            raise SchemaMismatchError(f"foreign key mismatch for {table}: {sorted(actual)}")

    index_defs = await _table_indexes(conn, "habit_completions")
    normalized = " ".join(
        index_defs.get("ix_habit_completions_habit_id_completed_at", "").lower().split()
    )
    if "(habit_id, completed_at desc)" not in normalized:
        raise SchemaMismatchError("habit completion descending index is missing or mismatched")


async def _inspect_before(engine) -> tuple[str, set[str], set[str], dict[str, int]]:
    async with engine.connect() as conn:
        tables = await _public_tables(conn)
        if "alembic_version" not in tables:
            validate_unversioned_baseline_tables(tables)
            await _verify_unversioned_baseline_schema(conn)
            raise BaselineVerifiedWithoutVersionError(
                "baseline schema verified but alembic_version table is missing"
            )

        revision = await _current_revision(conn)
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
        require_target_revision(revision)
        await _verify_schema(conn)
        tables = await _public_tables(conn)
        missing_preserved = preserved_tables - tables
        if missing_preserved:
            raise PreservedDataMismatchError(
                "pre-existing tables disappeared: " + ",".join(sorted(missing_preserved))
            )
        after_counts = await _row_counts(conn, preserved_tables)
        if after_counts != baseline_counts:
            changed = sorted(
                table
                for table in preserved_tables
                if after_counts.get(table) != baseline_counts.get(table)
            )
            raise PreservedDataMismatchError(
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
