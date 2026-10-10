#!/usr/bin/env python3
"""Release entrypoint for guarded schema reconciliation and Alembic upgrade.

The historical 0004 reconciliation/bootstrap path is preserved for databases
that still need it. Once 0004 is verified, normal Alembic advances to the
current additive release head. Already-current databases are a verified no-op.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from scripts import apply_cloud_domain_parity_migration as migration
from scripts import bootstrap_alembic_metadata as metadata_bootstrap
from scripts import diagnose_note_links_foreign_keys as note_links_fk_diagnosis
from scripts import preflight_alembic_metadata_bootstrap as metadata_preflight
from scripts.reconcile_projects_indexes import (
    run_reconciliation as run_projects_index_reconciliation,
)
from scripts.reconcile_projects_status_default import (
    run_reconciliation as run_projects_status_default_reconciliation,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_RELEASE_REVISION = "20261010_0015"
LEGACY_DIRECT_RELEASE_REVISIONS = {
    "20261009_0014",
    "20260927_0005",
    "20260928_0006",
    "20260930_0007",
    "20261002_0009",
    "20261007_0010",
    "20261009_0011",
    "20261009_0012",
    "20261009_0013",
}
RELEASE_TARGET_REVISION = "20261010_0016"
EXIT_RELEASE_REVISION = 60
EXIT_RELEASE_ALEMBIC = 61
EXIT_RELEASE_MISSING_TABLES = 62
EXIT_RELEASE_MISSING_TASK_COLUMNS = 63
EXIT_RELEASE_TARGET_REVISION = 64
EXIT_RELEASE_UNEXPECTED_PRE_REVISION = 65
EXIT_RELEASE_VERSION_TABLE = 66
EXIT_RELEASE_REVISION_ROW_COUNT = 67
RELEASE_REVISION_EXIT_CODES = {
    "generic": EXIT_RELEASE_REVISION,
    "missing_tables": EXIT_RELEASE_MISSING_TABLES,
    "missing_task_columns": EXIT_RELEASE_MISSING_TASK_COLUMNS,
    "target_revision": EXIT_RELEASE_TARGET_REVISION,
    "unexpected_pre_revision": EXIT_RELEASE_UNEXPECTED_PRE_REVISION,
    "version_table": EXIT_RELEASE_VERSION_TABLE,
    "revision_row_count": EXIT_RELEASE_REVISION_ROW_COUNT,
}
RELEASE_REQUIRED_TABLES = {
    "tasks",
    "checklist_items",
    "tags",
    "entity_tags",
    "reminders",
    "legacy_attachments",
    "calendar_event_refs",
    "gmail_refs",
    "legacy_activity_logs",
    "legacy_key_value_state",
    "legacy_migration_rows",
    "drive_workspaces",
    "drive_documents",
    "drive_workspace_documents",
    "project_drive_documents",
    "note_drive_documents",
    "drive_enrichment_settings",
    "drive_document_enrichment_runs",
    "drive_note_link_suggestions",
    "ai_provider_preferences",
    "free_event_sources",
    "free_event_organizers",
    "free_events",
    "free_event_sessions",
    "free_event_registration_opportunities",
    "free_event_evidence",
    "free_event_ingestion_leases",
    "free_event_source_observations",
    "free_event_candidate_queue",
    "curated_activities",
    "curated_personal_actions",
    "feature_rollouts",
    "user_ui_preferences",
    "life_ai_policy",
}
RELEASE_REQUIRED_TASK_COLUMNS = {"source_type", "source_ref", "completed_at", "deleted_at", "user_sub"}

NOTE_LINKS_FK_DIAGNOSTIC_EXIT_CODES = {
    "both_missing": 1,
    "source_missing": 2,
    "target_missing": 3,
    "driver_action_representation": 4,
    "source_update_action": 5,
    "target_update_action": 6,
    "both_update_action": 7,
    "source_delete_action": 8,
    "target_delete_action": 9,
    "both_delete_action": 10,
    "source_deferrable": 11,
    "target_deferrable": 12,
    "both_deferrable": 13,
    "source_initially_deferred": 14,
    "target_initially_deferred": 15,
    "both_initially_deferred": 16,
    "source_validation": 17,
    "target_validation": 18,
    "both_validation": 19,
}
EXIT_PROJECTS_STATUS_DEFAULT_MISSING = 250
EXIT_PROJECTS_STATUS_DEFAULT_VALUE_MISMATCH = 251
FOREIGN_KEY_MISMATCH_EXIT_CODES = {
    "note_links": 252,
    "habit_completions": 253,
    "shopping_items": 254,
}
EXIT_UNEXPECTED_FOREIGN_KEY_TABLE = 255


class ReleaseRevisionError(RuntimeError):
    def __init__(self, message: str, *, reason: str = "generic") -> None:
        super().__init__(message)
        self.reason = reason


class ReleaseAlembicError(RuntimeError):
    pass


def classify_failure(exc: BaseException) -> int:
    if isinstance(exc, ReleaseRevisionError):
        return RELEASE_REVISION_EXIT_CODES.get(exc.reason, EXIT_RELEASE_REVISION)
    if isinstance(exc, ReleaseAlembicError):
        return EXIT_RELEASE_ALEMBIC
    if isinstance(exc, metadata_preflight.MetadataBootstrapApprovalRequiredError):
        return metadata_preflight.EXIT_METADATA_BOOTSTRAP_APPROVAL_REQUIRED
    if isinstance(exc, note_links_fk_diagnosis.NoteLinksForeignKeyDiagnosisError):
        return NOTE_LINKS_FK_DIAGNOSTIC_EXIT_CODES.get(
            exc.reason,
            FOREIGN_KEY_MISMATCH_EXIT_CODES["note_links"],
        )
    if (
        isinstance(exc, metadata_preflight.BootstrapDefaultMismatchError)
        and exc.table == "projects"
        and exc.column == "status"
    ):
        if exc.expected is not None and exc.actual is None:
            return EXIT_PROJECTS_STATUS_DEFAULT_MISSING
        if exc.actual is not None and exc.actual != exc.expected:
            return EXIT_PROJECTS_STATUS_DEFAULT_VALUE_MISMATCH
    if isinstance(exc, metadata_preflight.BootstrapForeignKeyMismatchError):
        return FOREIGN_KEY_MISMATCH_EXIT_CODES.get(
            exc.table,
            EXIT_UNEXPECTED_FOREIGN_KEY_TABLE,
        )
    return metadata_preflight.classify_failure(exc)


async def _current_revision() -> str | None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            )
            if not exists:
                return None
            rows = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all()
            if len(rows) != 1:
                raise ReleaseRevisionError(
                    f"expected one alembic revision row, found {len(rows)}",
                    reason="revision_row_count",
                )
            return str(rows[0])
    finally:
        await engine.dispose()


async def _verify_release_revision() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            )
            if not exists:
                raise ReleaseRevisionError(
                    "release alembic_version table is missing",
                    reason="version_table",
                )
            rows = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalars().all()
            if len(rows) != 1 or str(rows[0]) != RELEASE_TARGET_REVISION:
                actual = str(rows[0]) if len(rows) == 1 else f"row-count:{len(rows)}"
                raise ReleaseRevisionError(
                    f"release revision mismatch: {actual}; expected {RELEASE_TARGET_REVISION}",
                    reason="target_revision",
                )
            tables = set(
                str(value)
                for value in (
                    await conn.execute(
                        text(
                            "SELECT tablename FROM pg_catalog.pg_tables "
                            "WHERE schemaname='public'"
                        )
                    )
                ).scalars().all()
            )
            missing_tables = RELEASE_REQUIRED_TABLES - tables
            if missing_tables:
                raise ReleaseRevisionError(
                    "release schema missing tables: " + ",".join(sorted(missing_tables)),
                    reason="missing_tables",
                )
            task_columns = set(
                str(value)
                for value in (
                    await conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema='public' AND table_name='tasks'"
                        )
                    )
                ).scalars().all()
            )
            missing_columns = RELEASE_REQUIRED_TASK_COLUMNS - task_columns
            if missing_columns:
                raise ReleaseRevisionError(
                    "release tasks schema missing columns: "
                    + ",".join(sorted(missing_columns)),
                    reason="missing_task_columns",
                )
    finally:
        await engine.dispose()


def _upgrade_release_head() -> None:
    try:
        subprocess.run(
            ["alembic", "upgrade", RELEASE_TARGET_REVISION],
            cwd=BACKEND_ROOT,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ReleaseAlembicError("release Alembic upgrade failed") from exc


async def _ensure_historical_0004() -> None:
    repaired_indexes = await run_projects_index_reconciliation()
    print(
        "migration_reconciled_projects_indexes="
        + (",".join(repaired_indexes) if repaired_indexes else "none")
    )

    repaired_status_default = await run_projects_status_default_reconciliation()
    print(
        "migration_reconciled_projects_status_default="
        + ("active" if repaired_status_default else "none")
    )

    await note_links_fk_diagnosis.run_diagnosis()

    ready_revision = await metadata_preflight.run_preflight()
    if ready_revision is not None:
        print(f"metadata_bootstrap_preflight=verified:{ready_revision}")
        bootstrapped = await metadata_bootstrap.run_bootstrap()
        print(
            "metadata_bootstrap_applied="
            + (ready_revision if bootstrapped else "already-versioned")
        )

    await migration.main()


async def main() -> None:
    current = await _current_revision()
    print(f"release_pre_revision={current or 'unversioned'}")

    if current == RELEASE_TARGET_REVISION:
        print("release_schema_action=verify-current")
        await _verify_release_revision()
        print(f"release_post_revision={RELEASE_TARGET_REVISION}")
        return

    historical_revisions = {
        None,
        migration.PREVIOUS_REVISION,
        migration.TARGET_REVISION,
    }
    if current in historical_revisions:
        await _ensure_historical_0004()
        print(f"release_base_revision={migration.TARGET_REVISION}")
    elif current == PREVIOUS_RELEASE_REVISION or current in LEGACY_DIRECT_RELEASE_REVISIONS:
        print(f"release_base_revision={current}")
    else:
        accepted_direct = ", ".join(
            sorted({PREVIOUS_RELEASE_REVISION, *LEGACY_DIRECT_RELEASE_REVISIONS})
        )
        raise ReleaseRevisionError(
            f"unexpected release pre-revision: {current}; expected unversioned, "
            f"{migration.PREVIOUS_REVISION}, {migration.TARGET_REVISION}, "
            f"one of [{accepted_direct}], or {RELEASE_TARGET_REVISION}",
            reason="unexpected_pre_revision",
        )

    _upgrade_release_head()
    await _verify_release_revision()
    print(f"release_post_revision={RELEASE_TARGET_REVISION}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        exit_code = classify_failure(exc)
        print(f"migration_failure_exit_code={exit_code}", file=sys.stderr)
        raise SystemExit(exit_code) from exc
