import unittest

from scripts import apply_cloud_domain_parity_release as release


class ReleaseRevisionDiagnosticsTests(unittest.TestCase):
    def test_release_revision_reasons_have_distinct_stable_exit_codes(self):
        expected = {
            "generic": 60,
            "missing_tables": 62,
            "missing_task_columns": 63,
            "target_revision": 64,
            "unexpected_pre_revision": 65,
            "version_table": 66,
            "revision_row_count": 67,
        }
        self.assertEqual(expected, release.RELEASE_REVISION_EXIT_CODES)
        self.assertEqual(len(expected), len(set(expected.values())))
        self.assertNotIn(release.EXIT_RELEASE_ALEMBIC, expected.values())

    def test_classifier_uses_release_revision_reason(self):
        for reason, exit_code in release.RELEASE_REVISION_EXIT_CODES.items():
            with self.subTest(reason=reason):
                exc = release.ReleaseRevisionError("diagnostic", reason=reason)
                self.assertEqual(exit_code, release.classify_failure(exc))

    def test_unknown_reason_fails_closed_to_generic_release_revision_exit(self):
        exc = release.ReleaseRevisionError("diagnostic", reason="unknown")
        self.assertEqual(release.EXIT_RELEASE_REVISION, release.classify_failure(exc))


if __name__ == "__main__":
    unittest.main()
