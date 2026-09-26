#!/usr/bin/env python3
"""Read-only safety preflight for an Alembic metadata bootstrap.

This module deliberately contains no stamp/write path. It proves that an
unversioned PostgreSQL database matches the physical contract of Alembic
revisions 20260925_0001 through 20260926_0004 closely enough to *consider*
bootstrapping Alembic metadata later, after explicit approval.

The existing migration verifier already checks table presence, columns/types,
nullability, primary keys, required relationships, and the cloud-domain index.
This stronger preflight additionally checks server defaults, exact definitions
for every migration-required non-PK index, foreign-key action/deferrability/
validation semantics, and unexpected UNIQUE/CHECK/EXCLUDE constraints on the
migration-managed tables.
"""

from __future__ import annotations

import asyncio
import re
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings
from scripts import apply_cloud_domain_parity_migration as migration


EXIT_METADATA_BOOTSTRAP_APPROVAL_REQUIRED = 50
EXIT_BOOTSTRAP_DEFAULT_MISMATCH = 51
EXIT_BOOTSTRAP_INDEX_MISMATCH = 52
EXIT_BOOTSTRAP_FOREIGN_KEY_MISMATCH = 53
EXIT_BOOTSTRAP_CONSTRAINT_MISMATCH = 54

MANAGED_TABLES = migration.BASELINE_TABLES + migration.TARGET_TABLES

# Canonical server defaults expressed by Alembic revisions 0001-0004.
# Columns not listed for a table must have no server default.
EXPECTED_SERVER_DEFAULTS = {
    "google_connections": {
        "created_at": "now()",
        "updated_at": "now()",
    },
    "google_oauth_states": {"created_at": "now()"},
    "execution_logs": {"started_at": "now()"},
    "projects": {
        "status": "active",
        "created_at": "now()",
        "updated_at": "now()",
    },
    "notes": {
        "created_at": "now()",
        "updated_at": "now()",
    },
    "note_links": {},
    "habits": {
        "is_active": "true",
        "created_at": "now()",
    },
    "habit_completions": {"completed_at": "now()"},
    "shopping_lists": {"created_at": "now()"},
    "shopping_items": {
        "is_done": "false",
        "sort_order": "0",
    },
    "templates": {
        "created_at": "now()",
        "updated_at": "now()",
    },
}

EXPECTED_REQUIRED_INDEX_DEFINITIONS = {
    "google_connections": {},
    "google_oauth_states": {
        "ix_google_oauth_states_user_sub": (
            "CREATE INDEX ix_google_oauth_states_user_sub "
            "ON public.google_oauth_states USING btree (user_sub)"
        ),
        "ix_google_oauth_states_expires_at": (
            "CREATE INDEX ix_google_oauth_states_expires_at "
            "ON public.google_oauth_states USING btree (expires_at)"
        ),
    },
    "execution_logs": {
        "ix_execution_logs_request_id": (
            "CREATE INDEX ix_execution_logs_request_id "
            "ON public.execution_logs USING btree (request_id)"
        ),
        "ix_execution_logs_action_id": (
            "CREATE INDEX ix_execution_logs_action_id "
            "ON public.execution_logs USING btree (action_id)"
        ),
        "ix_execution_logs_user_sub": (
            "CREATE INDEX ix_execution_logs_user_sub "
            "ON public.execution_logs USING btree (user_sub)"
        ),
        "ix_execution_logs_action_type": (
            "CREATE INDEX ix_execution_logs_action_type "
            "ON public.execution_logs USING btree (action_type)"
        ),
        "ix_execution_logs_status": (
            "CREATE INDEX ix_execution_logs_status "
            "ON public.execution_logs USING btree (status)"
        ),
    },
    "projects": {
        "ix_projects_status": (
            "CREATE INDEX ix_projects_status ON public.projects USING btree (status)"
        ),
        "ix_projects_name": (
            "CREATE INDEX ix_projects_name ON public.projects USING btree (name)"
        ),
    },
    "notes": {},
    "note_links": {},
    "habits": {},
    "habit_completions": {
        "ix_habit_completions_habit_id_completed_at": (
            "CREATE INDEX ix_habit_completions_habit_id_completed_at "
            "ON public.habit_completions USING btree (habit_id, completed_at DESC)"
        ),
    },
    "shopping_lists": {},
    "shopping_items": {},
    "templates": {},
}

# pg_constraint action codes: a = NO ACTION. Alembic's unnamed FKs in 0004
# are non-deferrable, initially immediate, and validated at creation.
EXPECTED_FOREIGN_KEY_CONTRACTS = {
    table: set() for table in MANAGED_TABLES
}
EXPECTED_FOREIGN_KEY_CONTRACTS.update(
    {
        "note_links": {
            ("source_note_id", "notes", "id", "a", "a", False, False, True),
            ("target_note_id", "notes", "id", "a", "a", False, False, True),
        },
        "habit_completions": {
            ("habit_id", "habits", "id", "a", "a", False, False, True),
        },
        "shopping_items": {
            ("list_id", "shopping_lists", "id", "a", "a", False, False, True),
        },
    }
)

_SIMPLE_QUOTED_IDENTIFIER = re.compile(r'"([a-z_][a-z0-9_]*)"')
_ACTIVE_CAST = re.compile(r"^'active'::(?:character varying|varchar|text)$")


class MetadataBootstrapApprovalRequiredError(migration.MigrationContractError):
    """The read-only preflight passed; an explicit approval is still required."""

    def __init__(self, revision: str):
        self.revision = revision
        super().__init__(
            f"schema is stamp-ready for {revision}, but metadata bootstrap is not authorized"
        )


class BootstrapDefaultMismatchError(migration.MigrationContractError):
    def __init__(self, table: str, column: str, expected: str | None, actual: str | None):
        self.table = table
        self.column = column
        self.expected = expected
        self.actual = actual
        super().__init__(f"server default mismatch for {table}.{column}")


class BootstrapIndexMismatchError(migration.MigrationContractError):
    def __init__(self, table: str, index_name: str):
        self.table = table
        self.index_name = index_name
        super().__init__(f"required index definition mismatch for {table}.{index_name}")


class BootstrapForeignKeyMismatchError(migration.MigrationContractError):
    def __init__(self, table: str):
        self.table = table
        super().__init__(f"foreign key semantics mismatch for {table}")


class BootstrapConstraintMismatchError(migration.MigrationContractError):
    def __init__(self, table: str):
        self.table = table
        super().__init__(f"unexpected unique/check/exclusion constraint for {table}")


BOOTSTRAP_EXIT_CODES = {
    MetadataBootstrapApprovalRequiredError: EXIT_METADATA_BOOTSTRAP_APPROVAL_REQUIRED,
    BootstrapDefaultMismatchError: EXIT_BOOTSTRAP_DEFAULT_MISMATCH,
    BootstrapIndexMismatchError: EXIT_BOOTSTRAP_INDEX_MISMATCH,
    BootstrapForeignKeyMismatchError: EXIT_BOOTSTRAP_FOREIGN_KEY_MISMATCH,
    BootstrapConstraintMismatchError: EXIT_BOOTSTRAP_CONSTRAINT_MISMATCH,
}


def classify_failure(exc: BaseException) -> int:
    for error_type, exit_code in BOOTSTRAP_EXIT_CODES.items():
        if isinstance(exc, error_type):
            return exit_code
    return migration.classify_failure(exc)


def _expected_columns(table: str) -> dict[str, tuple[str, int | None, bool]]:
    if table in migration.BASELINE_EXPECTED_COLUMNS:
        return migration.BASELINE_EXPECTED_COLUMNS[table]
    return migration.EXPECTED_COLUMNS[table]


def _normalize_server_default(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().lower().split())
    if normalized in {"now()", "current_timestamp"}:
        return "now()"
    if normalized == "'active'" or _ACTIVE_CAST.fullmatch(normalized):
        return "active"
    if normalized in {"true", "false", "0"}:
        return normalized
    return normalized


def validate_server_defaults(table: str, actual_defaults: dict[str, str | None]) -> None:
    expected_columns = _expected_columns(table)
    expected_defaults = EXPECTED_SERVER_DEFAULTS[table]

    all_columns = set(expected_columns)
    if set(actual_defaults) != all_columns:
        differing = sorted(set(actual_defaults) ^ all_columns)
        column = differing[0] if differing else "<unknown>"
        raise BootstrapDefaultMismatchError(
            table,
            column,
            expected_defaults.get(column),
            actual_defaults.get(column),
        )

    for column in expected_columns:
        expected = expected_defaults.get(column)
        actual = _normalize_server_default(actual_defaults[column])
        if actual != expected:
            raise BootstrapDefaultMismatchError(table, column, expected, actual)


def _normalize_index_definition(definition: str) -> str:
    normalized = " ".join(definition.strip().lower().split())
    return _SIMPLE_QUOTED_IDENTIFIER.sub(r"\1", normalized)


def validate_required_indexes(table: str, actual_index_defs: dict[str, str]) -> None:
    for index_name, expected_definition in EXPECTED_REQUIRED_INDEX_DEFINITIONS[table].items():
        actual_definition = actual_index_defs.get(index_name)
        if actual_definition is None:
            raise BootstrapIndexMismatchError(table, index_name)
        if _normalize_index_definition(actual_definition) != _normalize_index_definition(
            expected_definition
        ):
            raise BootstrapIndexMismatchError(table, index_name)


def validate_foreign_key_contracts(
    table: str,
    actual_contracts: set[tuple[str, str, str, str, str, bool, bool, bool]],
) -> None:
    if actual_contracts != EXPECTED_FOREIGN_KEY_CONTRACTS[table]:
        raise BootstrapForeignKeyMismatchError(table)


def validate_no_extra_constraints(
    table: str,
    constraints: set[tuple[str, str]],
) -> None:
    if constraints:
        raise BootstrapConstraintMismatchError(table)


async def _column_defaults(
    conn: AsyncConnection,
    table: str,
) -> dict[str, str | None]:
    result = await conn.execute(
        text(
            "SELECT column_name, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table "
            "ORDER BY ordinal_position"
        ),
        {"table": table},
    )
    return {
        str(row.column_name): (
            str(row.column_default) if row.column_default is not None else None
        )
        for row in result
    }


async def _foreign_key_contracts(
    conn: AsyncConnection,
    table: str,
) -> set[tuple[str, str, str, str, str, bool, bool, bool]]:
    result = await conn.execute(
        text(
            "SELECT la.attname AS local_column, ft.relname AS foreign_table, "
            "fa.attname AS foreign_column, c.confupdtype AS update_action, "
            "c.confdeltype AS delete_action, c.condeferrable, c.condeferred, "
            "c.convalidated "
            "FROM pg_constraint c "
            "JOIN LATERAL unnest(c.conkey, c.confkey) "
            "AS k(local_attnum, foreign_attnum) ON true "
            "JOIN pg_attribute la "
            "ON la.attrelid = c.conrelid AND la.attnum = k.local_attnum "
            "JOIN pg_class ft ON ft.oid = c.confrelid "
            "JOIN pg_attribute fa "
            "ON fa.attrelid = c.confrelid AND fa.attnum = k.foreign_attnum "
            "WHERE c.conrelid = to_regclass(:qualified_table) AND c.contype = 'f'"
        ),
        {"qualified_table": f"public.{table}"},
    )
    return {
        (
            str(row.local_column),
            str(row.foreign_table),
            str(row.foreign_column),
            str(row.update_action),
            str(row.delete_action),
            bool(row.condeferrable),
            bool(row.condeferred),
            bool(row.convalidated),
        )
        for row in result
    }


async def _extra_constraints(
    conn: AsyncConnection,
    table: str,
) -> set[tuple[str, str]]:
    result = await conn.execute(
        text(
            "SELECT conname, contype "
            "FROM pg_constraint "
            "WHERE conrelid = to_regclass(:qualified_table) "
            "AND contype IN ('u', 'c', 'x') "
            "ORDER BY conname"
        ),
        {"qualified_table": f"public.{table}"},
    )
    return {(str(row.conname), str(row.contype)) for row in result}


async def _verify_server_defaults(conn: AsyncConnection) -> None:
    for table in MANAGED_TABLES:
        validate_server_defaults(table, await _column_defaults(conn, table))


async def _verify_required_indexes(conn: AsyncConnection) -> None:
    for table in MANAGED_TABLES:
        validate_required_indexes(table, await migration._table_indexes(conn, table))


async def _verify_foreign_key_semantics(conn: AsyncConnection) -> None:
    for table in MANAGED_TABLES:
        validate_foreign_key_contracts(table, await _foreign_key_contracts(conn, table))


async def _verify_extra_constraints(conn: AsyncConnection) -> None:
    for table in MANAGED_TABLES:
        validate_no_extra_constraints(table, await _extra_constraints(conn, table))


async def inspect_bootstrap_readiness(conn: AsyncConnection) -> str | None:
    """Return target revision only when an unversioned DB passes every read-only guard.

    A database that already has Alembic metadata returns None and follows the normal
    migration path. No DDL/DML is issued by this function.
    """

    tables = await migration._public_tables(conn)
    if "alembic_version" in tables:
        return None

    full_target_schema = migration.validate_unversioned_baseline_tables(tables)
    await migration._verify_unversioned_baseline_schema(conn)
    if not full_target_schema:
        raise migration.BaselineVerifiedWithoutVersionError(
            "baseline-only unversioned database is not eligible for target metadata bootstrap"
        )

    await migration._verify_schema(conn)
    await _verify_server_defaults(conn)
    await _verify_required_indexes(conn)
    await _verify_foreign_key_semantics(conn)
    await _verify_extra_constraints(conn)
    return migration.TARGET_REVISION


async def run_preflight() -> str | None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            return await inspect_bootstrap_readiness(conn)
    finally:
        await engine.dispose()


async def main() -> None:
    revision = await run_preflight()
    if revision is None:
        print("metadata_bootstrap_preflight=not_required")
        return
    print(f"metadata_bootstrap_preflight=verified:{revision}")
    raise MetadataBootstrapApprovalRequiredError(revision)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        exit_code = classify_failure(exc)
        print(f"metadata_bootstrap_preflight_exit_code={exit_code}", file=sys.stderr)
        raise SystemExit(exit_code) from exc
