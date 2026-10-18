from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "run_checklist_cloud_acceptance.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-cloud-run.yml"


class ChecklistRuntimeAcceptanceContractTests(unittest.TestCase):
    def test_runtime_acceptance_script_exists_and_compiles(self):
        self.assertTrue(SCRIPT.is_file(), "Checklist Cloud acceptance runner must exist")
        source = SCRIPT.read_text(encoding="utf-8")
        compile(source, str(SCRIPT), "exec")

    def test_runner_covers_checklist_cloud_contract_and_exact_cleanup(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "/api/v1/tasks",
            "/checklist",
            "X-Life-Assistant-Action-ID",
            "checklist_create_replay",
            "checklist_order_persistence",
            "checklist_update_persistence",
            "cross_task_guard",
            "checklist_delete_persistence",
            "task_delete_child_cleanup",
            "checklist_item.create",
            "checklist_item.update",
            "checklist_item.delete",
            "cleanup_exact_artifacts",
            "app.dependency_overrides[current_user]",
            "[ACCEPTANCE TEST]",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_retired_checklist_cloud_runner_is_not_in_deploy_workflow(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("Run checklist cloud runtime acceptance", workflow)
        self.assertNotIn("--args=-m,scripts.run_checklist_cloud_acceptance", workflow)
        self.assertIn("Run action-id idempotency runtime acceptance", workflow)



if __name__ == "__main__":
    unittest.main()
