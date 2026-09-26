import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from app.models.project import Project


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "reconcile_projects_indexes.py"


def _load_reconciler():
    if not SCRIPT.is_file():
        raise FileNotFoundError(SCRIPT)
    spec = importlib.util.spec_from_file_location("projects_index_reconciler", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _exact_indexes():
    return {
        "ix_projects_status": "CREATE INDEX ix_projects_status ON public.projects USING btree (status)",
        "ix_projects_name": "CREATE INDEX ix_projects_name ON public.projects USING btree (name)",
    }


def _baseline_indexes(reconciler, table):
    if table == "projects":
        return {}
    return {
        name: f"CREATE INDEX {name} ON public.{table} USING btree {fragment}"
        for name, fragment in reconciler.migration.BASELINE_REQUIRED_INDEXES[table].items()
    }


class ProjectIndexMetadataTests(unittest.TestCase):
    def test_project_orm_declares_migration_required_indexes(self):
        indexes = {
            index.name: tuple(column.name for column in index.columns)
            for index in Project.__table__.indexes
        }
        self.assertEqual(
            {
                "ix_projects_status": ("status",),
                "ix_projects_name": ("name",),
            },
            indexes,
        )


class ProjectIndexReconciliationPlanTests(unittest.TestCase):
    def test_both_missing_indexes_plan_two_additive_creates_in_stable_order(self):
        reconciler = _load_reconciler()
        self.assertEqual(
            (
                ("ix_projects_status", "status"),
                ("ix_projects_name", "name"),
            ),
            reconciler.plan_projects_index_reconciliation({}),
        )

    def test_single_missing_index_plans_only_missing_create(self):
        reconciler = _load_reconciler()
        indexes = _exact_indexes()
        indexes.pop("ix_projects_name")
        self.assertEqual(
            (("ix_projects_name", "name"),),
            reconciler.plan_projects_index_reconciliation(indexes),
        )

    def test_exact_indexes_make_reconciliation_idempotent(self):
        reconciler = _load_reconciler()
        self.assertEqual((), reconciler.plan_projects_index_reconciliation(_exact_indexes()))

    def test_existing_wrong_definition_fails_closed_instead_of_replacing(self):
        reconciler = _load_reconciler()
        indexes = _exact_indexes()
        indexes["ix_projects_status"] = (
            "CREATE INDEX ix_projects_status ON public.projects USING btree (name)"
        )
        with self.assertRaises(reconciler.BaselineRequiredIndexMismatchError) as captured:
            reconciler.plan_projects_index_reconciliation(indexes)
        self.assertEqual("ix_projects_status", captured.exception.index_name)
        self.assertEqual("definition", captured.exception.reason)

    def test_partial_or_extra_definition_is_not_accepted_as_exact_contract(self):
        reconciler = _load_reconciler()
        indexes = _exact_indexes()
        indexes["ix_projects_status"] = (
            "CREATE INDEX ix_projects_status ON public.projects USING btree (status) "
            "WHERE status = 'active'"
        )
        with self.assertRaises(reconciler.BaselineRequiredIndexMismatchError) as captured:
            reconciler.plan_projects_index_reconciliation(indexes)
        self.assertEqual("ix_projects_status", captured.exception.index_name)
        self.assertEqual("definition", captured.exception.reason)


class ProjectIndexReconciliationExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_versioned_database_is_never_reconciled(self):
        reconciler = _load_reconciler()
        conn = AsyncMock()
        tables = (
            set(reconciler.migration.BASELINE_TABLES)
            | set(reconciler.migration.TARGET_TABLES)
            | {"alembic_version"}
        )
        with patch.object(
            reconciler.migration,
            "_public_tables",
            new=AsyncMock(return_value=tables),
        ):
            result = await reconciler.reconcile_projects_indexes(conn)
        self.assertEqual((), result)
        conn.execute.assert_not_awaited()

    async def test_target_schema_mismatch_blocks_all_index_ddl(self):
        reconciler = _load_reconciler()
        conn = AsyncMock()
        tables = set(reconciler.migration.BASELINE_TABLES) | set(
            reconciler.migration.TARGET_TABLES
        )

        async def columns(_conn, table):
            return reconciler.migration.BASELINE_EXPECTED_COLUMNS[table]

        async def primary_key(_conn, table):
            return reconciler.migration.BASELINE_EXPECTED_PRIMARY_KEYS[table]

        async def indexes(_conn, table):
            return _baseline_indexes(reconciler, table)

        with (
            patch.object(
                reconciler.migration,
                "_public_tables",
                new=AsyncMock(return_value=tables),
            ),
            patch.object(reconciler.migration, "_table_columns", new=AsyncMock(side_effect=columns)),
            patch.object(reconciler.migration, "_primary_key", new=AsyncMock(side_effect=primary_key)),
            patch.object(reconciler.migration, "_table_indexes", new=AsyncMock(side_effect=indexes)),
            patch.object(
                reconciler.migration,
                "_verify_schema",
                new=AsyncMock(side_effect=reconciler.migration.SchemaMismatchError("target mismatch")),
            ),
        ):
            with self.assertRaises(reconciler.migration.SchemaMismatchError):
                await reconciler.reconcile_projects_indexes(conn)

        conn.execute.assert_not_awaited()

    async def test_successful_reconciliation_creates_only_missing_indexes_after_preflight(self):
        reconciler = _load_reconciler()
        conn = AsyncMock()
        tables = set(reconciler.migration.BASELINE_TABLES) | set(
            reconciler.migration.TARGET_TABLES
        )
        project_index_reads = 0

        async def columns(_conn, table):
            return reconciler.migration.BASELINE_EXPECTED_COLUMNS[table]

        async def primary_key(_conn, table):
            return reconciler.migration.BASELINE_EXPECTED_PRIMARY_KEYS[table]

        async def indexes(_conn, table):
            nonlocal project_index_reads
            if table != "projects":
                return _baseline_indexes(reconciler, table)
            project_index_reads += 1
            return {} if project_index_reads == 1 else _exact_indexes()

        with (
            patch.object(
                reconciler.migration,
                "_public_tables",
                new=AsyncMock(return_value=tables),
            ),
            patch.object(reconciler.migration, "_table_columns", new=AsyncMock(side_effect=columns)),
            patch.object(reconciler.migration, "_primary_key", new=AsyncMock(side_effect=primary_key)),
            patch.object(reconciler.migration, "_table_indexes", new=AsyncMock(side_effect=indexes)),
            patch.object(reconciler.migration, "_verify_schema", new=AsyncMock()),
        ):
            result = await reconciler.reconcile_projects_indexes(conn)

        self.assertEqual(("ix_projects_status", "ix_projects_name"), result)
        self.assertEqual(2, conn.execute.await_count)
        ddl = [str(call.args[0]) for call in conn.execute.await_args_list]
        self.assertIn(
            'CREATE INDEX IF NOT EXISTS "ix_projects_status" ON "projects" ("status")',
            ddl[0],
        )
        self.assertIn(
            'CREATE INDEX IF NOT EXISTS "ix_projects_name" ON "projects" ("name")',
            ddl[1],
        )

    async def test_wrong_existing_definition_blocks_all_index_ddl(self):
        reconciler = _load_reconciler()
        conn = AsyncMock()
        tables = set(reconciler.migration.BASELINE_TABLES) | set(
            reconciler.migration.TARGET_TABLES
        )

        async def columns(_conn, table):
            return reconciler.migration.BASELINE_EXPECTED_COLUMNS[table]

        async def primary_key(_conn, table):
            return reconciler.migration.BASELINE_EXPECTED_PRIMARY_KEYS[table]

        async def indexes(_conn, table):
            if table != "projects":
                return _baseline_indexes(reconciler, table)
            bad = _exact_indexes()
            bad["ix_projects_status"] = (
                "CREATE INDEX ix_projects_status ON public.projects USING btree (name)"
            )
            return bad

        with (
            patch.object(
                reconciler.migration,
                "_public_tables",
                new=AsyncMock(return_value=tables),
            ),
            patch.object(reconciler.migration, "_table_columns", new=AsyncMock(side_effect=columns)),
            patch.object(reconciler.migration, "_primary_key", new=AsyncMock(side_effect=primary_key)),
            patch.object(reconciler.migration, "_table_indexes", new=AsyncMock(side_effect=indexes)),
            patch.object(reconciler.migration, "_verify_schema", new=AsyncMock()),
        ):
            with self.assertRaises(reconciler.BaselineRequiredIndexMismatchError):
                await reconciler.reconcile_projects_indexes(conn)

        conn.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
