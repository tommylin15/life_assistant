#!/usr/bin/env python3
"""Release entrypoint for guarded reconciliation and migration verification.

The release flow may repair only the previously diagnosed missing projects
indexes and projects.status server default. If the database is still
unversioned afterward, targeted read-only diagnostics and the stronger
metadata-bootstrap preflight run. When that complete physical-schema preflight
passes, a separately guarded, revision-scoped bootstrap may write only Alembic
metadata before normal migration verification continues.
"""

from __future__ import annotations

import asyncio
import sys

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


def classify_failure(exc: BaseException) -> int:
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


async def main() -> None:
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

    # Diagnose the already-observed note_links FK drift before the generic
    # preflight so Cloud Run task metadata remains useful without log-viewer IAM.
    await note_links_fk_diagnosis.run_diagnosis()

    ready_revision = await metadata_preflight.run_preflight()
    if ready_revision is not None:
        print(f"metadata_bootstrap_preflight=verified:{ready_revision}")
        bootstrapped = await metadata_bootstrap.run_bootstrap()
        print(
            "metadata_bootstrap_applied="
            + (ready_revision if bootstrapped else "already-versioned")
        )
        # A missing or mismatched workflow approval remains fail-closed as
        # MetadataBootstrapApprovalRequiredError (exit 50).

    await migration.main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        exit_code = classify_failure(exc)
        print(f"migration_failure_exit_code={exit_code}", file=sys.stderr)
        raise SystemExit(exit_code) from exc
