#!/usr/bin/env python3
"""Safely reconcile the two indexes required by Alembic revision 20260925_0003.

This helper is intentionally narrow. It only repairs missing projects indexes in
an unversioned database whose remaining 0001-0004 schema contract has already
been verified. Existing-but-wrong indexes are never replaced automatically.
"""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings
from scripts import apply_cloud_domain_parity_migration as migration


BaselineRequiredIndexMismatchError = migration.BaselineRequiredIndexMismatchError
ProjectsRequiredIndexesMismatchError = migration.ProjectsRequiredIndexesMismatchError

PROJECTS_INDEX_COLUMNS = (
    ("ix_projects_status", "status"),
    ("ix_projects_name", "name"),
)

_EXPECTED_INDEX_DEFINITIONS = {
    index_name: f"CREATE INDEX {index_name} ON public.projects USING btree ({column})"
    for index_name, column in PROJECTS_INDEX_COLUMNS
}
_SIMPLE_QUOTED_IDENTIFIER = re.compile(r'"([a-z_][a-z0-9_]*)"')


def _normalize_index_definition(definition: str) -> str:
    normalized = " ".join(definition.lower().split())
    return _SIMPLE_QUOTED_IDENTIFIER.sub(r"\1", normalized)


def plan_projects_index_reconciliation(
    actual_index_defs: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    """Return only safe additive creates; reject any existing wrong definition."""

    mismatches: dict[str, str] = {}
    missing: list[tuple[str, str]] = []

    for index_name, column in PROJECTS_INDEX_COLUMNS:
        raw_definition = actual_index_defs.get(index_name)
        if raw_definition is None:
            mismatches[index_name] = "missing"
            missing.append((index_name, column))
            continue

        expected = _normalize_index_definition(_EXPECTED_INDEX_DEFINITIONS[index_name])
        actual = _normalize_index_definition(raw_definition)
        if actual != expected:
            mismatches[index_name] = "definition"

    if any(reason == "definition" for reason in mismatches.values()):
        if len(mismatches) == 2:
            raise ProjectsRequiredIndexesMismatchError(
                mismatches["ix_projects_status"],
                mismatches["ix_projects_name"],
            )
        index_name, reason = next(iter(mismatches.items()))
        raise BaselineRequiredIndexMismatchError("projects", index_name, reason)

    return tuple(missing)


async def reconcile_projects_indexes(conn: AsyncConnection) -> tuple[str, ...]:
    """Repair only missing projects indexes after a complete fail-closed preflight."""

    tables = await migration._public_tables(conn)

    # A versioned database follows the normal Alembic path and must never be
    # modified by this one-off reconciliation helper.
    if "alembic_version" in tables:
        return ()

    all_target_tables_present = migration.validate_unversioned_baseline_tables(tables)

    # This helper only addresses the already-observed production state where
    # all 0004 target tables exist. Baseline-only databases remain read-only.
    if not all_target_tables_present:
        return ()

    for table in migration.BASELINE_TABLES:
        actual_columns = await migration._table_columns(conn, table)
        actual_pk = await migration._primary_key(conn, table)
        migration.validate_baseline_table_shape(table, actual_columns, actual_pk)

        if table != "projects":
            actual_indexes = await migration._table_indexes(conn, table)
            migration.validate_baseline_required_indexes(table, actual_indexes)

    project_indexes = await migration._table_indexes(conn, "projects")
    plan = plan_projects_index_reconciliation(project_indexes)

    # No DDL is allowed until every 0004 target table passes its full schema,
    # PK, FK, and required-index verification.
    await migration._verify_schema(conn)

    if not plan:
        return ()

    for index_name, column in plan:
        await conn.execute(
            text(
                f'CREATE INDEX IF NOT EXISTS "{index_name}" '
                f'ON "projects" ("{column}")'
            )
        )

    # Re-read the catalog inside the same transaction. IF NOT EXISTS protects
    # a benign race; exact post-verification prevents it from hiding a wrong
    # same-name index.
    post_indexes = await migration._table_indexes(conn, "projects")
    remaining = plan_projects_index_reconciliation(post_indexes)
    if remaining:
        index_name, _column = remaining[0]
        raise BaselineRequiredIndexMismatchError("projects", index_name, "missing")

    return tuple(index_name for index_name, _column in plan)


async def run_reconciliation() -> tuple[str, ...]:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            return await reconcile_projects_indexes(conn)
    finally:
        await engine.dispose()
