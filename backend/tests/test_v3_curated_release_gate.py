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
        for job in ("backend", "flutter", "deployment-scripts", "free-events-postgres", "gmail-onnx-image"):
            self.assertIn(f'.name=="{job}"', gate)
        self.assertIn("unique | length == 5", gate)
        self.assertIn("test \"$MAIN_SHA\" = \"$RELEASE_SHA\"", gate)

    def test_0018_migration_runs_before_live_traffic_without_retired_job(self):
        workflow = self.workflow
        migration = workflow.index("- name: Apply additive 0018 schema before staging or production cutover")
        staging = workflow.index("- name: Promote exact Preview to independent fixed staging live")
        promotion = workflow.index("- name: Reconfirm source SHA and live traffic, then promote")
        self.assertLess(migration, staging)
        self.assertLess(staging, promotion)
        self.assertIn("life_db_readback=PASS revision=20261028_0024", workflow)
        self.assertNotIn("scripts.run_curated_pool_runtime_acceptance", workflow)
        self.assertIn("Controlled rollback rehearsal and restore promoted live traffic", workflow)

    def test_runtime_acceptance_has_no_persistent_synthetic_writes(self):
        self.assertIn("await db.rollback()", self.script)
        self.assertIn("RELEASE_TARGET_REVISION", self.script)
        self.assertIn("on_conflict_do_update(", self.script)
        self.assertIn("UserUIPreference", self.script)
        self.assertNotIn("await db.commit()", self.script)

    def test_promotion_remains_opt_in_without_retired_google_fixture_job(self):
        self.assertIn("default: false", self.workflow)
        self.assertNotIn("DRIVE_ACCEPTANCE_GOOGLE_FILE_ID", self.workflow)
        self.assertNotIn("verify_staging_google_e2e", self.workflow)
        self.assertIn("inputs.promote && !inputs.publish_staging", self.workflow)
        self.assertIn("PROMOTION=NOT REQUESTED", self.workflow)
        self.assertIn("--no-traffic --tag", self.workflow)
        self.assertIn("cancel-in-progress: false", self.workflow)


if __name__ == "__main__":
    unittest.main()

