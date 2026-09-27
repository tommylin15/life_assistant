import importlib.util
from pathlib import Path
import unittest

from app.models.migration_support import ChecklistItem, LegacyAttachment, LegacyMigrationRow
from app.models.task import Task, TaskStatus


class SQLiteBackfillTargetTests(unittest.TestCase):
    def test_task_history_fields_and_scheduled_status_exist(self):
        self.assertEqual("scheduled", TaskStatus.scheduled.value)
        for column in ("source_type", "source_ref", "completed_at", "deleted_at"):
            self.assertIn(column, Task.__table__.c)

    def test_history_targets_have_expected_keys(self):
        self.assertEqual({"id"}, {c.name for c in ChecklistItem.__table__.primary_key.columns})
        self.assertIn("source_local_path", LegacyAttachment.__table__.c)
        self.assertEqual(
            {"source_fingerprint", "source_table", "source_key"},
            {c.name for c in LegacyMigrationRow.__table__.primary_key.columns},
        )

    def test_0005_extends_cloud_domain_head(self):
        path = Path(__file__).parents[1] / "alembic/versions/20260927_0005_sqlite_backfill_targets.py"
        spec = importlib.util.spec_from_file_location("sqlite_backfill_targets", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        self.assertEqual("20260927_0005", module.revision)
        self.assertEqual("20260926_0004", module.down_revision)


if __name__ == "__main__":
    unittest.main()
