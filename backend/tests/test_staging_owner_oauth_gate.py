"""Regression tests for staging owner-auth gate failure classification.

These tests do not mint a Google session or query a real production DB.
"""
import contextlib
import io
import unittest
from unittest.mock import patch

from scripts import verify_staging_google_e2e as gate


class StagingOwnerOAuthGateTests(unittest.TestCase):
    def _run_failure(self, exc, expected_exit):
        output = io.StringIO()
        with patch.object(gate.asyncio, "run", side_effect=exc), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                gate.main()
        self.assertEqual(raised.exception.code, expected_exit)
        return output.getvalue()

    def test_missing_owner_evidence_is_distinct_from_db_failure(self):
        line = self._run_failure(gate.OwnerEvidenceTimeout("not received"), gate.OWNER_EVIDENCE_MISSING_EXIT)
        self.assertIn("staging_oauth_e2e=NOT_VERIFIED", line)
        self.assertIn("missing_owner_callback_session", line)
        self.assertNotIn("error_type=", line)

    def test_db_failure_is_marked_fail_without_message_or_credentials(self):
        line = self._run_failure(ConnectionError("secret-token=never-log-me"), gate.VERIFICATION_ERROR_EXIT)
        self.assertIn("staging_oauth_e2e=FAIL", line)
        self.assertIn("error_type=ConnectionError", line)
        self.assertNotIn("never-log-me", line)

    def test_unexpected_error_also_rolls_back_without_leaking_details(self):
        line = self._run_failure(ValueError("private-db-host"), gate.VERIFICATION_ERROR_EXIT)
        self.assertIn("staging_rollback_required", line)
        self.assertIn("error_type=ValueError", line)
        self.assertNotIn("private-db-host", line)


if __name__ == "__main__":
    unittest.main()
