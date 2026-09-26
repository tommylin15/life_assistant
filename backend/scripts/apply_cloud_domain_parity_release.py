#!/usr/bin/env python3
"""Release entrypoint: guarded reconciliation followed by normal migration verification.

The reconciliation step may add only the two missing projects indexes after a
full preflight. It never stamps Alembic metadata. The existing migration runner
remains responsible for revision/schema verification and stable exit codes.
"""

from __future__ import annotations

import asyncio
import sys

from scripts import apply_cloud_domain_parity_migration as migration
from scripts.reconcile_projects_indexes import run_reconciliation


async def main() -> None:
    repaired = await run_reconciliation()
    print(
        "migration_reconciled_projects_indexes="
        + (",".join(repaired) if repaired else "none")
    )
    await migration.main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        exit_code = migration.classify_failure(exc)
        print(f"migration_failure_exit_code={exit_code}", file=sys.stderr)
        raise SystemExit(exit_code) from exc
