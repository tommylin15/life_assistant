#!/usr/bin/env python3
"""Guarded one-time Alembic metadata bootstrap for verified physical schema.

This module never creates or changes application tables. It may create only the
standard public.alembic_version metadata table and insert the already-verified
target revision. The write is revision-scoped, explicitly approved by an
environment variable, serialized with the same advisory-lock id used by
Alembic, and performed in one transaction after re-running the full read-only
metadata bootstrap preflight.
"""

from __future__ import annotations

import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import settings
from scripts import apply_cloud_domain_parity_migration as migration
from scripts import preflight_alembic_metadata_bootstrap as metadata_preflight


APPROVAL_ENV = "ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION"
MIGRATION_LOCK_ID = 7520250925


def require_approved_revision(approved_revision: str | None) -> None:
    """Require approval for exactly the physical schema revision being stamped."""

    if approved_revision != migration.TARGET_REVISION:
        raise metadata_preflight.MetadataBootstrapApprovalRequiredError(
            migration.TARGET_REVISION
        )


async def bootstrap_alembic_metadata(
    conn: AsyncConnection,
    approved_revision: str | None,
) -> bool:
    """Create only Alembic metadata after the full physical contract is verified.

    Returns True when metadata is created. An already-versioned database at the
    target revision is an idempotent no-op. Any other state fails closed.
    """

    require_approved_revision(approved_revision)

    # Serialize this one-time metadata write with normal Alembic migrations.
    # pg_advisory_xact_lock is automatically released at transaction end.
    await conn.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": MIGRATION_LOCK_ID},
    )

    tables = await migration._public_tables(conn)
    if "alembic_version" in tables:
        current_revision = await migration._current_revision(conn)
        migration.require_target_revision(current_revision)
        return False

    # Re-run the complete read-only preflight while holding the migration lock
    # so the metadata write cannot rely on stale schema evidence.
    ready_revision = await metadata_preflight.inspect_bootstrap_readiness(conn)
    if ready_revision != migration.TARGET_REVISION:
        raise metadata_preflight.MetadataBootstrapApprovalRequiredError(
            migration.TARGET_REVISION
        )

    await conn.execute(
        text(
            "CREATE TABLE public.alembic_version ("
            "version_num VARCHAR(32) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        )
    )
    await conn.execute(
        text(
            "INSERT INTO public.alembic_version (version_num) "
            "VALUES (:revision)"
        ),
        {"revision": ready_revision},
    )

    current_revision = await migration._current_revision(conn)
    migration.require_target_revision(current_revision)
    return True


async def run_bootstrap(approved_revision: str | None = None) -> bool:
    """Run the guarded bootstrap in one transaction.

    When approved_revision is omitted, approval is read from the deployment
    environment. The explicit parameter exists for deterministic tests and
    controlled tooling, but must still exactly match TARGET_REVISION.
    """

    approval = (
        approved_revision
        if approved_revision is not None
        else os.getenv(APPROVAL_ENV)
    )
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            return await bootstrap_alembic_metadata(conn, approval)
    finally:
        await engine.dispose()
