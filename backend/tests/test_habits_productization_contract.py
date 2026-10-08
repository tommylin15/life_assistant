from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
HABIT_API = REPO_ROOT / "lib" / "web" / "habit_api.dart"
HABITS_PAGE = REPO_ROOT / "lib" / "web" / "habits_page.dart"
MORE_PAGE = REPO_ROOT / "lib" / "web" / "more_page.dart"
WEB_APP = REPO_ROOT / "lib" / "web" / "web_app.dart"
UI_SCRIPT = REPO_ROOT / ".github" / "scripts" / "verify_habits_ui_production.mjs"
UI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "habits-ui-acceptance.yml"
RUNTIME_RUNNER = (
    REPO_ROOT / "backend" / "scripts" / "run_cloud_domain_parity_acceptance.py"
)


class HabitsProductizationContractTests(unittest.TestCase):
    def test_web_product_surface_exists_and_is_reachable(self):
        for path in (HABIT_API, HABITS_PAGE, MORE_PAGE, WEB_APP):
            self.assertTrue(path.is_file(), str(path))

        api = HABIT_API.read_text(encoding="utf-8")
        page = HABITS_PAGE.read_text(encoding="utf-8")
        more = MORE_PAGE.read_text(encoding="utf-8")
        app = WEB_APP.read_text(encoding="utf-8")

        for required in (
            "/habits",
            "/complete",
            "/completions",
            "createHabit",
            "updateHabit",
        ):
            self.assertIn(required, api)

        for required in (
            "新增習慣",
            "記錄完成",
            "完成紀錄",
            "提醒時間",
            "無法載入習慣",
            "還沒有習慣",
        ):
            self.assertIn(required, page)

        self.assertIn("context.go('/more/habits')", more)
        self.assertIn("path: '/more/habits'", app)
        self.assertIn("const HabitsPage()", app)

    def test_production_ui_acceptance_covers_desktop_mobile_and_release_identity(self):
        self.assertTrue(UI_SCRIPT.is_file())
        self.assertTrue(UI_WORKFLOW.is_file())

        script = UI_SCRIPT.read_text(encoding="utf-8")
        workflow = UI_WORKFLOW.read_text(encoding="utf-8")
        for required in (
            "/more/habits",
            "/api/v1/habits",
            "desktop(context)",
            "mobile(context)",
            "habits_ui_acceptance=PASS",
            "habit create",
            "habit update",
            "habit completion",
        ):
            self.assertIn(required, script)

        self.assertNotIn("workflow_run:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("release.txt?habits_acceptance=$RELEASE_SHA", workflow)
        self.assertIn("verify_habits_ui_production.mjs", workflow)

    def test_existing_real_postgres_runtime_gate_covers_habits_and_activity(self):
        self.assertTrue(RUNTIME_RUNNER.is_file())
        source = RUNTIME_RUNNER.read_text(encoding="utf-8")
        for required in (
            '"/api/v1/habits"',
            'f"/api/v1/habits/{habit_id}"',
            'f"/api/v1/habits/{habit_id}/complete"',
            'f"/api/v1/habits/{habit_id}/completions"',
            "habit_append_history_persistence",
            '"/api/v1/activity?limit=200"',
            '("habit.create", habit_id)',
            '("habit.update", habit_id)',
            '("habit.complete", habit_id)',
        ):
            self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
