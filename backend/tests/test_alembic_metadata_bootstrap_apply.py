from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

from scripts import apply_cloud_domain_parity_migration as migration
from scripts import bootstrap_alembic_metadata as bootstrap
from scripts import preflight_alembic_metadata_bootstrap as metadata_preflight


REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / "backend" / "scripts" / "bootstrap_alembic_metadata.py"
RELEASE = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_release.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class MetadataBootstrapApplyContractTests(unittest.TestCase):
    def test_guarded_bootstrap_module_exists(self):
        self.assertTrue(
            BOOTSTRAP.is_file(),
            "guarded Alembic metadata bootstrap module must exist before release can write metadata",
        )

    def test_release_runner_uses_guarded_bootstrap(self):
        text = RELEASE.read_text(encoding="utf-8")
        self.assertIn("bootstrap_alembic_metadata", text)
        self.assertIn("run_bootstrap", text)
        self.assertNotIn("CREATE TABLE alembic_version", text)
        self.assertNotIn("INSERT INTO alembic_version", text)

    def test_deploy_workflow_carries_revision_scoped_bootstrap_approval(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION: '20260926_0004'",
            text,
        )
        self.assertIn(
            "ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION=$ALEMBIC_METADATA_BOOTSTRAP_APPROVED_REVISION",
            text,
        )

    def test_bootstrap_source_contains_no_application_data_rewrite_sql(self):
        text = BOOTSTRAP.read_text(encoding="utf-8").upper()
        for forbidden in (
            "DROP TABLE",
            "DROP COLUMN",
            "TRUNCATE",
            "ALTER TABLE",
            "UPDATE PROJECTS",
            "DELETE FROM",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)


class MetadataBootstrapApplyBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_wrong_or_missing_approval_fails_before_database_access(self):
        for approval in (None, "20260925_0003", "20260926_0004-extra"):
            with self.subTest(approval=approval):
                conn = AsyncMock()
                with self.assertRaises(
                    metadata_preflight.MetadataBootstrapApprovalRequiredError
                ):
                    await bootstrap.bootstrap_alembic_metadata(conn, approval)
                conn.execute.assert_not_awaited()

    async def test_verified_unversioned_schema_writes_only_version_metadata(self):
        conn = AsyncMock()
        physical_tables = set(migration.BASELINE_TABLES) | set(migration.TARGET_TABLES)

        with (
            patch.object(
                migration,
                "_public_tables",
                new=AsyncMock(return_value=physical_tables),
            ),
            patch.object(
                metadata_preflight,
                "inspect_bootstrap_readiness",
                new=AsyncMock(return_value=migration.TARGET_REVISION),
            ) as inspect_readiness,
            patch.object(
                migration,
                "_current_revision",
                new=AsyncMock(return_value=migration.TARGET_REVISION),
            ) as current_revision,
        ):
            changed = await bootstrap.bootstrap_alembic_metadata(
                conn,
                migration.TARGET_REVISION,
            )

        self.assertTrue(changed)
        inspect_readiness.assert_awaited_once_with(conn)
        current_revision.assert_awaited_once_with(conn)

        statements = [str(call.args[0]) for call in conn.execute.await_args_list]
        self.assertEqual(3, len(statements))
        self.assertIn("pg_advisory_xact_lock", statements[0])
        self.assertIn("CREATE TABLE public.alembic_version", statements[1])
        self.assertIn("INSERT INTO public.alembic_version", statements[2])
        self.assertEqual(
            {"revision": migration.TARGET_REVISION},
            conn.execute.await_args_list[2].args[1],
        )

    async def test_existing_target_revision_is_idempotent_noop(self):
        conn = AsyncMock()
        physical_tables = (
            set(migration.BASELINE_TABLES)
            | set(migration.TARGET_TABLES)
            | {"alembic_version"}
        )

        with (
            patch.object(
                migration,
                "_public_tables",
                new=AsyncMock(return_value=physical_tables),
            ),
            patch.object(
                migration,
                "_current_revision",
                new=AsyncMock(return_value=migration.TARGET_REVISION),
            ),
            patch.object(
                metadata_preflight,
                "inspect_bootstrap_readiness",
                new=AsyncMock(),
            ) as inspect_readiness,
        ):
            changed = await bootstrap.bootstrap_alembic_metadata(
                conn,
                migration.TARGET_REVISION,
            )

        self.assertFalse(changed)
        inspect_readiness.assert_not_awaited()
        statements = [str(call.args[0]) for call in conn.execute.await_args_list]
        self.assertEqual(1, len(statements))
        self.assertIn("pg_advisory_xact_lock", statements[0])


if __name__ == "__main__":
    unittest.main()
