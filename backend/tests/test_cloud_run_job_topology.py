from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


class CloudRunJobTopologyTests(unittest.TestCase):
    def test_core_acceptance_uses_one_shared_runner(self):
        workflow = (WORKFLOWS / "deploy-cloud-run.yml").read_text(encoding="utf-8")

        self.assertIn(
            "CORE_ACCEPTANCE_JOB: life-assistant-core-acceptance",
            workflow,
        )
        for legacy_job in (
            "life-assistant-cloud-domain-acceptance",
            "life-assistant-idempotency-acceptance",
            "life-assistant-google-failure-acceptance",
            "life-assistant-sqlite-backfill-acceptance",
            "life-assistant-sqlite-backfill-failure-acceptance",
        ):
            self.assertNotIn(legacy_job, workflow)

        self.assertEqual(
            workflow.count('gcloud run jobs deploy "$CORE_ACCEPTANCE_JOB"'),
            1,
        )
        self.assertEqual(
            workflow.count('gcloud run jobs execute "$CORE_ACCEPTANCE_JOB"'),
            6,
        )
        for acceptance_module in (
            "scripts.run_cloud_domain_parity_acceptance",
            "scripts.run_checklist_cloud_acceptance",
            "scripts.run_idempotency_acceptance",
            "scripts.run_google_failure_acceptance",
            "scripts.run_sqlite_backfill_acceptance",
            "scripts.run_sqlite_backfill_failure_acceptance",
        ):
            self.assertIn(acceptance_module, workflow)

    def test_postdeploy_acceptance_uses_one_shared_runner(self):
        workflow_path = WORKFLOWS / "postdeploy-runtime-acceptance.yml"
        self.assertTrue(workflow_path.is_file())
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn(
            "POSTDEPLOY_ACCEPTANCE_JOB: life-assistant-postdeploy-acceptance",
            workflow,
        )
        self.assertEqual(
            workflow.count('gcloud run jobs deploy "$POSTDEPLOY_ACCEPTANCE_JOB"'),
            1,
        )
        self.assertEqual(
            workflow.count('gcloud run jobs execute "$POSTDEPLOY_ACCEPTANCE_JOB"'),
            3,
        )
        for acceptance_module in (
            "scripts.run_notes_product_acceptance",
            "scripts.run_project_drive_runtime_acceptance",
            "scripts.run_drive_ai_enrichment_acceptance",
        ):
            self.assertIn(acceptance_module, workflow)

        self.assertEqual(workflow.count("continue-on-error: true"), 3)
        self.assertIn("Fail post-deploy runtime acceptance gate", workflow)
        for step_id in (
            "notes_acceptance",
            "project_drive_acceptance",
            "drive_ai_acceptance",
        ):
            self.assertIn(f"steps.{step_id}.outcome == 'failure'", workflow)

        for retired_workflow in (
            "notes-runtime-acceptance.yml",
            "project-drive-runtime-acceptance.yml",
            "drive-ai-enrichment-runtime-acceptance.yml",
        ):
            self.assertFalse((WORKFLOWS / retired_workflow).exists())

    def test_normal_workflows_do_not_delete_cloud_run_jobs(self):
        workflow_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in WORKFLOWS.glob("*.yml")
        )
        self.assertNotIn("gcloud run jobs delete", workflow_text)


if __name__ == "__main__":
    unittest.main()
