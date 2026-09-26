import importlib.util
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
SCRIPT = BACKEND_ROOT / "scripts" / "reconcile_projects_status_default.py"


def _load_reconciler():
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    spec = importlib.util.spec_from_file_location(
        "reconcile_projects_status_default_test_target",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProjectsStatusDefaultReconciliationTests(unittest.TestCase):
    def test_missing_default_is_repairable(self):
        reconciler = _load_reconciler()
        self.assertTrue(
            reconciler.plan_projects_status_default_reconciliation(None)
        )

    def test_expected_default_is_noop_for_postgres_variants(self):
        reconciler = _load_reconciler()
        for value in (
            "'active'",
            "'active'::character varying",
            "'active'::text",
        ):
            with self.subTest(value=value):
                self.assertFalse(
                    reconciler.plan_projects_status_default_reconciliation(value)
                )

    def test_wrong_existing_default_is_fail_closed(self):
        reconciler = _load_reconciler()
        with self.assertRaises(
            reconciler.metadata_preflight.BootstrapDefaultMismatchError
        ) as captured:
            reconciler.plan_projects_status_default_reconciliation(
                "'archived'::character varying"
            )

        self.assertEqual("projects", captured.exception.table)
        self.assertEqual("status", captured.exception.column)
        self.assertEqual("active", captured.exception.expected)
        self.assertEqual(
            "'archived'::character varying",
            captured.exception.actual,
        )

    def test_repair_sql_only_sets_default(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(
            'ALTER COLUMN "status" SET DEFAULT \'active\'',
            source,
        )
        self.assertNotIn("UPDATE projects", source)
        self.assertNotIn("DROP TABLE", source)
        self.assertNotIn("DROP COLUMN", source)


if __name__ == "__main__":
    unittest.main()
