import importlib.util
import unittest
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic/versions/20260930_0008_drive_project_knowledge.py"
)


class DriveMigrationContractTests(unittest.TestCase):
    def test_drive_migration_file_exists(self):
        self.assertTrue(MIGRATION_PATH.is_file(), str(MIGRATION_PATH))

    def test_drive_models_are_importable_by_metadata_bootstrap(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive"))

    def test_drive_migration_extends_notes_search_head_and_is_additive(self):
        self.assertTrue(MIGRATION_PATH.is_file(), str(MIGRATION_PATH))
        source = MIGRATION_PATH.read_text()
        self.assertIn('revision: str = "20260930_0008"', source)
        self.assertIn('down_revision: Union[str, None] = "20260930_0007"', source)
        for table in (
            "drive_workspaces",
            "drive_documents",
            "drive_workspace_documents",
            "project_drive_documents",
            "note_drive_documents",
            "drive_ai_settings",
            "drive_document_enrichment_runs",
            "drive_note_link_suggestions",
        ):
            self.assertIn(f'op.create_table(\n        "{table}"', source)
        self.assertIn("uq_drive_workspaces_default_per_owner", source)
        self.assertIn("postgresql_where=sa.text(\"is_default\")", source)
        self.assertNotIn("google_connections", source)
        self.assertNotIn("op.drop_column", source)
        self.assertNotIn("op.alter_column", source)


if __name__ == "__main__":
    unittest.main()
