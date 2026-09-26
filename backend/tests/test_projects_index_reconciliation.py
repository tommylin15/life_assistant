import importlib.util
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
