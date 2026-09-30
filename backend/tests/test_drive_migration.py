import importlib.util
import unittest
from pathlib import Path


class DriveMigrationContractTests(unittest.TestCase):
    def test_drive_migration_file_exists(self):
        path = Path(__file__).parents[1] / "alembic/versions/20260930_0008_drive_project_knowledge.py"
        self.assertTrue(path.is_file(), str(path))

    def test_drive_models_are_importable_by_metadata_bootstrap(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive"))


if __name__ == "__main__":
    unittest.main()
