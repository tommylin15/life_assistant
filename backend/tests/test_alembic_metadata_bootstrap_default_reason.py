import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_release.py"


def _load_release():
    if not RELEASE.is_file():
        raise FileNotFoundError(RELEASE)
    spec = importlib.util.spec_from_file_location(
        "cloud_domain_parity_release_default_reason",
        RELEASE,
    )
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


class ProjectsStatusDefaultReasonDiagnosisTests(unittest.TestCase):
    def _classifier(self, release):
        return getattr(
            release,
            "classify_failure",
            release.metadata_preflight.classify_failure,
        )

    def test_missing_projects_status_default_has_distinct_exit(self):
        release = _load_release()
        preflight = release.metadata_preflight
        actual = _project_defaults(preflight)
        actual["status"] = None

        with self.assertRaises(preflight.BootstrapDefaultMismatchError) as captured:
            preflight.validate_server_defaults("projects", actual)

        self.assertEqual("projects", captured.exception.table)
        self.assertEqual("status", captured.exception.column)
        self.assertEqual("active", captured.exception.expected)
        self.assertIsNone(captured.exception.actual)
        self.assertEqual(250, self._classifier(release)(captured.exception))

    def test_wrong_non_null_projects_status_default_has_distinct_exit(self):
        release = _load_release()
        preflight = release.metadata_preflight
        actual = _project_defaults(preflight)
        actual["status"] = "'archived'::character varying"

        with self.assertRaises(preflight.BootstrapDefaultMismatchError) as captured:
            preflight.validate_server_defaults("projects", actual)

        self.assertEqual("projects", captured.exception.table)
        self.assertEqual("status", captured.exception.column)
        self.assertEqual("active", captured.exception.expected)
        self.assertEqual("'archived'::character varying", captured.exception.actual)
        self.assertEqual(251, self._classifier(release)(captured.exception))

    def test_reason_exit_codes_are_stable_non_overlapping_and_byte_safe(self):
        release = _load_release()
        preflight = release.metadata_preflight
        reason_codes = {250, 251}
        self.assertTrue(reason_codes.isdisjoint(preflight.BOOTSTRAP_EXIT_CODES.values()))
        self.assertTrue(reason_codes.isdisjoint(preflight.DEFAULT_MISMATCH_EXIT_CODES.values()))
        self.assertTrue(
            reason_codes.isdisjoint(
                range(
                    preflight.migration.EXIT_UNVERSIONED_TARGETS_BASE,
                    preflight.migration.EXIT_UNVERSIONED_TARGETS_BASE + 128,
                )
            )
        )
        self.assertLessEqual(max(reason_codes), 255)


if __name__ == "__main__":
    unittest.main()
