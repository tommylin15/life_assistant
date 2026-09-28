from pathlib import Path
import json
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"
CLEANUP_POLICY = REPO_ROOT / ".github" / "artifact-registry-cleanup-policy.json"
DIAGNOSTIC_WRAPPER = REPO_ROOT / ".github" / "scripts" / "run_cloud_run_job_with_diagnostics.sh"


class DeployCloudRunWorkflowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_batch_fast_forward_cannot_skip_backend_release(self):
        self.assertNotIn("git diff --quiet HEAD^ HEAD -- backend", self.text)
        self.assertNotIn("backend_changes.outputs.deploy", self.text)

    def test_backend_image_is_built_once_and_reused_for_every_runtime(self):
        shared_image_ref = '--image "${{ steps.backend_image.outputs.ref }}"'
        self.assertEqual(self.text.count("gcloud builds submit backend"), 1)
        self.assertIn("--async", self.text)
        self.assertIn('gcloud builds describe "$BUILD_ID"', self.text)
        self.assertIn("BUILD_STATUS", self.text)
        self.assertNotIn("--source backend", self.text)
        self.assertEqual(self.text.count(shared_image_ref), 7)

    def test_acceptance_jobs_collect_runtime_diagnostics_on_failure(self):
        wrapper_call = ".github/scripts/run_cloud_run_job_with_diagnostics.sh"
        self.assertTrue(DIAGNOSTIC_WRAPPER.is_file())
        self.assertEqual(self.text.count(wrapper_call), 5)
        wrapper = DIAGNOSTIC_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("gcloud run jobs executions list", wrapper)
        self.assertIn("gcloud run jobs executions tasks list", wrapper)
        self.assertIn("status.lastAttemptResult.exitCode", wrapper)
        self.assertIn("gcloud logging read", wrapper)

    def test_cleanup_policy_retains_only_latest_shared_backend_image(self):
        policies = json.loads(CLEANUP_POLICY.read_text(encoding="utf-8"))
        policies_by_name = {policy["name"]: policy for policy in policies}
        keep = policies_by_name["keep-latest-life-assistant-backend"]
        self.assertEqual(keep["action"], {"type": "Keep"})
        self.assertEqual(keep["mostRecentVersions"]["keepCount"], 1)
        self.assertEqual(
            keep["mostRecentVersions"]["packageNamePrefixes"],
            ["life-assistant-backend"],
        )
        self.assertLess(
            self.text.index("Run SQLite backfill failure-path runtime acceptance"),
            self.text.index("Keep only the latest life_assistant image"),
        )
        self.assertIn(
            "if: ${{ always() && steps.backend_image.outcome == 'success' }}",
            self.text,
        )

    def test_runtime_migration_gate_runs_before_service_deploy(self):
        migration_marker = "Apply verified database migration"
        deploy_marker = "Deploy backend to Cloud Run"
        self.assertIn(migration_marker, self.text)
        self.assertIn("apply_cloud_domain_parity_release", self.text)
        self.assertIn(deploy_marker, self.text)
        self.assertLess(self.text.index(migration_marker), self.text.index(deploy_marker))

    def test_release_runner_starts_as_module_from_backend_workdir(self):
        self.assertIn("--args=-m,scripts.apply_cloud_domain_parity_release", self.text)
        self.assertNotIn("--args=-m,scripts.apply_cloud_domain_parity_migration", self.text)
        self.assertNotIn("--args scripts/apply_cloud_domain_parity_migration.py", self.text)

    def test_failed_migration_surfaces_execution_task_exit_code_before_failing_gate(self):
        migration_marker = "Apply verified database migration"
        diagnostics_marker = "Collect failed migration diagnostics"
        fail_marker = "Fail migration gate"
        deploy_marker = "Deploy backend to Cloud Run"
        self.assertIn("id: migration", self.text)
        self.assertIn("continue-on-error: true", self.text)
        self.assertIn(diagnostics_marker, self.text)
        self.assertIn("steps.migration.outcome == 'failure'", self.text)
        self.assertIn("gcloud run jobs executions describe", self.text)
        self.assertIn("gcloud run jobs executions tasks list", self.text)
        self.assertIn("gcloud run jobs executions tasks describe", self.text)
        self.assertIn("status.lastAttemptResult.exitCode", self.text)
        self.assertIn(fail_marker, self.text)
        self.assertLess(self.text.index(migration_marker), self.text.index(diagnostics_marker))
        self.assertLess(self.text.index(diagnostics_marker), self.text.index(fail_marker))
        self.assertLess(self.text.index(fail_marker), self.text.index(deploy_marker))

    def test_runtime_verification_remains_mandatory(self):
        self.assertIn("Verify Cloud Run health", self.text)
        self.assertIn("Verify Cloud Run database readiness", self.text)
        self.assertIn("Verify unauthenticated API is application-protected", self.text)

    def test_sqlite_backfill_acceptance_runs_after_cloud_domain_acceptance(self):
        cloud_marker = "Run authenticated cloud-domain acceptance"
        backfill_marker = "Run SQLite backfill runtime acceptance"
        self.assertIn("BACKFILL_ACCEPTANCE_JOB: life-assistant-sqlite-backfill-acceptance", self.text)
        self.assertIn("--args=-m,scripts.run_sqlite_backfill_acceptance", self.text)
        self.assertIn(cloud_marker, self.text)
        self.assertIn(backfill_marker, self.text)
        self.assertLess(self.text.index(cloud_marker), self.text.index(backfill_marker))

    def test_sqlite_backfill_failure_acceptance_runs_after_success_acceptance(self):
        success_marker = "Run SQLite backfill runtime acceptance"
        failure_marker = "Run SQLite backfill failure-path runtime acceptance"
        self.assertIn(
            "BACKFILL_FAILURE_ACCEPTANCE_JOB: life-assistant-sqlite-backfill-failure-acceptance",
            self.text,
        )
        self.assertIn("--args=-m,scripts.run_sqlite_backfill_failure_acceptance", self.text)
        self.assertIn(success_marker, self.text)
        self.assertIn(failure_marker, self.text)
        self.assertLess(self.text.index(success_marker), self.text.index(failure_marker))


if __name__ == "__main__":
    unittest.main()
