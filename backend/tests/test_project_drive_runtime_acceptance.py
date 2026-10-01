import inspect
import unittest
from pathlib import Path

from scripts import run_project_drive_runtime_acceptance as acceptance


class ProjectDriveRuntimeAcceptanceContractTests(unittest.TestCase):
    def test_acceptance_uses_synthetic_identity_and_never_calls_google_drive(self):
        self.assertEqual(
            acceptance.ACCEPTANCE_USER_SUB,
            "acceptance-project-drive-runtime",
        )
        source = inspect.getsource(acceptance)
        self.assertIn("DriveDocument(", source)
        self.assertIn("ProjectDriveDocument", source)
        self.assertIn("explicit_confirmation_value", source)
        self.assertNotIn("get_drive_file_metadata", source)
        self.assertNotIn("googleapis.com", source)

    def test_workflow_runs_only_after_successful_cloud_run_release(self):
        workflow = (
            Path(__file__).parents[2]
            / ".github/workflows/project-drive-runtime-acceptance.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflows: [Deploy Cloud Run]", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("github.event.workflow_run.head_sha", workflow)
        self.assertIn("scripts.run_project_drive_runtime_acceptance", workflow)
        self.assertIn("--max-retries 0", workflow)

    def test_acceptance_covers_relation_lifecycle_and_exact_cleanup(self):
        source = inspect.getsource(acceptance)
        for marker in (
            'project_drive_runtime_check={check}:PASS',
            'repeat_attach_idempotent',
            'project_delete_guard',
            'detach_preserves_drive_document',
            'project_delete_after_detach_preserves_document',
            'project_drive_runtime_acceptance=PASS',
        ):
            self.assertIn(marker, source)
        self.assertIn("delete(ProjectDriveDocument)", source)
        self.assertIn("delete(DriveDocument)", source)
        self.assertIn("delete(Project)", source)


if __name__ == "__main__":
    unittest.main()
