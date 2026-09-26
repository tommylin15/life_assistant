import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_migration.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("cloud_domain_migration_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProjectsIndexCombinedDiagnosisTests(unittest.TestCase):
    def test_combined_projects_index_exit_mapping_is_stable(self):
        runner = _load_runner()
        self.assertEqual(
            {
                ("missing", "missing"): 46,
                ("missing", "definition"): 47,
                ("definition", "missing"): 48,
                ("definition", "definition"): 49,
            },
            runner.PROJECTS_COMBINED_INDEX_MISMATCH_EXIT_CODES,
        )
        self.assertLess(
            max(runner.PROJECTS_COMBINED_INDEX_MISMATCH_EXIT_CODES.values()),
            runner.EXIT_UNVERSIONED_TARGETS_BASE,
        )

    def test_both_projects_indexes_missing_reports_both_states(self):
        runner = _load_runner()
        with self.assertRaises(runner.ProjectsRequiredIndexesMismatchError) as captured:
            runner.validate_baseline_required_indexes("projects", {})
        self.assertEqual("missing", captured.exception.status_reason)
        self.assertEqual("missing", captured.exception.name_reason)
        self.assertEqual(46, runner.classify_failure(captured.exception))

    def test_status_missing_and_name_definition_mismatch_is_combined(self):
        runner = _load_runner()
        indexes = {
            "ix_projects_name": "CREATE INDEX ix_projects_name ON public.projects USING btree (status)",
        }
        with self.assertRaises(runner.ProjectsRequiredIndexesMismatchError) as captured:
            runner.validate_baseline_required_indexes("projects", indexes)
        self.assertEqual("missing", captured.exception.status_reason)
        self.assertEqual("definition", captured.exception.name_reason)
        self.assertEqual(47, runner.classify_failure(captured.exception))

    def test_status_definition_mismatch_and_name_missing_is_combined(self):
        runner = _load_runner()
        indexes = {
            "ix_projects_status": "CREATE INDEX ix_projects_status ON public.projects USING btree (name)",
        }
        with self.assertRaises(runner.ProjectsRequiredIndexesMismatchError) as captured:
            runner.validate_baseline_required_indexes("projects", indexes)
        self.assertEqual("definition", captured.exception.status_reason)
        self.assertEqual("missing", captured.exception.name_reason)
        self.assertEqual(48, runner.classify_failure(captured.exception))

    def test_both_projects_indexes_definition_mismatch_is_combined(self):
        runner = _load_runner()
        indexes = {
            "ix_projects_status": "CREATE INDEX ix_projects_status ON public.projects USING btree (name)",
            "ix_projects_name": "CREATE INDEX ix_projects_name ON public.projects USING btree (status)",
        }
        with self.assertRaises(runner.ProjectsRequiredIndexesMismatchError) as captured:
            runner.validate_baseline_required_indexes("projects", indexes)
        self.assertEqual("definition", captured.exception.status_reason)
        self.assertEqual("definition", captured.exception.name_reason)
        self.assertEqual(49, runner.classify_failure(captured.exception))


if __name__ == "__main__":
    unittest.main()
