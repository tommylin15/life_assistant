#!/usr/bin/env python3
"""Release entrypoint for guarded reconciliation and migration verification.

The release flow may repair only the two previously diagnosed missing projects
indexes. If the database is still unversioned afterward, a stronger read-only
metadata-bootstrap preflight runs. Passing that preflight is intentionally a
non-zero approval gate: this module contains no metadata write path.
"""

from __future__ import annotations

import asyncio
import sys

from scripts import apply_cloud_domain_parity_migration as migration
from scripts import preflight_alembic_metadata_bootstrap as metadata_preflight
from scripts.reconcile_projects_indexes import run_reconciliation


async def main() -> None:
    repaired = await run_reconciliation()
    print(
        "migration_reconciled_projects_indexes="
        + (",".join(repaired) if repaired else "none")
    )

    ready_revision = await metadata_preflight.run_preflight()
    if ready_revision is not None:
        print(f"metadata_bootstrap_preflight=verified:{ready_revision}")
        raise metadata_preflight.MetadataBootstrapApprovalRequiredError(
            ready_revision
        )

    await migration.main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        exit_code = metadata_preflight.classify_failure(exc)
        print(f"migration_failure_exit_code={exit_code}", file=sys.stderr)
        raise SystemExit(exit_code) from exc
