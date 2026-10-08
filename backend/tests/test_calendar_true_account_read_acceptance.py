from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "backend/scripts/run_calendar_true_account_read_acceptance.py"
WORKFLOW = REPO / ".github/workflows/calendar-true-account-acceptance.yml"


class CalendarTrueAccountAcceptanceContractTests(unittest.TestCase):
    def test_read_only_runner_compiles(self):
        source = RUNNER.read_text(encoding="utf-8")
        compile(source, str(RUNNER), "exec")
        self.assertIn('"GET"', source)
        self.assertIn("CALENDAR_EVENTS_URL", source)
        self.assertIn("calendar_true_account_read_list=PASS", source)
        for destructive in ('"POST"', '"PATCH"', '"DELETE"'):
            self.assertNotIn(destructive, source)

    def test_ambiguous_owner_and_output_redaction(self):
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("len(user_ids) != 1", source)
        self.assertIn("multiple_authorized_owners", source)
        self.assertIn("NOT_VERIFIED", source)
        self.assertIn("len(events)", source)
        self.assertNotIn("print(events)", source)
        self.assertNotIn("print(user_ids)", source)

    def test_failure_categories_can_be_diagnosed_without_cloud_logging(self):
        source = RUNNER.read_text(encoding="utf-8")
        for category in (
            '"reauthorization": 21',
            '"insufficient_scope": 22',
            '"google_upstream": 23',
            '"google_unavailable": 24',
            '"invalid_output": 26',
            '"database": 31',
            '"runtime": 32',
        ):
            with self.subTest(category=category):
                self.assertIn(category, source)
        self.assertIn("except HTTPException as exc:", source)
        self.assertIn("except SQLAlchemyError:", source)
        self.assertNotIn("print(exc)", source)

    def test_independent_post_deploy_workflow_reuses_core_job(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Deploy Cloud Run", workflow)
        self.assertIn("life-assistant-core-acceptance", workflow)
        self.assertIn("--args=-m,scripts.run_calendar_true_account_read_acceptance", workflow)
        self.assertIn("GCP_WORKLOAD_IDENTITY_PROVIDER", workflow)


if __name__ == "__main__":
    unittest.main()
