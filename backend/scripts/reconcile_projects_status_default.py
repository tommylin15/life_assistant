#!/usr/bin/env python3
"""Safely reconcile the diagnosed missing projects.status server default.

This helper is intentionally narrow. It only adds the Alembic-required
DEFAULT 'active' to projects.status when the production database is unversioned,
the full 0001-0004 physical contract is otherwise verified, and the current
projects.status default is missing. An existing non-matching default is never
changed automatically.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings
from scripts import apply_cloud_domain_parity_migration as migration
from scripts import preflight_alembic_metadata_bootstrap as metadata_preflight


EXPECTED_PROJECTS_STATUS_DEFAULT = "active"


def plan_projects_status_default_reconciliation(actual_default: str | None) -> bool:
    """Return True only for the diagnosed missing-default state.

    Correct existing defaults are a no-op. Any different non-null default is
    fail-closed and must be investigated rather than overwritten.
    """

    normalized = metadata_preflight._normalize_server_default(actual_default)
    if normalized is None:
        return True
    if normalized == EXPECTED_PROJECTS_STATUS_DEFAULT:
        return False
    raise metadata_preflight.BootstrapDefaultMismatchError(
        "projects",
        "status",
        EXPECTED_PROJECTS_STATUS_DEFAULT,
        normalized,
    )


async def reconcile_projects_status_default(conn: AsyncConnection) -> bool:
    """Repair only a missing projects.status default after fail-closed guards."""

    tables = await migration._public_tables(conn)

    # A versioned database follows normal Alembic and must never be touched by
    # this one-off reconciliation helper.
    if "alembic_version" in tables:
        return False

    all_target_tables_present = migration.validate_unversioned_baseline_tables(tables)
    if not all_target_tables_present:
        return False

    # Structural verification happens before any DDL.
    await migration._verify_unversioned_baseline_schema(conn)
    await migration._verify_schema(conn)

    # Verify the stronger bootstrap contract that is independent of the one
    # diagnosed default. This prevents a write when some other hidden mismatch
    # already exists.
    await metadata_preflight._verify_required_indexes(conn)
    await metadata_preflight._verify_foreign_key_semantics(conn)
    await metadata_preflight._verify_extra_constraints(conn)

    should_repair = False
    for table in metadata_preflight.MANAGED_TABLES:
        actual_defaults = await metadata_preflight._column_defaults(conn, table)
        if table != "projects":
            metadata_preflight.validate_server_defaults(table, actual_defaults)
            continue

        should_repair = plan_projects_status_default_reconciliation(
            actual_defaults["status"]
        )

        # Validate every other projects default while temporarily substituting
        # the known expected status value. No database write occurs here.
        verification_defaults = dict(actual_defaults)
        verification_defaults["status"] = "'active'"
        metadata_preflight.validate_server_defaults("projects", verification_defaults)

    if not should_repair:
        return False

    await conn.execute(
        text(
            'ALTER TABLE "projects" '
            'ALTER COLUMN "status" SET DEFAULT \'active\''
        )
    )

    # Re-read the catalog in the same transaction and verify the complete
    # projects default contract after the repair.
    post_defaults = await metadata_preflight._column_defaults(conn, "projects")
    metadata_preflight.validate_server_defaults("projects", post_defaults)
    return True


async def run_reconciliation() -> bool:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            return await reconcile_projects_status_default(conn)
    finally:
        await engine.dispose()
