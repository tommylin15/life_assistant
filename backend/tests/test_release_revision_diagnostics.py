import unittest
from unittest.mock import AsyncMock, patch

from alembic.config import Config
from alembic.script import ScriptDirectory

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

    def test_release_target_tracks_single_alembic_head(self):
        config = Config(str(release.BACKEND_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(release.BACKEND_ROOT / "alembic"))
        heads = ScriptDirectory.from_config(config).get_heads()
        self.assertEqual([release.RELEASE_TARGET_REVISION], heads)


class ReleaseAdvanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_current_previous_release_advances_without_historical_reconciliation(self):
        with (
            patch.object(
                release,
                "_current_revision",
                AsyncMock(return_value="20260927_0005"),
            ),
            patch.object(
                release,
                "_ensure_historical_0004",
                AsyncMock(),
            ) as historical,
            patch.object(release, "_upgrade_release_head") as upgrade,
            patch.object(
                release,
                "_verify_release_revision",
                AsyncMock(),
            ) as verify,
        ):
            await release.main()

        historical.assert_not_awaited()
        upgrade.assert_called_once_with()
        verify.assert_awaited_once_with()


if __name__ == "__main__":
    unittest.main()
