from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts import sqlite_postgres_backfill as backfill


class SQLitePostgresBackfillTests(unittest.TestCase):
    def _fixture(self, path: Path, *, broken_project: bool = False) -> None:
        db = sqlite3.connect(path)
        try:
            db.execute("PRAGMA user_version = 3")
            db.execute(
                "CREATE TABLE items (id TEXT PRIMARY KEY, title TEXT NOT NULL, note TEXT, status TEXT, priority TEXT, due_at INTEGER, reminder_at INTEGER, project_id TEXT, source_type TEXT, source_ref TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, completed_at INTEGER, deleted_at INTEGER)"
            )
            db.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "task-1", "Task", None, "scheduled", "normal", None, None,
                    "missing-project" if broken_project else None,
                    "test", "ref", 1790000000, 1790000001, None, None,
                ),
            )
            db.commit()
        finally:
            db.close()

    def test_export_is_deterministic_and_fingerprinted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "life_assistant.db"
            self._fixture(path)
            first = backfill.export_bundle(path)
            second = backfill.export_bundle(path)
            self.assertEqual(first, second)
            self.assertEqual(64, len(first["source_fingerprint"]))
            self.assertEqual("scheduled", first["tables"]["items"][0]["status"])

    def test_build_items_preserves_scheduled_status_and_source_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "life_assistant.db"
            self._fixture(path)
            items = backfill.build_migration_items(backfill.export_bundle(path))
            task = next(item for item in items if item.target_table == "tasks")
            self.assertEqual("scheduled", task.values["status"])
            self.assertEqual("test", task.values["source_type"])
            self.assertEqual("ref", task.values["source_ref"])

    def test_missing_project_relationship_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "life_assistant.db"
            self._fixture(path, broken_project=True)
            with self.assertRaises(backfill.RelationshipValidationError):
                backfill.build_migration_items(backfill.export_bundle(path))

    def test_naive_iso_datetime_is_rejected(self):
        with self.assertRaises(backfill.BundleValidationError):
            backfill._as_datetime("2026-09-27T12:00:00", "example")

    def test_numeric_datetime_is_utc_aware(self):
        value = backfill._as_datetime(1790000000, "example")
        self.assertIsNotNone(value.tzinfo)
        self.assertEqual(0, value.utcoffset().total_seconds())


if __name__ == "__main__":
    unittest.main()
