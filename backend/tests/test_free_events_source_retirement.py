"""Cancelled collectors must remain absent and old Cloud Run command fail closed."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RetiredCollectorsTests(unittest.TestCase):
    def test_obsolete_github_source_workflows_absent(self):
        for name in ("free-events-moc-observations.yml", "free-events-activation-once.yml", "free-events-db-diagnose-once.yml", "free-events-live-readback-once.yml", "free-events-cancel-stale-once.yml"):
            self.assertFalse((ROOT / ".github/workflows" / name).exists())

    def test_retired_batch_is_noop_failure(self):
        result = subprocess.run([sys.executable, "-m", "scripts.run_free_events_moc_batch"], cwd=ROOT / "backend", capture_output=True, text=True, timeout=8)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RETIRED_SOURCE_BATCH", result.stderr)

    def test_old_crawlers_are_removed(self):
        for rel in ("scripts/eventgo_connector.py", "scripts/free_events_moc_offline.py", "backend/app/services/free_events_moc_adapter.py"):
            self.assertFalse((ROOT / rel).exists())


if __name__ == "__main__":
    unittest.main()
