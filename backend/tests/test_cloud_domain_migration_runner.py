import importlib.util
from pathlib import Path
import subprocess
import unittest

from sqlalchemy.exc import SQLAlchemyError


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_migration.py"


def _load_runner():
    if not SCRIPT.is_file():
        raise FileNotFoundError(SCRIPT)
    spec = importlib.util.spec_from_file_location("cloud_domain_migration_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CloudDomainMigrationRunnerTests(unittest.TestCase):
    def test_previous_revision_without_target_tables_allows_forward_upgrade(self):
        runner = _load_runner()
        action = runner.decide_migration_action("20260925_0003", set())
        self.assertEqual("upgrade", action)

    def test_previous_revision_with_precreated_target_table_is_drift(self):
        runner = _load_runner()
        with self.assertRaisesRegex(RuntimeError, "migration drift"):
            runner.decide_migration_action("20260925_0003", {"notes"})

    def test_target_revision_requires_schema_verification_only(self):
        runner = _load_runner()
        action = runner.decide_migration_action(
            "20260926_0004",
            set(runner.TARGET_TABLES),
        )
        self.assertEqual("verify", action)

    def test_target_revision_missing_table_is_invalid(self):
        runner = _load_runner()
        with self.assertRaisesRegex(RuntimeError, "missing target tables"):
            runner.decide_migration_action("20260926_0004", {"notes"})

    def test_unknown_revision_is_rejected(self):
        runner = _load_runner()
        with self.assertRaisesRegex(RuntimeError, "unexpected alembic revision"):
            runner.decide_migration_action("legacy", set())

    def test_database_failure_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_DATABASE,
            runner.classify_failure(SQLAlchemyError("database unavailable")),
        )

    def test_contract_failure_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_CONTRACT,
            runner.classify_failure(RuntimeError("migration drift")),
        )

    def test_alembic_failure_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_ALEMBIC,
            runner.classify_failure(subprocess.CalledProcessError(1, ["alembic"])),
        )

    def test_unexpected_failure_is_fail_closed_with_distinct_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_UNEXPECTED,
            runner.classify_failure(ValueError("unexpected")),
        )


if __name__ == "__main__":
    unittest.main()
