import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
SCRIPT = BACKEND_ROOT / "scripts" / "reconcile_projects_status_default.py"


def _load_reconciler():
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    spec = importlib.util.spec_from_file_location(
        "reconcile_projects_status_default_guard_test_target",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProjectsStatusDefaultGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_unrelated_fk_drift_does_not_block_narrow_default_repair(self):
        reconciler = _load_reconciler()
        conn = AsyncMock()
        project_reads = 0

        async def column_defaults(_conn, table):
            nonlocal project_reads
            if table == "projects":
                project_reads += 1
                if project_reads == 1:
                    return {"status": None}
                return {"status": "'active'::character varying"}
            return {}

        with (
            patch.object(
                reconciler.migration,
                "_public_tables",
                new=AsyncMock(
                    return_value=set(reconciler.migration.BASELINE_TABLES)
                    | set(reconciler.migration.TARGET_TABLES)
                ),
            ),
            patch.object(
                reconciler.migration,
                "validate_unversioned_baseline_tables",
                return_value=True,
            ),
            patch.object(
                reconciler.migration,
                "_verify_unversioned_baseline_schema",
                new=AsyncMock(),
            ),
            patch.object(
                reconciler.migration,
                "_verify_schema",
                new=AsyncMock(),
            ),
            patch.object(
                reconciler.metadata_preflight,
                "_verify_required_indexes",
                new=AsyncMock(),
            ),
            patch.object(
                reconciler.metadata_preflight,
                "_verify_foreign_key_semantics",
                new=AsyncMock(),
            ) as verify_fks,
            patch.object(
                reconciler.metadata_preflight,
                "_verify_extra_constraints",
                new=AsyncMock(),
            ),
            patch.object(
                reconciler.metadata_preflight,
                "_column_defaults",
                new=AsyncMock(side_effect=column_defaults),
            ),
            patch.object(
                reconciler.metadata_preflight,
                "validate_server_defaults",
            ),
        ):
            repaired = await reconciler.reconcile_projects_status_default(conn)

        self.assertTrue(repaired)
        verify_fks.assert_not_awaited()
        conn.execute.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
