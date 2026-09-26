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
        with self.assertRaisesRegex(runner.PrecreatedDriftError, "migration drift"):
            runner.decide_migration_action("20260925_0003", {"notes"})

    def test_target_revision_requires_schema_verification_only(self):
        runner = _load_runner()
        action = runner.decide_migration_action(
            "20260926_0004",
            set(runner.TARGET_TABLES),
        )
        self.assertEqual("verify", action)

    def test_target_revision_missing_table_is_schema_mismatch(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.SchemaMismatchError, "missing target tables"):
            runner.decide_migration_action("20260926_0004", {"notes"})

    def test_missing_revision_table_is_distinct_revision_failure(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.RevisionTableMissingError, "alembic_version table is missing"):
            runner.validate_revision_state(False, [])
        self.assertEqual(
            runner.EXIT_REVISION_TABLE_MISSING,
            runner.classify_failure(runner.RevisionTableMissingError("missing")),
        )

    def test_invalid_revision_row_count_is_distinct_revision_failure(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.RevisionRowCountError, "expected one alembic_version row"):
            runner.validate_revision_state(True, [])
        self.assertEqual(
            runner.EXIT_REVISION_ROW_COUNT,
            runner.classify_failure(runner.RevisionRowCountError("bad row count")),
        )

    def test_single_revision_row_is_returned(self):
        runner = _load_runner()
        self.assertEqual(
            "20260925_0003",
            runner.validate_revision_state(True, ["20260925_0003"]),
        )

    def test_unknown_revision_is_distinct_current_revision_failure(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.UnexpectedCurrentRevisionError, "unexpected alembic revision"):
            runner.decide_migration_action("legacy", set())
        self.assertEqual(
            runner.EXIT_UNEXPECTED_CURRENT_REVISION,
            runner.classify_failure(runner.UnexpectedCurrentRevisionError("legacy")),
        )

    def test_post_migration_revision_mismatch_is_distinct_failure(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.PostMigrationRevisionMismatchError, "post-migration revision mismatch"):
            runner.require_target_revision("20260925_0003")
        self.assertEqual(
            runner.EXIT_POST_MIGRATION_REVISION,
            runner.classify_failure(runner.PostMigrationRevisionMismatchError("mismatch")),
        )

    def test_target_revision_passes_post_migration_check(self):
        runner = _load_runner()
        runner.require_target_revision(runner.TARGET_REVISION)

    def test_unversioned_database_missing_baseline_tables_is_distinct_failure(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.BaselineTablesMissingError, "missing baseline tables"):
            runner.validate_unversioned_baseline_tables({"tasks"})
        self.assertEqual(
            runner.EXIT_BASELINE_TABLES_MISSING,
            runner.classify_failure(runner.BaselineTablesMissingError("missing baseline")),
        )

    def test_unversioned_database_with_target_table_is_precreated_drift(self):
        runner = _load_runner()
        tables = set(runner.BASELINE_TABLES) | {"tasks", "notes"}
        with self.assertRaisesRegex(runner.PrecreatedDriftError, "target tables already exist"):
            runner.validate_unversioned_baseline_tables(tables)

    def test_unversioned_target_presence_encodes_exact_subset(self):
        runner = _load_runner()
        present = {"notes", "templates"}
        self.assertEqual(129, runner.encode_unversioned_target_tables(present))
        error = runner.UnversionedTargetTablesPresentError(present)
        self.assertEqual(present, error.tables)
        self.assertEqual(129, runner.classify_failure(error))

    def test_unversioned_target_presence_uses_stable_target_order(self):
        runner = _load_runner()
        self.assertEqual(
            {
                "notes": 1,
                "note_links": 2,
                "habits": 4,
                "habit_completions": 8,
                "shopping_lists": 16,
                "shopping_items": 32,
                "templates": 64,
            },
            runner.UNVERSIONED_TARGET_TABLE_BITS,
        )
        self.assertEqual(191, runner.encode_unversioned_target_tables(set(runner.TARGET_TABLES)))

    def test_unversioned_database_raises_encoded_target_presence_error(self):
        runner = _load_runner()
        tables = set(runner.BASELINE_TABLES) | {"tasks", "notes", "shopping_items"}
        with self.assertRaises(runner.UnversionedTargetTablesPresentError) as captured:
            runner.validate_unversioned_baseline_tables(tables)
        self.assertEqual({"notes", "shopping_items"}, captured.exception.tables)
        self.assertEqual(97, runner.classify_failure(captured.exception))

    def test_unversioned_database_with_baseline_tables_allows_shape_check(self):
        runner = _load_runner()
        runner.validate_unversioned_baseline_tables(set(runner.BASELINE_TABLES) | {"tasks"})

    def test_unversioned_baseline_schema_mismatch_is_distinct_failure(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.BaselineSchemaMismatchError, "baseline schema mismatch"):
            runner.validate_baseline_table_shape("projects", {}, ())
        self.assertEqual(
            runner.EXIT_BASELINE_SCHEMA_MISMATCH,
            runner.classify_failure(runner.BaselineSchemaMismatchError("schema mismatch")),
        )

    def test_unversioned_baseline_matching_table_shape_passes(self):
        runner = _load_runner()
        runner.validate_baseline_table_shape(
            "projects",
            runner.BASELINE_EXPECTED_COLUMNS["projects"],
            runner.BASELINE_EXPECTED_PRIMARY_KEYS["projects"],
        )

    def test_unversioned_baseline_missing_required_index_is_schema_mismatch(self):
        runner = _load_runner()
        with self.assertRaisesRegex(runner.BaselineSchemaMismatchError, "baseline index mismatch"):
            runner.validate_baseline_required_indexes("projects", {})

    def test_unversioned_baseline_required_indexes_pass(self):
        runner = _load_runner()
        runner.validate_baseline_required_indexes(
            "projects",
            {
                "ix_projects_status": "CREATE INDEX ix_projects_status ON public.projects USING btree (status)",
                "ix_projects_name": "CREATE INDEX ix_projects_name ON public.projects USING btree (name)",
            },
        )

    def test_verified_unversioned_baseline_has_distinct_diagnostic_exit(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_BASELINE_VERIFIED_UNVERSIONED,
            runner.classify_failure(
                runner.BaselineVerifiedWithoutVersionError("baseline verified")
            ),
        )

    def test_database_failure_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_DATABASE,
            runner.classify_failure(SQLAlchemyError("database unavailable")),
        )

    def test_precreated_drift_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_PRECREATED_DRIFT,
            runner.classify_failure(runner.PrecreatedDriftError("migration drift")),
        )

    def test_schema_mismatch_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_SCHEMA_MISMATCH,
            runner.classify_failure(runner.SchemaMismatchError("schema mismatch")),
        )

    def test_preserved_data_mismatch_has_distinct_process_exit_code(self):
        runner = _load_runner()
        self.assertEqual(
            runner.EXIT_PRESERVED_DATA,
            runner.classify_failure(runner.PreservedDataMismatchError("data changed")),
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
