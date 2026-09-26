import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE = REPO_ROOT / "backend" / "scripts" / "apply_cloud_domain_parity_release.py"


def _load_release():
    spec = importlib.util.spec_from_file_location(
        "cloud_domain_parity_release_fk_reason",
        RELEASE,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ForeignKeyReasonDiagnosisTests(unittest.TestCase):
    def test_expected_fk_tables_have_distinct_byte_safe_exit_codes(self):
        release = _load_release()
        self.assertEqual(
            {
                "note_links": 252,
                "habit_completions": 253,
                "shopping_items": 254,
            },
            release.FOREIGN_KEY_MISMATCH_EXIT_CODES,
        )
        self.assertEqual(255, release.EXIT_UNEXPECTED_FOREIGN_KEY_TABLE)

        all_codes = set(release.FOREIGN_KEY_MISMATCH_EXIT_CODES.values()) | {
            release.EXIT_UNEXPECTED_FOREIGN_KEY_TABLE
        }
        self.assertEqual(4, len(all_codes))
        self.assertTrue(all(0 <= code <= 255 for code in all_codes))
        self.assertTrue(
            all_codes.isdisjoint(release.metadata_preflight.BOOTSTRAP_EXIT_CODES.values())
        )
        self.assertTrue(
            all_codes.isdisjoint(
                release.metadata_preflight.DEFAULT_MISMATCH_EXIT_CODES.values()
            )
        )
        self.assertTrue(
            all_codes.isdisjoint(
                range(
                    release.migration.EXIT_UNVERSIONED_TARGETS_BASE,
                    release.migration.EXIT_UNVERSIONED_TARGETS_BASE + 128,
                )
            )
        )
        self.assertTrue(all_codes.isdisjoint({250, 251}))

    def test_fk_classifier_identifies_each_expected_table(self):
        release = _load_release()
        for table, code in release.FOREIGN_KEY_MISMATCH_EXIT_CODES.items():
            with self.subTest(table=table):
                error = release.metadata_preflight.BootstrapForeignKeyMismatchError(table)
                self.assertEqual(code, release.classify_failure(error))

    def test_unexpected_fk_table_fails_closed_with_reserved_exit(self):
        release = _load_release()
        error = release.metadata_preflight.BootstrapForeignKeyMismatchError("notes")
        self.assertEqual(
            release.EXIT_UNEXPECTED_FOREIGN_KEY_TABLE,
            release.classify_failure(error),
        )


if __name__ == "__main__":
    unittest.main()
