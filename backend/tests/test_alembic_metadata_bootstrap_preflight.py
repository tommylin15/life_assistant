import importlib.util
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "preflight_alembic_metadata_bootstrap.py"
RELEASE = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_release.py"


def _load_preflight():
    if not SCRIPT.is_file():
        raise FileNotFoundError(SCRIPT)
    spec = importlib.util.spec_from_file_location("alembic_metadata_bootstrap_preflight", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _project_defaults(preflight):
    actual = {
        column: None
        for column in preflight.migration.BASELINE_EXPECTED_COLUMNS["projects"]
    }
    actual.update(
        {
            "status": "'active'::character varying",
            "created_at": "now()",
            "updated_at": "now()",
        }
    )
    return actual


class AlembicMetadataBootstrapContractTests(unittest.TestCase):
    def test_expected_server_defaults_match_migrations_0001_through_0004(self):
        preflight = _load_preflight()
        self.assertEqual(
            {
                "google_connections": {
                    "created_at": "now()",
                    "updated_at": "now()",
                },
                "google_oauth_states": {"created_at": "now()"},
                "execution_logs": {"started_at": "now()"},
                "projects": {
                    "status": "active",
                    "created_at": "now()",
                    "updated_at": "now()",
                },
                "notes": {
                    "created_at": "now()",
                    "updated_at": "now()",
                },
                "note_links": {},
                "habits": {
                    "is_active": "true",
                    "created_at": "now()",
                },
                "habit_completions": {"completed_at": "now()"},
                "shopping_lists": {"created_at": "now()"},
                "shopping_items": {
                    "is_done": "false",
                    "sort_order": "0",
                },
                "templates": {
                    "created_at": "now()",
                    "updated_at": "now()",
                },
            },
            preflight.EXPECTED_SERVER_DEFAULTS,
        )

    def test_server_default_validation_accepts_postgresql_casts_and_rejects_missing_default(self):
        preflight = _load_preflight()
        actual = _project_defaults(preflight)
        preflight.validate_server_defaults("projects", actual)

        actual["status"] = None
        with self.assertRaises(preflight.BootstrapDefaultMismatchError) as captured:
            preflight.validate_server_defaults("projects", actual)
        self.assertEqual("projects", captured.exception.table)
        self.assertEqual("status", captured.exception.column)

    def test_default_mismatch_exit_mapping_identifies_exact_table_and_column(self):
        preflight = _load_preflight()
        expected_columns = {
            "google_connections": (
                "user_sub",
                "email",
                "encrypted_access_token",
                "encrypted_refresh_token",
                "scopes",
                "access_token_expires_at",
                "created_at",
                "updated_at",
            ),
            "google_oauth_states": (
                "state_hash",
                "user_sub",
                "email",
                "services",
                "expires_at",
                "created_at",
            ),
            "execution_logs": (
                "id",
                "request_id",
                "action_id",
                "user_sub",
                "action_type",
                "entity_type",
                "entity_id",
                "provider",
                "status",
                "result",
                "error_category",
                "summary",
                "started_at",
                "finished_at",
            ),
            "projects": (
                "id",
                "name",
                "summary",
                "status",
                "created_at",
                "updated_at",
            ),
            "notes": (
                "id",
                "title",
                "body",
                "project_id",
                "created_at",
                "updated_at",
            ),
            "note_links": ("source_note_id", "target_note_id"),
            "habits": (
                "id",
                "title",
                "recurrence_rule",
                "reminder_time",
                "is_active",
                "created_at",
            ),
            "habit_completions": ("id", "habit_id", "completed_at"),
            "shopping_lists": ("id", "name", "project_id", "created_at"),
            "shopping_items": (
                "id",
                "list_id",
                "name",
                "category",
                "is_done",
                "sort_order",
            ),
            "templates": (
                "id",
                "name",
                "template_type",
                "payload_json",
                "created_at",
                "updated_at",
            ),
        }
        expected_keys = [
            (table, column)
            for table, columns in expected_columns.items()
            for column in columns
        ]
        expected_codes = list(range(55, 64)) + list(range(192, 250))
        self.assertEqual(67, len(expected_keys))
        self.assertEqual(
            list(zip(expected_keys, expected_codes, strict=True)),
            list(preflight.DEFAULT_MISMATCH_EXIT_CODES.items()),
        )
        self.assertEqual(len(expected_codes), len(set(expected_codes)))
        self.assertTrue(
            set(expected_codes).isdisjoint(preflight.BOOTSTRAP_EXIT_CODES.values())
        )
        self.assertTrue(
            set(expected_codes).isdisjoint(
                range(
                    preflight.migration.EXIT_UNVERSIONED_TARGETS_BASE,
                    preflight.migration.EXIT_UNVERSIONED_TARGETS_BASE + 128,
                )
            )
        )
        for (table, column), code in zip(expected_keys, expected_codes, strict=True):
            error = preflight.BootstrapDefaultMismatchError(
                table,
                column,
                expected=None,
                actual="unexpected",
            )
            self.assertEqual(code, preflight.classify_failure(error))

        unknown = preflight.BootstrapDefaultMismatchError(
            "future_table",
            "future_column",
            expected=None,
            actual="unexpected",
        )
        self.assertEqual(
            preflight.EXIT_BOOTSTRAP_DEFAULT_MISMATCH,
            preflight.classify_failure(unknown),
        )

    def test_required_index_definition_is_exact_and_rejects_partial_index(self):
        preflight = _load_preflight()
        indexes = {
            "ix_projects_status": (
                "CREATE INDEX ix_projects_status ON public.projects USING btree (status)"
            ),
            "ix_projects_name": (
                "CREATE INDEX ix_projects_name ON public.projects USING btree (name)"
            ),
        }
        preflight.validate_required_indexes("projects", indexes)

        indexes["ix_projects_status"] += " WHERE status = 'active'"
        with self.assertRaises(preflight.BootstrapIndexMismatchError) as captured:
            preflight.validate_required_indexes("projects", indexes)
        self.assertEqual("projects", captured.exception.table)
        self.assertEqual("ix_projects_status", captured.exception.index_name)

    def test_foreign_key_semantics_require_no_action_nondeferrable_validated(self):
        preflight = _load_preflight()
        exact = {
            (
                "list_id",
                "shopping_lists",
                "id",
                "a",
                "a",
                False,
                False,
                True,
            )
        }
        preflight.validate_foreign_key_contracts("shopping_items", exact)

        cascade = {
            (
                "list_id",
                "shopping_lists",
                "id",
                "a",
                "c",
                False,
                False,
                True,
            )
        }
        with self.assertRaises(preflight.BootstrapForeignKeyMismatchError):
            preflight.validate_foreign_key_contracts("shopping_items", cascade)

    def test_unexpected_unique_check_or_exclusion_constraint_fails_closed(self):
        preflight = _load_preflight()
        preflight.validate_no_extra_constraints("projects", set())
        with self.assertRaises(preflight.BootstrapConstraintMismatchError) as captured:
            preflight.validate_no_extra_constraints(
                "projects",
                {("projects_name_key", "u")},
            )
        self.assertEqual("projects", captured.exception.table)

    def test_preflight_exit_mapping_is_stable_and_non_overlapping(self):
        preflight = _load_preflight()
        self.assertEqual(
            {
                preflight.MetadataBootstrapApprovalRequiredError: 50,
                preflight.BootstrapDefaultMismatchError: 51,
                preflight.BootstrapIndexMismatchError: 52,
                preflight.BootstrapForeignKeyMismatchError: 53,
                preflight.BootstrapConstraintMismatchError: 54,
            },
            preflight.BOOTSTRAP_EXIT_CODES,
        )
        self.assertTrue(
            all(
                code < preflight.migration.EXIT_UNVERSIONED_TARGETS_BASE
                for code in preflight.BOOTSTRAP_EXIT_CODES.values()
            )
        )


class AlembicMetadataBootstrapInspectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_versioned_database_skips_bootstrap_preflight(self):
        preflight = _load_preflight()
        conn = AsyncMock()
        tables = (
            set(preflight.migration.BASELINE_TABLES)
            | set(preflight.migration.TARGET_TABLES)
            | {"alembic_version"}
        )
        with (
            patch.object(
                preflight.migration,
                "_public_tables",
                new=AsyncMock(return_value=tables),
            ),
            patch.object(
                preflight,
                "_verify_server_defaults",
                new=AsyncMock(),
            ) as verify_defaults,
        ):
            result = await preflight.inspect_bootstrap_readiness(conn)
        self.assertIsNone(result)
        verify_defaults.assert_not_awaited()

    async def test_verified_unversioned_schema_returns_only_target_revision_without_writes(self):
        preflight = _load_preflight()
        conn = AsyncMock()
        tables = set(preflight.migration.BASELINE_TABLES) | set(
            preflight.migration.TARGET_TABLES
        )

        with (
            patch.object(
                preflight.migration,
                "_public_tables",
                new=AsyncMock(return_value=tables),
            ),
            patch.object(
                preflight.migration,
                "_verify_unversioned_baseline_schema",
                new=AsyncMock(),
            ) as verify_baseline,
            patch.object(
                preflight.migration,
                "_verify_schema",
                new=AsyncMock(),
            ) as verify_target,
            patch.object(
                preflight,
                "_verify_server_defaults",
                new=AsyncMock(),
            ) as verify_defaults,
            patch.object(
                preflight,
                "_verify_required_indexes",
                new=AsyncMock(),
            ) as verify_indexes,
            patch.object(
                preflight,
                "_verify_foreign_key_semantics",
                new=AsyncMock(),
            ) as verify_fks,
            patch.object(
                preflight,
                "_verify_extra_constraints",
                new=AsyncMock(),
            ) as verify_constraints,
        ):
            result = await preflight.inspect_bootstrap_readiness(conn)

        self.assertEqual(preflight.migration.TARGET_REVISION, result)
        verify_baseline.assert_awaited_once_with(conn)
        verify_target.assert_awaited_once_with(conn)
        verify_defaults.assert_awaited_once_with(conn)
        verify_indexes.assert_awaited_once_with(conn)
        verify_fks.assert_awaited_once_with(conn)
        verify_constraints.assert_awaited_once_with(conn)
        conn.execute.assert_not_awaited()


class AlembicMetadataBootstrapReleaseGuardTests(unittest.TestCase):
    def test_release_runner_runs_preflight_but_contains_no_stamp_write_path(self):
        text = RELEASE.read_text(encoding="utf-8")
        self.assertIn("preflight_alembic_metadata_bootstrap", text)
        self.assertIn("MetadataBootstrapApprovalRequiredError", text)
        self.assertNotIn("alembic stamp", text.lower())
        self.assertNotIn("command.stamp", text)
        self.assertNotIn("INSERT INTO alembic_version", text)
        self.assertNotIn("CREATE TABLE alembic_version", text)

    def test_bootstrap_ready_exit_code_is_stable_and_below_target_bitmap_range(self):
        preflight = _load_preflight()
        self.assertEqual(50, preflight.EXIT_METADATA_BOOTSTRAP_APPROVAL_REQUIRED)
        self.assertLess(
            preflight.EXIT_METADATA_BOOTSTRAP_APPROVAL_REQUIRED,
            preflight.migration.EXIT_UNVERSIONED_TARGETS_BASE,
        )


if __name__ == "__main__":
    unittest.main()
