"""V3 migration/acceptance ordering guarantees for the curated release."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / ".github/workflows/v3-release-ghcr.yml"
SCRIPT = ROOT / "backend/scripts/run_curated_pool_runtime_acceptance.py"


class CuratedV3ReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = FLOW.read_text(encoding="utf-8")
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_main_sha_gate_requires_postgresql_sidecar_success(self):
        gate = self.workflow.split("- name: Guard main SHA", 1)[1].split(
            "- name: Build Docker", 1
        )[0]
        for job in ("backend", "flutter", "deployment-scripts", "free-events-postgres"):
            self.assertIn(f'.name=="{job}"', gate)
        self.assertIn("unique | length == 4", gate)
        self.assertIn("test \"$MAIN_SHA\" = \"$RELEASE_SHA\"", gate)

    def test_0015_migration_runs_before_drive_ai_and_live_traffic(self):
        workflow = self.workflow
        migration = workflow.index("- name: Apply additive 0015 schema before production cutover")
        readback = workflow.index("- name: Rollback-only curated pool migration")
        drive = workflow.index("- name: Pre-promotion Drive AI consent")
        promotion = workflow.index("- name: Reconfirm source SHA and live traffic, then promote")
        self.assertLess(migration, readback)
        self.assertLess(readback, drive)
        self.assertLess(drive, promotion)
        self.assertIn("curated_schema_migration=PASS alembic=20261010_0015", workflow)
        self.assertIn("--args=-m,scripts.run_curated_pool_runtime_acceptance", workflow)

    def test_runtime_acceptance_has_no_persistent_synthetic_writes(self):
        self.assertIn("await db.rollback()", self.script)
        self.assertIn("20261010_0015", self.script)
        self.assertIn("on_conflict_do_update(", self.script)
        self.assertIn("UserUIPreference", self.script)
        self.assertNotIn("await db.commit()", self.script)

    def test_promotion_remains_opt_in_and_google_fixture_required(self):
        self.assertIn("default: false", self.workflow)
        self.assertIn("DRIVE_ACCEPTANCE_GOOGLE_FILE_ID", self.workflow)
        self.assertIn("PROMOTION=NOT REQUESTED", self.workflow)
        self.assertIn("--no-traffic --tag", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)


if __name__ == "__main__":
    unittest.main()
